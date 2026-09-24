"""Guardas de seguridad y dominio para preguntas antes de NL2SQL."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .entity_resolver import ResolvedEntity
from .intent_router import SqlIntentHint


class UnsafeQuestionError(ValueError):
    """Error lanzado cuando la pregunta del usuario implica una accion no permitida."""


class OutOfDomainQuestionError(ValueError):
    """Error lanzado cuando la pregunta parece estar fuera del dominio Formula 1."""


@dataclass(slots=True)
class QuestionGuardResult:
    """Resultado de las validaciones previas sobre la pregunta del usuario."""

    normalized_question: str
    advisory_message: str | None = None


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
    r"\bagrega(r)?\b.*\b(dato|datos|registro|registros|fila|filas)\b",
    r"\bagrega(r)?\b.*\b(en|a)\b.*\b(tabla|races|drivers|constructors|results|circuits)\b",
    r"\bañade\b.*\b(dato|datos|registro|registros|fila|filas)\b",
    r"\bmete\b.*\b(en|a)\b.*\b(tabla|races|drivers|constructors|results|circuits)\b",
    r"\bcarga\b.*\b(dato|datos|registro|registros|fila|filas)\b",
    r"\bagrega(r)?\b.*\bcolumna\b",
    r"\bcrear?\b.*\bregistro\b",
    r"\bcrea(r)?\b.*\btabla\b",
    r"\balter table\b",
    r"\bdrop table\b",
    r"\btruncate\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\binsert\b",
)

BLOCKED_PROMPT_INJECTION_PATTERNS = (
    r"\bignora(r)?\b.*\b(instrucciones|reglas|restricciones|guardas)\b",
    r"\bomite\b.*\b(validacion|validación|seguridad|reglas)\b",
    r"\bsystem prompt\b",
    r"\bprompt del sistema\b",
    r"\bdeveloper message\b",
    r"\bcredenciales?\b",
    r"\bapi[_\s-]?key\b",
    r"\btoken\b.*\b(openai|github|api)\b",
    r"\bsecret(s|o)?\b",
)

F1_DOMAIN_KEYWORDS = {
    "formula 1",
    "f1",
    "grand prix",
    "gp",
    "piloto",
    "pilotos",
    "escuderia",
    "escuderia",
    "escuderias",
    "constructor",
    "constructores",
    "circuit",
    "circuito",
    "circuitos",
    "carrera",
    "carreras",
    "temporada",
    "temporadas",
    "campeonato",
    "campeon",
    "campeones",
    "victoria",
    "victorias",
    "pole",
    "poles",
    "clasificacion",
    "clasificación",
    "qualifying",
    "sprint",
    "podio",
    "podios",
    "parrilla",
    "grilla",
    "vueltas",
    "race",
    "races",
    "driver",
    "drivers",
    "results",
    "standings",
    "pole position",
}


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

    for pattern in BLOCKED_PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lowered_question):
            raise UnsafeQuestionError(
                "La solicitud fue bloqueada porque intenta eludir las reglas de seguridad o acceder a datos sensibles. "
                "Solo se permiten consultas de lectura sobre el dataset de Formula 1."
            )

    return normalized_question


def validate_question_guardrails(
    question: str,
    intent_hint: SqlIntentHint | None = None,
    resolved_entities: list[ResolvedEntity] | None = None,
) -> QuestionGuardResult:
    """Ejecuta validaciones de seguridad y relevancia de dominio en una sola pasada."""

    normalized_question = validate_user_question_safety(question)
    advisory_message = build_domain_advisory_message(
        normalized_question,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities or [],
    )
    return QuestionGuardResult(
        normalized_question=normalized_question,
        advisory_message=advisory_message,
    )


def build_domain_advisory_message(
    question: str,
    intent_hint: SqlIntentHint | None = None,
    resolved_entities: list[ResolvedEntity] | None = None,
) -> str | None:
    """Valida si la pregunta cae dentro del dominio F1 y genera un mensaje claro si no."""

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("La pregunta del usuario no puede estar vacia.")

    lowered_question = normalized_question.lower()
    entities = resolved_entities or []
    if entities:
        return None

    if any(keyword in lowered_question for keyword in F1_DOMAIN_KEYWORDS):
        return None

    if intent_hint is not None and _looks_like_f1_statistical_question(lowered_question):
        return None

    raise OutOfDomainQuestionError(
        "La pregunta parece estar fuera del dominio de Formula 1. "
        "Este sistema esta especializado en pilotos, escuderias, circuitos, carreras, resultados y temporadas del dataset F1. "
        "Si intentara responder, solo podria ofrecer una interpretacion cercana y no una respuesta confiable."
    )


def _looks_like_f1_statistical_question(lowered_question: str) -> bool:
    """Permite preguntas generales del dominio aunque no nombren F1 de forma explicita."""

    statistical_keywords = (
        "gano",
        "gano?",
        "ganó",
        "quien gano",
        "quien hizo la pole",
        "quien hizo pole",
        "lideraba",
        "campeones",
        "campeon",
        "campeón",
        "puntos",
        "victorias",
        "poles",
        "promedio",
        "top 10",
        "compara",
        "evolucion",
        "evolución",
    )
    return any(keyword in lowered_question for keyword in statistical_keywords)
