"""Capa de base de datos para PostgreSQL."""

from .sql_validator import validate_select_query

__all__ = [
    "validate_select_query",
]
