"""Generacion de SQL a partir de lenguaje natural con apoyo de RAG."""

from __future__ import annotations

import re

from openai import OpenAI

from f1_rag.config import AppConfig
from f1_rag.database.sql_validator import validate_select_query

from .entity_resolver import ResolvedEntity, format_resolved_entities, resolve_entities
from .intent_router import SqlIntentHint, infer_sql_intent_hint
from .prompt_builder import build_nl2sql_prompt
from .schema_context import get_schema_context_text


def generate_sql_query(
    user_question: str,
    rag_context: str,
    schema_context: str | None = None,
    config: AppConfig | None = None,
    intent_hint: SqlIntentHint | None = None,
    resolved_entities: list[ResolvedEntity] | None = None,
) -> str:
    """Genera una consulta SQL SELECT limpia a partir de una pregunta natural."""

    app_config = config or AppConfig.from_env()
    if not app_config.openai_api_key:
        raise ValueError("OPENAI_API_KEY es obligatorio para generar SQL con el modelo.")

    effective_intent_hint = intent_hint or infer_sql_intent_hint(user_question)
    effective_resolved_entities = resolved_entities
    if effective_resolved_entities is None:
        effective_resolved_entities = resolve_entities(user_question, config=app_config)
    effective_schema_context = schema_context or get_schema_context_text()
    prompt = build_nl2sql_prompt(
        user_question=user_question,
        rag_context=rag_context,
        schema_context=effective_schema_context,
        intent_guidance=(
            f"Intento detectado: {effective_intent_hint.intent_name}. "
            f"Tablas prioritarias: {', '.join(effective_intent_hint.target_tables)}. "
            f"{effective_intent_hint.guidance}"
        ),
        entity_context=format_resolved_entities(effective_resolved_entities),
    )

    client = OpenAI(api_key=app_config.openai_api_key)
    try:
        response = client.responses.create(
            model=app_config.sql_generation_model,
            input=prompt,
        )
    except Exception as exc:  # pragma: no cover - depende del entorno externo
        raise RuntimeError(f"La generacion de SQL con OpenAI fallo: {exc}") from exc

    raw_output = getattr(response, "output_text", "").strip()
    if not raw_output:
        raise RuntimeError("El modelo no devolvio ninguna consulta SQL.")

    cleaned_sql = _extract_sql_text(raw_output)
    cleaned_sql = _apply_sql_postprocessing(
        cleaned_sql,
        intent_hint=effective_intent_hint,
        user_question=user_question,
    )
    return validate_select_query(cleaned_sql)


def _extract_sql_text(raw_output: str) -> str:
    """Extrae SQL limpio desde una salida potencialmente envuelta en markdown."""

    fenced_match = re.search(r"```sql\s*(.*?)```", raw_output, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()

    generic_fenced_match = re.search(r"```\s*(.*?)```", raw_output, flags=re.DOTALL)
    if generic_fenced_match:
        return generic_fenced_match.group(1).strip()

    return raw_output.strip()


def _apply_sql_postprocessing(
    sql_text: str,
    intent_hint: SqlIntentHint,
    user_question: str,
) -> str:
    """Aplica ajustes deterministas menores para estabilizar el SQL generado."""

    adjusted_sql = sql_text.strip()

    if intent_hint.intent_name == "analytical_ranking":
        adjusted_sql = _normalize_standings_order_by(
            adjusted_sql,
            user_question=user_question,
        )
        adjusted_sql = _normalize_ranking_order_by(
            adjusted_sql,
            user_question=user_question,
        )

    return adjusted_sql


def _normalize_ranking_order_by(
    sql_text: str,
    user_question: str,
) -> str:
    """Normaliza el desempate de rankings para que use aliases legibles."""

    ranking_aliases = [
        "driver_name",
        "constructor_name",
        "circuit_name",
        "race_name",
    ]

    lowered_sql = sql_text.lower()
    lowered_question = user_question.lower()
    alias_to_use = next((alias for alias in ranking_aliases if re.search(rf"\bas\s+{alias}\b", lowered_sql)), None)
    asks_for_wins = any(
        keyword in lowered_question
        for keyword in ("victorias", "triunfos", "ganadores", "wins", "victory")
    )
    metric_to_use = "total_wins" if asks_for_wins and re.search(r"\btotal_wins\b", lowered_sql) else None

    if alias_to_use is None or metric_to_use is None or "order by" not in lowered_sql:
        return sql_text

    order_by_pattern = re.compile(
        r"order\s+by\s+.+?(?=(\s+limit\b|\s+offset\b|$))",
        flags=re.IGNORECASE | re.DOTALL,
    )
    replacement = f"ORDER BY {metric_to_use} DESC, {alias_to_use} ASC"
    return order_by_pattern.sub(replacement, sql_text, count=1)


def _normalize_standings_order_by(
    sql_text: str,
    user_question: str,
) -> str:
    """Fuerza orden estable por posicion en preguntas de standings del campeonato."""

    lowered_sql = sql_text.lower()
    lowered_question = user_question.lower()

    asks_for_standings = any(
        keyword in lowered_question
        for keyword in ("campeonato", "standings", "clasificacion", "ranking")
    )
    asks_for_points = any(
        keyword in lowered_question
        for keyword in ("puntos", "point", "pts")
    )

    if not asks_for_standings or not asks_for_points or "order by" not in lowered_sql:
        return sql_text

    if "from driver_standings" in lowered_sql and "ds.position" in lowered_sql:
        replacement = "ORDER BY ds.position"
    elif "from constructor_standings" in lowered_sql and "cs.position" in lowered_sql:
        replacement = "ORDER BY cs.position"
    else:
        return sql_text

    order_by_pattern = re.compile(
        r"order\s+by\s+.+?(?=(\s+limit\b|\s+offset\b|$))",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return order_by_pattern.sub(replacement, sql_text, count=1)
