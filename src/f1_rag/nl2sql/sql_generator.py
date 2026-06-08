"""Generacion de SQL a partir de lenguaje natural con apoyo de RAG."""

from __future__ import annotations

import re

from openai import OpenAI

from f1_rag.config import AppConfig
from f1_rag.database.sql_validator import validate_select_query

from .prompt_builder import build_nl2sql_prompt
from .schema_context import get_schema_context_text


def generate_sql_query(
    user_question: str,
    rag_context: str,
    schema_context: str | None = None,
    config: AppConfig | None = None,
) -> str:
    """Genera una consulta SQL SELECT limpia a partir de una pregunta natural."""

    app_config = config or AppConfig.from_env()
    if not app_config.openai_api_key:
        raise ValueError("OPENAI_API_KEY es obligatorio para generar SQL con el modelo.")

    effective_schema_context = schema_context or get_schema_context_text()
    prompt = build_nl2sql_prompt(
        user_question=user_question,
        rag_context=rag_context,
        schema_context=effective_schema_context,
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
