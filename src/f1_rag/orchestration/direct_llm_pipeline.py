"""Pipeline alternativo para comparar el enfoque hibrido contra LLM puro."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from f1_rag.config import AppConfig
from f1_rag.generation import FinalAnswerResult, generate_direct_llm_answer
from f1_rag.nl2sql import (
    ResolvedEntity,
    SqlIntentHint,
    infer_sql_intent_hint,
    resolve_entities,
    validate_question_guardrails,
)

ProgressCallback = Callable[[str, str, int, int], None]


@dataclass(slots=True)
class DirectLLMPipelineResult:
    """Resultado del modo LLM puro sin recuperacion ni consulta estructurada."""

    question: str
    advisory_message: str | None
    intent_hint: SqlIntentHint
    resolved_entities: list[ResolvedEntity]
    final_answer: FinalAnswerResult
    stage_timings: dict[str, float]


def run_direct_llm_pipeline(
    question: str,
    config: AppConfig | None = None,
    progress_callback: ProgressCallback | None = None,
) -> DirectLLMPipelineResult:
    """Ejecuta una comparacion usando solo el LLM, sin RAG ni SQL."""

    app_config = config or AppConfig.from_env()
    normalized_question = question.strip()
    stage_timings: dict[str, float] = {}
    total_steps = 2

    _emit_progress(
        progress_callback,
        "validation",
        "Validando la pregunta dentro del dominio Formula 1...",
        current_step=1,
        total_steps=total_steps,
    )
    stage_start = perf_counter()
    intent_hint = infer_sql_intent_hint(normalized_question)
    resolved_entities = resolve_entities(normalized_question, config=app_config)
    guard_result = validate_question_guardrails(
        normalized_question,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities,
    )
    stage_timings["validation"] = round(perf_counter() - stage_start, 3)

    _emit_progress(
        progress_callback,
        "llm_only_answer",
        "Generando respuesta directa con LLM puro...",
        current_step=2,
        total_steps=total_steps,
    )
    stage_start = perf_counter()
    final_answer = generate_direct_llm_answer(
        user_question=guard_result.normalized_question,
        config=app_config,
    )
    stage_timings["llm_only_answer"] = round(perf_counter() - stage_start, 3)

    return DirectLLMPipelineResult(
        question=guard_result.normalized_question,
        advisory_message=guard_result.advisory_message,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities,
        final_answer=final_answer,
        stage_timings=stage_timings,
    )


def _emit_progress(
    callback: ProgressCallback | None,
    stage_name: str,
    message: str,
    current_step: int,
    total_steps: int,
) -> None:
    """Emite una notificacion de avance si existe callback de interfaz."""

    if callback is None:
        return
    callback(stage_name, message, current_step, total_steps)
