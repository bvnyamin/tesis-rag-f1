"""Pruebas simples para la validacion de consultas SQL."""

from __future__ import annotations

import pytest

from f1_rag.database.sql_validator import validate_select_query


def test_accepts_basic_select() -> None:
    """Permite una consulta SELECT simple."""

    validated = validate_select_query("SELECT * FROM drivers;")
    assert validated == "SELECT * FROM drivers"


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE drivers SET surname = 'Test'",
        "DELETE FROM results",
        "INSERT INTO drivers (driver_id) VALUES (9999)",
        "DROP TABLE drivers",
        "ALTER TABLE races ADD COLUMN temp TEXT",
        "TRUNCATE TABLE results",
        "SELECT * FROM drivers; DELETE FROM drivers",
    ],
)
def test_rejects_blocked_or_multiple_statements(query: str) -> None:
    """Bloquea escritura, DDL y multiples statements."""

    with pytest.raises(ValueError):
        validate_select_query(query)


def test_rejects_non_select_statement() -> None:
    """Bloquea consultas que no comienzan con SELECT."""

    with pytest.raises(ValueError):
        validate_select_query("WITH cte AS (SELECT 1) SELECT * FROM cte")
