"""Benchmark reproducible para evaluar el pipeline híbrido según el capítulo 6."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import re
import time
import unicodedata
from typing import Any

from f1_rag.config import AppConfig
from f1_rag.database.query_executor import QueryExecutionResult, execute_select_query
from f1_rag.database.sql_validator import validate_select_query
from f1_rag.orchestration import HybridPipelineResult, run_hybrid_pipeline


@dataclass(slots=True)
class BenchmarkExpectation:
    """Criterios esperados para una pregunta del benchmark."""

    min_row_count: int = 1
    expected_context_tables: list[str] | None = None
    expected_sql_keywords: list[str] | None = None
    expected_answer_keywords: list[str] | None = None
    reference_sql: str | None = None
    ignore_row_order: bool = False
    expected_rejection: bool = False
    expected_error_keywords: list[str] | None = None
    expected_chart_type: str | None = None
    allow_additional_rows: bool = False


@dataclass(slots=True)
class BenchmarkCase:
    """Caso individual del benchmark."""

    case_id: str
    category_code: str
    category_name: str
    question: str
    top_k: int
    apply_to_baseline: bool
    expectation: BenchmarkExpectation


@dataclass(slots=True)
class BenchmarkCheck:
    """Resultado de una verificación puntual del benchmark."""

    name: str
    passed: bool
    details: str


@dataclass(slots=True)
class BenchmarkCaseResult:
    """Resultado estructurado de un caso del benchmark."""

    case_id: str
    category_code: str
    category_name: str
    question: str
    mode: str
    passed: bool
    duration_seconds: float
    checks: list[BenchmarkCheck]
    metrics: dict[str, bool | None]
    generated_sql: str | None
    row_count: int | None
    reference_row_count: int | None
    retrieved_tables: list[str]
    chart_type: str | None
    final_answer: str | None
    error: str | None = None


@dataclass(slots=True)
class BenchmarkCategorySummary:
    """Resumen agregado por categoría del benchmark."""

    category_code: str
    category_name: str
    total_cases: int
    passed_cases: int
    average_duration_seconds: float
    metric_rates: dict[str, float]


@dataclass(slots=True)
class BenchmarkSuiteResult:
    """Resultado agregado de una corrida completa del benchmark."""

    mode: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_seconds: float
    category_summaries: list[BenchmarkCategorySummary]
    case_results: list[BenchmarkCaseResult]


def load_benchmark_cases(path: str | Path) -> list[BenchmarkCase]:
    """Carga casos de benchmark desde un archivo JSON."""

    cases_path = Path(path)
    if not cases_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de benchmark: {cases_path}")

    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("El archivo de benchmark debe contener una lista no vacía de casos.")

    cases: list[BenchmarkCase] = []
    for item in payload:
        expectation = BenchmarkExpectation(**item["expectation"])
        category_code = item.get("category_code", item.get("category", "general"))
        category_name = item.get("category_name", category_code)
        cases.append(
            BenchmarkCase(
                case_id=item["case_id"],
                category_code=category_code,
                category_name=category_name,
                question=item["question"],
                top_k=item.get("top_k", 3),
                apply_to_baseline=item.get("apply_to_baseline", category_code in {"A", "B", "C"}),
                expectation=expectation,
            )
        )
    return cases


def filter_cases_for_mode(cases: list[BenchmarkCase], mode: str) -> list[BenchmarkCase]:
    """Filtra casos según el modo de evaluación solicitado."""

    if mode == "hybrid":
        return cases

    if mode == "baseline":
        filtered_cases = [case for case in cases if case.apply_to_baseline]
        if not filtered_cases:
            raise ValueError("No hay casos compatibles con la línea base sin RAG.")
        return filtered_cases

    raise ValueError(f"Modo de benchmark no soportado: {mode}")


def run_benchmark_suite(
    cases: list[BenchmarkCase],
    config: AppConfig | None = None,
    mode: str = "hybrid",
) -> BenchmarkSuiteResult:
    """Ejecuta una batería de casos sobre el pipeline híbrido o su línea base."""

    app_config = config or AppConfig.from_env()
    filtered_cases = filter_cases_for_mode(cases, mode=mode)
    enable_rag = mode == "hybrid"
    start_time = time.perf_counter()
    case_results = [
        run_benchmark_case(case, config=app_config, mode=mode, enable_rag=enable_rag)
        for case in filtered_cases
    ]
    duration_seconds = time.perf_counter() - start_time
    passed_cases = sum(1 for result in case_results if result.passed)
    return BenchmarkSuiteResult(
        mode=mode,
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=len(case_results) - passed_cases,
        duration_seconds=duration_seconds,
        category_summaries=_build_category_summaries(case_results),
        case_results=case_results,
    )


def run_benchmark_case(
    case: BenchmarkCase,
    config: AppConfig | None = None,
    mode: str = "hybrid",
    enable_rag: bool = True,
) -> BenchmarkCaseResult:
    """Ejecuta y evalúa un único caso del benchmark."""

    app_config = config or AppConfig.from_env()
    start_time = time.perf_counter()

    try:
        result = run_hybrid_pipeline(
            case.question,
            config=app_config,
            top_k=case.top_k,
            enable_rag=enable_rag,
        )
    except Exception as exc:
        duration_seconds = time.perf_counter() - start_time
        if case.expectation.expected_rejection:
            checks = _evaluate_expected_rejection(str(exc), case.expectation)
            metrics = _build_rejection_metrics(checks, duration_seconds)
            return BenchmarkCaseResult(
                case_id=case.case_id,
                category_code=case.category_code,
                category_name=case.category_name,
                question=case.question,
                mode=mode,
                passed=_metrics_passed(metrics),
                duration_seconds=duration_seconds,
                checks=checks,
                metrics=metrics,
                generated_sql=None,
                row_count=None,
                reference_row_count=None,
                retrieved_tables=[],
                chart_type=None,
                final_answer=None,
                error=str(exc),
            )

        metrics = {"M-01": False, "M-02": False, "M-03": None, "M-06": True, "M-07": None}
        return BenchmarkCaseResult(
            case_id=case.case_id,
            category_code=case.category_code,
            category_name=case.category_name,
            question=case.question,
            mode=mode,
            passed=False,
            duration_seconds=duration_seconds,
            checks=[
                BenchmarkCheck(
                    name="pipeline_error",
                    passed=False,
                    details=f"El pipeline falló antes de completar la consulta: {exc}",
                )
            ],
            metrics=metrics,
            generated_sql=None,
            row_count=None,
            reference_row_count=None,
            retrieved_tables=[],
            chart_type=None,
            final_answer=None,
            error=str(exc),
        )

    checks, metrics, reference_row_count = evaluate_hybrid_result(
        result=result,
        expectation=case.expectation,
        config=app_config,
        mode=mode,
    )
    return BenchmarkCaseResult(
        case_id=case.case_id,
        category_code=case.category_code,
        category_name=case.category_name,
        question=case.question,
        mode=mode,
        passed=_metrics_passed(metrics),
        duration_seconds=time.perf_counter() - start_time,
        checks=checks,
        metrics=metrics,
        generated_sql=result.generated_sql,
        row_count=result.query_result.row_count,
        reference_row_count=reference_row_count,
        retrieved_tables=[str(chunk.metadata.get("table_name", "")) for chunk in result.retrieved_chunks],
        chart_type=result.query_report.chart_spec.chart_type if result.query_report.chart_spec else None,
        final_answer=result.final_answer.answer,
        error=None,
    )


def evaluate_hybrid_result(
    result: HybridPipelineResult,
    expectation: BenchmarkExpectation,
    config: AppConfig,
    mode: str,
) -> tuple[list[BenchmarkCheck], dict[str, bool | None], int | None]:
    """Evalúa un resultado del pipeline contra expectativas y métricas del capítulo 6."""

    if expectation.expected_rejection:
        checks = [
            BenchmarkCheck(
                name="security_rejection",
                passed=False,
                details=(
                    "La consulta no fue rechazada por el sistema. "
                    "Se generó una respuesta en lugar de bloquear la operación."
                ),
            )
        ]
        metrics = {
            "M-01": None,
            "M-02": None,
            "M-03": False,
            "M-06": True,
            "M-07": None,
        }
        return checks, metrics, None

    checks: list[BenchmarkCheck] = []
    metrics: dict[str, bool | None] = {
        "M-01": None,
        "M-02": True,
        "M-03": None,
        "M-06": True,
        "M-07": None,
    }
    reference_row_count: int | None = None

    checks.append(
        BenchmarkCheck(
            name="row_count",
            passed=result.query_result.row_count >= expectation.min_row_count,
            details=(
                f"Filas obtenidas: {result.query_result.row_count}. "
                f"Mínimo esperado: {expectation.min_row_count}."
            ),
        )
    )

    if expectation.reference_sql:
        reference_result = _execute_reference_query(expectation.reference_sql, config=config)
        reference_row_count = reference_result.row_count
        execution_accuracy_passed = _compare_query_results(
            actual=result.query_result,
            expected=reference_result,
            ignore_row_order=expectation.ignore_row_order,
            allow_additional_rows=expectation.allow_additional_rows,
        )
        metrics["M-01"] = execution_accuracy_passed
        checks.append(
            BenchmarkCheck(
                name="execution_accuracy",
                passed=execution_accuracy_passed,
                details=(
                    f"Filas referencia: {reference_result.row_count}. "
                    f"Filas generadas: {result.query_result.row_count}."
                ),
            )
        )

    if expectation.expected_context_tables and mode == "hybrid":
        retrieved_tables = [str(chunk.metadata.get("table_name", "")) for chunk in result.retrieved_chunks]
        missing_tables = [
            table
            for table in expectation.expected_context_tables
            if table not in retrieved_tables
        ]
        checks.append(
            BenchmarkCheck(
                name="context_tables",
                passed=not missing_tables,
                details=(
                    f"Tablas recuperadas: {retrieved_tables}. "
                    f"Esperadas: {expectation.expected_context_tables}."
                ),
            )
        )

    if expectation.expected_sql_keywords:
        normalized_sql = _normalize_text(result.generated_sql)
        missing_keywords = [
            keyword
            for keyword in expectation.expected_sql_keywords
            if _normalize_text(keyword) not in normalized_sql
        ]
        checks.append(
            BenchmarkCheck(
                name="sql_keywords",
                passed=not missing_keywords,
                details=(
                    f"Keywords SQL faltantes: {missing_keywords or 'ninguna'}. "
                    f"SQL generada: {result.generated_sql}"
                ),
            )
        )

    if expectation.expected_answer_keywords:
        normalized_answer = _normalize_text(result.final_answer.answer)
        missing_keywords = [
            keyword
            for keyword in expectation.expected_answer_keywords
            if _normalize_text(keyword) not in normalized_answer
        ]
        checks.append(
            BenchmarkCheck(
                name="answer_keywords",
                passed=not missing_keywords,
                details=(
                    f"Keywords de respuesta faltantes: {missing_keywords or 'ninguna'}."
                ),
            )
        )

    if expectation.expected_chart_type is not None:
        actual_chart_type = result.query_report.chart_spec.chart_type if result.query_report.chart_spec else "none"
        chart_passed = actual_chart_type == expectation.expected_chart_type
        metrics["M-07"] = chart_passed
        checks.append(
            BenchmarkCheck(
                name="chart_type",
                passed=chart_passed,
                details=(
                    f"Gráfico esperado: {expectation.expected_chart_type}. "
                    f"Gráfico obtenido: {actual_chart_type}."
                ),
            )
        )

    return checks, metrics, reference_row_count


def benchmark_suite_to_dict(suite_result: BenchmarkSuiteResult) -> dict[str, Any]:
    """Convierte el resultado del benchmark a un diccionario serializable."""

    return asdict(suite_result)


def render_benchmark_summary(suite_result: BenchmarkSuiteResult) -> str:
    """Construye un resumen legible de la corrida del benchmark."""

    lines = [
        f"Benchmark ({suite_result.mode}) completado.",
        f"- Casos totales: {suite_result.total_cases}",
        f"- Casos aprobados: {suite_result.passed_cases}",
        f"- Casos fallidos: {suite_result.failed_cases}",
        f"- Duración total: {suite_result.duration_seconds:.2f} segundos",
    ]

    if suite_result.category_summaries:
        lines.append("- Resumen por categoría:")
        for summary in suite_result.category_summaries:
            lines.append(
                f"  - {summary.category_code} ({summary.category_name}): "
                f"{summary.passed_cases}/{summary.total_cases} aprobados, "
                f"promedio {summary.average_duration_seconds:.2f}s, "
                f"métricas {summary.metric_rates}"
            )

    for case_result in suite_result.case_results:
        status = "PASS" if case_result.passed else "FAIL"
        lines.append(
            f"- [{status}] {case_result.case_id} "
            f"({case_result.category_code} - {case_result.category_name}) en "
            f"{case_result.duration_seconds:.2f}s"
        )
        if case_result.error:
            lines.append(f"  Error: {case_result.error}")
        for metric_name, metric_value in case_result.metrics.items():
            lines.append(f"  - {metric_name}: {_format_metric_value(metric_value)}")
        for check in case_result.checks:
            check_status = "ok" if check.passed else "error"
            lines.append(f"  - {check.name}: {check_status} | {check.details}")
    return "\n".join(lines)


def export_manual_review_template(
    suite_result: BenchmarkSuiteResult,
    output_path: str | Path,
) -> Path:
    """Genera una plantilla CSV para las métricas cualitativas manuales."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "ID",
                "Categoria",
                "Nombre_categoria",
                "Modo",
                "Consulta_NL",
                "SQL_generada",
                "Resultado_resumen",
                "M_01",
                "M_02",
                "M_03",
                "M_04_eval_1",
                "M_04_eval_2",
                "M_05_o_M_05E_eval_1",
                "M_05_o_M_05E_eval_2",
                "M_07_eval_1",
                "M_07_eval_2",
                "Tipo_grafico",
                "Tiempo_s",
                "Observaciones",
            ],
        )
        writer.writeheader()
        for case_result in suite_result.case_results:
            writer.writerow(
                {
                    "ID": case_result.case_id,
                    "Categoria": case_result.category_code,
                    "Nombre_categoria": case_result.category_name,
                    "Modo": case_result.mode,
                    "Consulta_NL": case_result.question,
                    "SQL_generada": case_result.generated_sql or "",
                    "Resultado_resumen": case_result.final_answer or case_result.error or "",
                    "M_01": _format_metric_value(case_result.metrics.get("M-01")),
                    "M_02": _format_metric_value(case_result.metrics.get("M-02")),
                    "M_03": _format_metric_value(case_result.metrics.get("M-03")),
                    "M_04_eval_1": "",
                    "M_04_eval_2": "",
                    "M_05_o_M_05E_eval_1": "",
                    "M_05_o_M_05E_eval_2": "",
                    "M_07_eval_1": "",
                    "M_07_eval_2": "",
                    "Tipo_grafico": case_result.chart_type or "",
                    "Tiempo_s": f"{case_result.duration_seconds:.2f}",
                    "Observaciones": "",
                }
            )

    return destination


def _evaluate_expected_rejection(
    error_message: str,
    expectation: BenchmarkExpectation,
) -> list[BenchmarkCheck]:
    """Evalúa un caso donde el comportamiento correcto es rechazar la consulta."""

    checks = [
        BenchmarkCheck(
            name="security_rejection",
            passed=True,
            details=f"La consulta fue rechazada correctamente: {error_message}",
        )
    ]

    if expectation.expected_error_keywords:
        normalized_error = _normalize_text(error_message)
        missing_keywords = [
            keyword
            for keyword in expectation.expected_error_keywords
            if _normalize_text(keyword) not in normalized_error
        ]
        checks.append(
            BenchmarkCheck(
                name="rejection_message_keywords",
                passed=not missing_keywords,
                details=(
                    f"Keywords de rechazo faltantes: {missing_keywords or 'ninguna'}."
                ),
            )
        )

    return checks


def _build_rejection_metrics(
    checks: list[BenchmarkCheck],
    _duration_seconds: float,
) -> dict[str, bool | None]:
    """Construye el mapa de métricas para casos de seguridad."""

    rejection_passed = all(check.passed for check in checks)
    return {
        "M-01": None,
        "M-02": None,
        "M-03": rejection_passed,
        "M-06": True,
        "M-07": None,
    }


def _execute_reference_query(query: str, config: AppConfig) -> QueryExecutionResult:
    """Ejecuta la consulta SQL de referencia asociada a un caso."""

    validated_query = validate_select_query(query)
    return execute_select_query(validated_query, config=config)


def _compare_query_results(
    actual: QueryExecutionResult,
    expected: QueryExecutionResult,
    ignore_row_order: bool,
    allow_additional_rows: bool = False,
) -> bool:
    """Compara dos resultados SQL por valores devueltos."""

    if allow_additional_rows:
        if actual.row_count < expected.row_count:
            return False
    elif actual.row_count != expected.row_count:
        return False

    actual_rows = [_normalize_row_values(row, actual.columns) for row in actual.rows]
    expected_rows = [_normalize_row_values(row, expected.columns) for row in expected.rows]

    if ignore_row_order:
        unmatched_actual_rows = actual_rows.copy()
        for expected_row in expected_rows:
            matched_index = next(
                (
                    index
                    for index, actual_row in enumerate(unmatched_actual_rows)
                    if _actual_row_covers_expected(actual_row, expected_row)
                ),
                None,
            )
            if matched_index is None:
                return False
            unmatched_actual_rows.pop(matched_index)
        return True

    if allow_additional_rows:
        actual_rows = actual_rows[: len(expected_rows)]

    return all(
        _actual_row_covers_expected(actual_row, expected_row)
        for actual_row, expected_row in zip(actual_rows, expected_rows)
    )


def _normalize_row_values(row: dict[str, Any], columns: list[str]) -> tuple[str, ...]:
    """Normaliza una fila SQL a valores comparables, tolerando columnas adicionales."""

    normalized_values: list[str] = []
    for column in columns:
        raw_value = _make_json_safe(row.get(column))
        text_value = _stringify_scalar(raw_value)
        normalized_value = _normalize_result_value(text_value)
        if normalized_value:
            normalized_values.append(normalized_value)
    return tuple(normalized_values)


def _actual_row_covers_expected(actual_row: tuple[str, ...], expected_row: tuple[str, ...]) -> bool:
    """Verifica si la fila generada contiene la información relevante de la referencia."""

    if not expected_row:
        return True

    for expected_value in expected_row:
        if not any(
            _result_values_match(actual_value, expected_value)
            for actual_value in actual_row
        ):
            return False
    return True


def _result_values_match(actual_value: str, expected_value: str) -> bool:
    """Compara dos valores escalares, tolerando redondeos numéricos leves."""

    if actual_value == expected_value:
        return True

    actual_number = _try_parse_float(actual_value)
    expected_number = _try_parse_float(expected_value)
    if actual_number is not None and expected_number is not None:
        return abs(actual_number - expected_number) <= 0.01

    return expected_value in actual_value or actual_value in expected_value


def _try_parse_float(value: str) -> float | None:
    """Intenta interpretar un valor normalizado como número decimal."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_category_summaries(case_results: list[BenchmarkCaseResult]) -> list[BenchmarkCategorySummary]:
    """Calcula métricas agregadas por categoría."""

    grouped: dict[tuple[str, str], list[BenchmarkCaseResult]] = {}
    for result in case_results:
        grouped.setdefault((result.category_code, result.category_name), []).append(result)

    summaries: list[BenchmarkCategorySummary] = []
    for (category_code, category_name), results in sorted(grouped.items()):
        metric_rates: dict[str, float] = {}
        for metric_name in ["M-01", "M-02", "M-03", "M-07"]:
            values = [result.metrics.get(metric_name) for result in results if result.metrics.get(metric_name) is not None]
            if not values:
                continue
            metric_rates[metric_name] = round(sum(1 for value in values if value) / len(values), 3)

        summaries.append(
            BenchmarkCategorySummary(
                category_code=category_code,
                category_name=category_name,
                total_cases=len(results),
                passed_cases=sum(1 for result in results if result.passed),
                average_duration_seconds=round(
                    sum(result.duration_seconds for result in results) / len(results),
                    3,
                ),
                metric_rates=metric_rates,
            )
        )

    return summaries


def _make_json_safe(value: object) -> object:
    """Convierte valores a una forma comparable y serializable."""

    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


def _stringify_scalar(value: object) -> str:
    """Convierte un valor escalar a string estable para comparaciones."""

    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _format_metric_value(value: bool | None) -> str:
    """Formatea una métrica booleana o no aplicable."""

    if value is None:
        return "N/A"
    return "V" if value else "X"


def _metrics_passed(metrics: dict[str, bool | None]) -> bool:
    """Determina si un caso aprueba considerando solo métricas aplicables."""

    applicable_values = [value for value in metrics.values() if value is not None]
    if not applicable_values:
        return False
    return all(applicable_values)


def _normalize_text(value: str) -> str:
    """Normaliza texto para comparaciones suaves."""

    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_accents.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _normalize_result_value(value: str) -> str:
    """Normaliza valores de resultados SQL preservando decimales y fechas."""

    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_accents.lower()
    lowered = re.sub(r"[^a-z0-9\.\-:\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()
