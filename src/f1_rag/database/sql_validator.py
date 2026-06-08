"""Validacion basica de consultas SQL para ejecucion segura."""

from __future__ import annotations

import re


BLOCKED_KEYWORDS = {
    "update",
    "delete",
    "insert",
    "drop",
    "alter",
    "truncate",
}


def validate_select_query(query: str) -> str:
    """Valida que una consulta sea un unico statement SELECT seguro.

    Reglas:
    - solo se permite SELECT
    - se bloquean palabras clave destructivas o de escritura
    - se bloquean multiples statements
    """

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("La consulta SQL no puede estar vacia.")

    query_without_trailing_semicolon = normalized_query.rstrip(";").strip()
    if not query_without_trailing_semicolon:
        raise ValueError("La consulta SQL no puede estar vacia.")

    if ";" in query_without_trailing_semicolon:
        raise ValueError("No se permiten multiples statements SQL.")

    lowered_query = query_without_trailing_semicolon.lower()
    if not lowered_query.startswith("select"):
        raise ValueError("Solo se permiten consultas SQL que comiencen con SELECT.")

    blocked_pattern = r"\b(" + "|".join(sorted(BLOCKED_KEYWORDS)) + r")\b"
    if re.search(blocked_pattern, lowered_query):
        raise ValueError("La consulta contiene palabras clave SQL bloqueadas.")

    return query_without_trailing_semicolon
