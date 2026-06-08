"""Ejecucion segura de consultas SELECT sobre PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from f1_rag.config import AppConfig

from .connection import create_connection
from .sql_validator import validate_select_query


@dataclass(slots=True)
class QueryExecutionResult:
    """Resultado estructurado de una consulta SELECT."""

    query: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


def execute_select_query(query: str, config: AppConfig | None = None) -> QueryExecutionResult:
    """Valida y ejecuta una consulta SELECT en PostgreSQL."""

    app_config = config or AppConfig.from_env()
    validated_query = validate_select_query(query)

    try:
        with create_connection(app_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(validated_query)
                raw_rows = cursor.fetchall()
                columns = [description.name for description in cursor.description or []]
    except Exception as exc:  # pragma: no cover - depende de la BD y el entorno
        raise RuntimeError(f"La ejecucion de la consulta SQL fallo: {exc}") from exc

    rows = [dict(zip(columns, row)) for row in raw_rows]
    return QueryExecutionResult(
        query=validated_query,
        columns=columns,
        rows=rows,
        row_count=len(rows),
    )
