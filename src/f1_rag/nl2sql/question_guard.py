"""Guardas de seguridad para preguntas en lenguaje natural antes de NL2SQL."""

from __future__ import annotations

import re


class UnsafeQuestionError(ValueError):
    """Error lanzado cuando la pregunta del usuario implica una accion no permitida."""


BLOCKED_SQL_KEYWORDS = (
    "delete",
    "drop",
    "update",
    "insert",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
)

BLOCKED_NL_PATTERNS = (
    r"\belimina(r)?\b",
    r"\bborra(r)?\b",
    r"\bborrar\b",
    r"\bmodifica(r)?\b",
    r"\bactualiza(r)?\b",
    r"\binserta(r)?\b",
    r"\bagrega(r)?\b.*\bcolumna\b",
    r"\bcrea(r)?\b.*\btabla\b",
    r"\balter table\b",
    r"\bdrop table\b",
    r"\btruncate\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\binsert\b",
)


def validate_user_question_safety(question: str) -> str:
    """Valida que la pregunta del usuario sea solo de lectura.

    Reglas:
    - bloquea intenciones destructivas o de escritura expresadas en español o SQL
    - bloquea intentos de inyección con múltiples statements
    - permite únicamente preguntas orientadas a consulta/lectura
    """

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("La pregunta del usuario no puede estar vacia.")

    lowered_question = normalized_question.lower()

    # Bloquea múltiples statements o payloads híbridos tipo "muestrame X; DROP TABLE Y".
    if ";" in lowered_question:
        trailing_segments = [segment.strip() for segment in lowered_question.split(";") if segment.strip()]
        if len(trailing_segments) > 1:
            raise UnsafeQuestionError(
                "La solicitud fue bloqueada porque contiene múltiples instrucciones o un posible intento de inyección SQL."
            )

    blocked_sql_pattern = r"\b(" + "|".join(BLOCKED_SQL_KEYWORDS) + r")\b"
    if re.search(blocked_sql_pattern, lowered_question):
        raise UnsafeQuestionError(
            "La solicitud fue bloqueada porque intenta modificar la base de datos. Solo se permiten consultas de lectura."
        )

    for pattern in BLOCKED_NL_PATTERNS:
        if re.search(pattern, lowered_question):
            raise UnsafeQuestionError(
                "La solicitud fue bloqueada porque implica una acción no permitida sobre la base de datos. "
                "Solo se permiten consultas de lectura."
            )

    return normalized_question
