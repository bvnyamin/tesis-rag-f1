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
