"""Utilidades de reportería y visualización para resultados tabulares."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from f1_rag.database.query_executor import QueryExecutionResult


@dataclass(slots=True)
class ChartSpec:
    """Define un gráfico simple para representar un resultado tabular."""

    chart_type: str
    x_column: str
    y_columns: list[str]
    title: str
    sort_by: str | None = None
    sort_ascending: bool = True


@dataclass(slots=True)
class QueryReport:
    """Resumen analítico derivado del resultado SQL."""

    dataframe: pd.DataFrame
    summary_text: str
    headline_text: str
    primary_metric: str | None
    chart_spec: ChartSpec | None
    no_chart_reason: str | None


def build_query_report(query_result: QueryExecutionResult) -> QueryReport:
    """Construye un reporte analítico simple a partir del resultado SQL."""

    dataframe = pd.DataFrame(query_result.rows)
    if dataframe.empty:
        return QueryReport(
            dataframe=dataframe,
            summary_text="La consulta no devolvió filas, por lo que no hay gráfico ni resumen analítico adicional.",
            headline_text="No hubo resultados para construir un análisis adicional.",
            primary_metric=None,
            chart_spec=None,
            no_chart_reason="La consulta no devolvió filas.",
        )

    normalized_dataframe = _normalize_dataframe_types(dataframe)
    primary_metric = _select_primary_metric(normalized_dataframe)
    chart_spec, no_chart_reason = infer_chart_spec(normalized_dataframe, primary_metric=primary_metric)
    headline_text = build_headline_text(normalized_dataframe, primary_metric=primary_metric)
    summary_text = build_summary_text(
        normalized_dataframe,
        primary_metric=primary_metric,
        chart_spec=chart_spec,
        no_chart_reason=no_chart_reason,
    )
    return QueryReport(
        dataframe=normalized_dataframe,
        summary_text=summary_text,
        headline_text=headline_text,
        primary_metric=primary_metric,
        chart_spec=chart_spec,
        no_chart_reason=no_chart_reason,
    )


def infer_chart_spec(
    dataframe: pd.DataFrame,
    primary_metric: str | None,
) -> tuple[ChartSpec | None, str | None]:
    """Infiera un gráfico sencillo a partir de columnas del DataFrame."""

    if len(dataframe) <= 1:
        return None, "La consulta devolvió una sola fila, por lo que no hay comparación visual útil."

    numeric_columns = _get_preferred_numeric_columns(dataframe)
    datetime_columns = list(dataframe.select_dtypes(include=["datetime64[ns]"]).columns)
    timeline_columns = _get_timeline_columns(dataframe)
    categorical_columns = _get_preferred_categorical_columns(dataframe, excluded_columns=datetime_columns)

    if primary_metric is None:
        return None, "No se detectó una métrica numérica suficientemente informativa para graficar."

    if timeline_columns and primary_metric in dataframe.columns:
        return (
            ChartSpec(
                chart_type="line",
                x_column=timeline_columns[0],
                y_columns=[primary_metric],
                title=f"Evolución de {primary_metric} en función de {timeline_columns[0]}",
                sort_by=timeline_columns[0],
                sort_ascending=True,
            ),
            None,
        )

    if categorical_columns and primary_metric in dataframe.columns and len(dataframe) <= 20:
        return (
            ChartSpec(
                chart_type="bar",
                x_column=categorical_columns[0],
                y_columns=[primary_metric],
                title=f"Comparación de {primary_metric} por {categorical_columns[0]}",
                sort_by=primary_metric,
                sort_ascending=False,
            ),
            None,
        )

    if len(dataframe) > 20:
        return None, "El resultado tiene demasiadas filas para un gráfico automático simple."

    return None, "No se detectó una combinación simple de ejes que aportara una visualización útil."


def build_summary_text(
    dataframe: pd.DataFrame,
    primary_metric: str | None,
    chart_spec: ChartSpec | None = None,
    no_chart_reason: str | None = None,
) -> str:
    """Construye un resumen breve y legible del resultado."""

    row_count = len(dataframe)
    column_count = len(dataframe.columns)

    parts = [f"Se obtuvieron {row_count} filas y {column_count} columnas desde PostgreSQL."]

    if primary_metric is not None:
        parts.append(
            f"La métrica numérica principal detectada es `{primary_metric}`, con mínimo "
            f"{_format_scalar(dataframe[primary_metric].min())} y máximo "
            f"{_format_scalar(dataframe[primary_metric].max())}."
        )
    else:
        parts.append("No se detectó una métrica numérica principal claramente útil en este resultado.")

    if chart_spec is not None:
        parts.append(
            f"Se sugirió un gráfico de tipo `{chart_spec.chart_type}` usando "
            f"`{chart_spec.x_column}` en el eje X y `{', '.join(chart_spec.y_columns)}` como serie."
        )
    elif no_chart_reason:
        parts.append(no_chart_reason)
    else:
        parts.append("No se detectó una forma de visualización simple que fuera claramente útil.")

    return " ".join(parts)


def build_headline_text(dataframe: pd.DataFrame, primary_metric: str | None) -> str:
    """Construye un hallazgo breve a partir del resultado SQL."""

    if dataframe.empty:
        return "No hubo resultados para resumir."

    if len(dataframe) == 1:
        row = dataframe.iloc[0].to_dict()
        identity = _build_row_identity(row)
        if primary_metric and primary_metric in row:
            return (
                f"El resultado contiene un único registro"
                f"{': ' + identity if identity else ''} con `{primary_metric}` = "
                f"{_format_scalar(row[primary_metric])}."
            )
        lap_metric = _select_present_lap_metric(row)
        if identity and lap_metric is not None:
            return (
                f"El resultado confirma a {identity} y registra `{lap_metric}` = "
                f"{_format_scalar(row[lap_metric])}."
            )
        if identity:
            return f"El resultado contiene un único registro correspondiente a {identity}."
        return "El resultado contiene un único registro."

    if primary_metric and primary_metric in dataframe.columns:
        ordered = dataframe.sort_values(primary_metric, ascending=False, kind="stable")
        top_row = ordered.iloc[0].to_dict()
        identity = _build_row_identity(top_row)
        metric_value = _format_scalar(top_row[primary_metric])
        if identity:
            return f"El valor más alto de `{primary_metric}` corresponde a {identity} con {metric_value}."
        return f"El valor más alto de `{primary_metric}` es {metric_value}."

    return f"El resultado incluye {len(dataframe)} filas listas para comparación."


def format_chart_guidance(chart_spec: ChartSpec | None, no_chart_reason: str | None = None) -> str:
    """Convierte la sugerencia de gráfico en una descripción breve."""

    if chart_spec is None:
        return no_chart_reason or "No se sugirió un gráfico para este resultado."
    return (
        f"Gráfico sugerido: tipo `{chart_spec.chart_type}`, eje X `{chart_spec.x_column}`, "
        f"series `{', '.join(chart_spec.y_columns)}`, título `{chart_spec.title}`."
    )


def _normalize_dataframe_types(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normaliza tipos de columnas para facilitar reportería y gráficos."""

    normalized = dataframe.copy()
    for column in normalized.columns:
        if normalized[column].dtype == "object":
            parsed_time_series = _try_parse_lap_time_series(normalized[column])
            if pd.api.types.is_numeric_dtype(parsed_time_series):
                normalized[column] = parsed_time_series
                continue
            normalized[column] = _try_parse_datetime_series(normalized[column])
    return normalized


def _try_parse_datetime_series(series: pd.Series) -> pd.Series:
    """Convierte una serie a fecha si la mayoría de sus valores parecen fechas."""

    converted = pd.to_datetime(series, errors="coerce")
    if converted.notna().sum() >= max(1, int(len(series) * 0.8)):
        return converted
    return series


def _try_parse_lap_time_series(series: pd.Series) -> pd.Series:
    """Convierte tiempos tipo M:SS.mmm a segundos cuando la mayoría coincide."""

    if series.empty:
        return series

    converted = series.map(_lap_time_to_seconds)
    if converted.notna().sum() >= max(1, int(len(series) * 0.8)):
        return converted
    return series


def _select_primary_metric(dataframe: pd.DataFrame) -> str | None:
    """Selecciona una métrica numérica útil y evita columnas poco informativas."""

    for column in _get_preferred_numeric_columns(dataframe):
        series = dataframe[column]
        if series.nunique(dropna=True) <= 1 and len(dataframe) > 1:
            continue
        return column
    return None


def _get_preferred_numeric_columns(dataframe: pd.DataFrame) -> list[str]:
    """Prioriza métricas útiles y evita usar IDs o años como serie principal."""

    numeric_columns = list(dataframe.select_dtypes(include=["number"]).columns)
    preferred_order = [
        "q3",
        "q2",
        "q1",
        "total_wins",
        "total_points",
        "total_poles",
        "total_podiums",
        "total_races",
        "points",
        "wins",
        "position",
        "position_order",
        "laps",
        "milliseconds",
        "fastest_lap_speed",
        "grid",
    ]

    preferred_columns = [column for column in preferred_order if column in numeric_columns]
    remaining_columns = [
        column
        for column in numeric_columns
        if column not in preferred_columns
        and not column.endswith("_id")
        and column not in {"year", "round", "race_id", "driver_id", "constructor_id"}
    ]
    fallback_columns = [
        column
        for column in numeric_columns
        if column not in preferred_columns + remaining_columns and not column.endswith("_id")
    ]
    return preferred_columns + remaining_columns + fallback_columns


def _get_timeline_columns(dataframe: pd.DataFrame) -> list[str]:
    """Prioriza columnas útiles para series temporales o evolutivas."""

    datetime_columns = list(dataframe.select_dtypes(include=["datetime64[ns]"]).columns)
    preferred_order = ["date", "race_date", "year", "season_year", "round"]
    preferred_columns = [column for column in preferred_order if column in dataframe.columns]
    return preferred_columns + [column for column in datetime_columns if column not in preferred_columns]


def _get_preferred_categorical_columns(
    dataframe: pd.DataFrame,
    excluded_columns: list[str] | None = None,
) -> list[str]:
    """Prioriza columnas categóricas más expresivas para el eje X."""

    excluded = set(excluded_columns or [])
    candidate_columns = [
        column
        for column in dataframe.columns
        if column not in excluded and not pd.api.types.is_numeric_dtype(dataframe[column])
    ]

    preferred_order = [
        "winner",
        "pole_sitter",
        "driver_name",
        "constructor_name",
        "forename",
        "surname",
        "race",
        "name",
        "status",
    ]
    preferred_columns = [column for column in preferred_order if column in candidate_columns]
    remaining_columns = [
        column
        for column in candidate_columns
        if column not in preferred_columns and not column.endswith("_id")
    ]
    return preferred_columns + remaining_columns


def _build_row_identity(row: dict[str, Any]) -> str:
    """Construye una etiqueta breve para una fila de resultado."""

    if row.get("winner"):
        return str(row["winner"])
    if row.get("pole_sitter"):
        return str(row["pole_sitter"])
    if row.get("forename") and row.get("surname"):
        return f"{row['forename']} {row['surname']}"
    if row.get("driver_name"):
        return str(row["driver_name"])
    if row.get("constructor_name"):
        return str(row["constructor_name"])
    if row.get("race"):
        return str(row["race"])
    if row.get("name"):
        return str(row["name"])
    return ""


def _format_scalar(value: Any) -> str:
    """Convierte un valor escalar a texto legible."""

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _lap_time_to_seconds(value: Any) -> float | None:
    """Convierte un tiempo de vuelta M:SS.mmm a segundos."""

    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower().startswith("sin tiempo"):
        return None

    match = pd.Series([text]).str.extract(r"^(?:(\d+):)?(\d{1,2})\.(\d{3})$").iloc[0]
    if match.isna().any():
        return None

    minutes = int(match[0]) if pd.notna(match[0]) else 0
    seconds = int(match[1])
    milliseconds = int(match[2])
    return minutes * 60 + seconds + (milliseconds / 1000)


def _select_present_lap_metric(row: dict[str, Any]) -> str | None:
    """Selecciona una métrica de tiempo presente dentro de una fila."""

    for column in ["q3", "q2", "q1"]:
        if column in row and row[column] is not None and str(row[column]) != "nan":
            return column
    return None
