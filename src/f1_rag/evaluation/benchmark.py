"""Benchmark reproducible para evaluar el pipeline híbrido de F1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import time
import unicodedata
from typing import Any

from f1_rag.config import AppConfig
from f1_rag.orchestration import HybridPipelineResult, run_hybrid_pipeline


@dataclass(slots=True)
class BenchmarkExpectation:
    """Criterios esperados para una pregunta del benchmark."""

    min_row_count: int = 1
    expected_context_tables: list[str] | None = None
    expected_sql_keywords: list[str] | None = None
    expected_answer_keywords: list[str] | None = None


@dataclass(slots=True)
class BenchmarkCase:
    """Caso individual del benchmark."""

    case_id: str
    category: str
    question: str
    top_k: int
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
    category: str
    question: str
    passed: bool
    duration_seconds: float
    checks: list[BenchmarkCheck]
    generated_sql: str | None
    row_count: int | None
    retrieved_tables: list[str]
    final_answer: str | None
    error: str | None = None


@dataclass(slots=True)
class BenchmarkSuiteResult:
    """Resultado agregado de una corrida completa del benchmark."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_seconds: float
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
        cases.append(
            BenchmarkCase(
                case_id=item["case_id"],
                category=item["category"],
                question=item["question"],
                top_k=item.get("top_k", 3),
                expectation=expectation,
            )
        )
    return cases


def run_benchmark_suite(
    cases: list[BenchmarkCase],
    config: AppConfig | None = None,
) -> BenchmarkSuiteResult:
    """Ejecuta una batería de casos sobre el pipeline híbrido."""

    app_config = config or AppConfig.from_env()
    start_time = time.perf_counter()
    case_results = [run_benchmark_case(case, config=app_config) for case in cases]
    duration_seconds = time.perf_counter() - start_time
    passed_cases = sum(1 for result in case_results if result.passed)
    return BenchmarkSuiteResult(
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=len(case_results) - passed_cases,
        duration_seconds=duration_seconds,
        case_results=case_results,
    )


def run_benchmark_case(
    case: BenchmarkCase,
    config: AppConfig | None = None,
) -> BenchmarkCaseResult:
    """Ejecuta y evalúa un único caso del benchmark."""

    app_config = config or AppConfig.from_env()
    start_time = time.perf_counter()
    try:
        result = run_hybrid_pipeline(case.question, config=app_config, top_k=case.top_k)
    except Exception as exc:
        return BenchmarkCaseResult(
            case_id=case.case_id,
            category=case.category,
            question=case.question,
            passed=False,
            duration_seconds=time.perf_counter() - start_time,
            checks=[],
            generated_sql=None,
            row_count=None,
            retrieved_tables=[],
            final_answer=None,
            error=str(exc),
        )

    checks = evaluate_hybrid_result(result, case.expectation)
    return BenchmarkCaseResult(
        case_id=case.case_id,
        category=case.category,
        question=case.question,
        passed=all(check.passed for check in checks),
        duration_seconds=time.perf_counter() - start_time,
        checks=checks,
        generated_sql=result.generated_sql,
        row_count=result.query_result.row_count,
        retrieved_tables=[str(chunk.metadata.get("table_name", "")) for chunk in result.retrieved_chunks],
        final_answer=result.final_answer.answer,
        error=None,
    )


def evaluate_hybrid_result(
    result: HybridPipelineResult,
    expectation: BenchmarkExpectation,
) -> list[BenchmarkCheck]:
    """Evalúa un resultado del pipeline contra expectativas sencillas."""

    checks: list[BenchmarkCheck] = []
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

    if expectation.expected_context_tables:
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

    return checks


def benchmark_suite_to_dict(suite_result: BenchmarkSuiteResult) -> dict[str, Any]:
    """Convierte el resultado del benchmark a un diccionario serializable."""

    return asdict(suite_result)


def render_benchmark_summary(suite_result: BenchmarkSuiteResult) -> str:
    """Construye un resumen legible de la corrida del benchmark."""

    lines = [
        "Benchmark híbrido completado.",
        f"- Casos totales: {suite_result.total_cases}",
        f"- Casos aprobados: {suite_result.passed_cases}",
        f"- Casos fallidos: {suite_result.failed_cases}",
        f"- Duración total: {suite_result.duration_seconds:.2f} segundos",
    ]

    for case_result in suite_result.case_results:
        status = "PASS" if case_result.passed else "FAIL"
        lines.append(
            f"- [{status}] {case_result.case_id} ({case_result.category}) en "
            f"{case_result.duration_seconds:.2f}s"
        )
        if case_result.error:
            lines.append(f"  Error: {case_result.error}")
            continue
        for check in case_result.checks:
            check_status = "ok" if check.passed else "error"
            lines.append(f"  - {check.name}: {check_status} | {check.details}")
    return "\n".join(lines)


def _normalize_text(value: str) -> str:
    """Normaliza texto para comparaciones suaves."""

    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_accents.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()
