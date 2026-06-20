"""Capa NL2SQL para generacion de consultas SQL apoyadas por RAG."""

from .entity_resolver import ResolvedEntity, format_resolved_entities, resolve_entities
from .intent_router import SqlIntentHint, infer_sql_intent_hint
from .prompt_builder import build_nl2sql_prompt
from .schema_context import get_default_schema_context, get_schema_context_text
from .sql_generator import generate_sql_query

__all__ = [
    "ResolvedEntity",
    "SqlIntentHint",
    "build_nl2sql_prompt",
    "format_resolved_entities",
    "generate_sql_query",
    "get_default_schema_context",
    "get_schema_context_text",
    "infer_sql_intent_hint",
    "resolve_entities",
]
