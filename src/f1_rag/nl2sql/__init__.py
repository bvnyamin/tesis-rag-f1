"""Capa NL2SQL para generacion de consultas SQL apoyadas por RAG."""

from .entity_resolver import ResolvedEntity, format_resolved_entities, resolve_entities
from .intent_router import SqlIntentHint, infer_sql_intent_hint
from .prompt_builder import build_nl2sql_prompt
from .question_guard import (
    OutOfDomainQuestionError,
    QuestionGuardResult,
    UnsafeQuestionError,
    validate_question_guardrails,
    validate_user_question_safety,
)
from .schema_context import get_default_schema_context, get_schema_context_text
from .sql_generator import generate_sql_query

__all__ = [
    "OutOfDomainQuestionError",
    "QuestionGuardResult",
    "ResolvedEntity",
    "SqlIntentHint",
    "UnsafeQuestionError",
    "build_nl2sql_prompt",
    "format_resolved_entities",
    "generate_sql_query",
    "get_default_schema_context",
    "get_schema_context_text",
    "infer_sql_intent_hint",
    "resolve_entities",
    "validate_question_guardrails",
    "validate_user_question_safety",
]
