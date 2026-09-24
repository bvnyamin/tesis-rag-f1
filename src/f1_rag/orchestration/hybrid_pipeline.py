"""Pipeline hibrido completo: RAG + SQL + respuesta final."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from f1_rag.config import AppConfig
from f1_rag.database.query_executor import QueryExecutionResult, execute_select_query
from f1_rag.database.sql_validator import validate_select_query
from f1_rag.generation import FinalAnswerResult, generate_final_response
from f1_rag.nl2sql import (
    ResolvedEntity,
    SqlIntentHint,
    generate_sql_query,
    get_schema_context_text,
    infer_sql_intent_hint,
    resolve_entities,
    validate_question_guardrails,
)
from f1_rag.retrieval import RetrievedChunk, format_retrieved_context, retrieve_context
from f1_rag.ui import QueryReport, build_query_report

ProgressCallback = Callable[[str, str, int, int], None]


@dataclass(slots=True)
class HybridPipelineResult:
    """Resultado consolidado del pipeline hibrido end-to-end."""

    question: str
    advisory_message: str | None
    retrieved_chunks: list[RetrievedChunk]
    rag_context: str
    intent_hint: SqlIntentHint
    resolved_entities: list[ResolvedEntity]
    schema_context: str
    generated_sql: str
    query_result: QueryExecutionResult
    query_report: QueryReport
    final_answer: FinalAnswerResult | None
    stage_timings: dict[str, float]


def run_hybrid_pipeline(
    question: str,
    config: AppConfig | None = None,
    top_k: int | None = None,
    enable_rag: bool = True,
    enable_final_response: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> HybridPipelineResult:
    """Ejecuta el flujo completo de pregunta a respuesta final."""

    app_config = config or AppConfig.from_env()
    normalized_question = question.strip()
    stage_timings: dict[str, float] = {}
    total_steps = 6 if enable_rag and enable_final_response else 5 if enable_rag else 4 if enable_final_response else 4

    _emit_progress(
        progress_callback,
        "validation",
        "Validando la pregunta y resolviendo entidades...",
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
    if enable_rag:
        _emit_progress(
            progress_callback,
            "retrieval",
            "Recuperando contexto RAG desde Chroma...",
            current_step=2,
            total_steps=total_steps,
        )
        stage_start = perf_counter()
        retrieved_chunks = retrieve_context(
            guard_result.normalized_question,
            config=app_config,
            top_k=top_k,
            intent_hint=intent_hint,
            resolved_entities=resolved_entities,
        )
        rag_context = format_retrieved_context(retrieved_chunks)
        stage_timings["retrieval"] = round(perf_counter() - stage_start, 3)
    else:
        retrieved_chunks = []
        rag_context = "No se recupero contexto adicional (modo linea base sin RAG)."
    schema_context = get_schema_context_text()

    _emit_progress(
        progress_callback,
        "sql_generation",
        "Generando SQL a partir de la pregunta...",
        current_step=3 if enable_rag else 2,
        total_steps=total_steps,
    )
    stage_start = perf_counter()
    generated_sql = generate_sql_query(
        user_question=guard_result.normalized_question,
        rag_context=rag_context,
        schema_context=schema_context,
        config=app_config,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities,
    )
    stage_timings["sql_generation"] = round(perf_counter() - stage_start, 3)

    _emit_progress(
        progress_callback,
        "sql_validation",
        "Validando la consulta SQL generada...",
        current_step=4 if enable_rag else 3,
        total_steps=total_steps,
    )
    stage_start = perf_counter()
    validated_sql = validate_select_query(generated_sql)
    stage_timings["sql_validation"] = round(perf_counter() - stage_start, 3)

    _emit_progress(
        progress_callback,
        "sql_execution",
        "Consultando PostgreSQL...",
        current_step=5 if enable_rag else 4,
        total_steps=total_steps,
    )
    stage_start = perf_counter()
    query_result = execute_select_query(validated_sql, config=app_config)
    stage_timings["sql_execution"] = round(perf_counter() - stage_start, 3)
    query_report = build_query_report(query_result)

    final_answer: FinalAnswerResult | None = None
    if enable_final_response:
        _emit_progress(
            progress_callback,
            "final_response",
            "Generando la respuesta final...",
            current_step=6 if enable_rag else 4,
            total_steps=total_steps,
        )
        stage_start = perf_counter()
        final_answer = generate_final_response(
            user_question=guard_result.normalized_question,
            rag_context=rag_context,
            sql_query=validated_sql,
            sql_result=query_result,
            query_report=query_report,
            config=app_config,
        )
        stage_timings["final_response"] = round(perf_counter() - stage_start, 3)

    return HybridPipelineResult(
        question=guard_result.normalized_question,
        advisory_message=guard_result.advisory_message,
        retrieved_chunks=retrieved_chunks,
        rag_context=rag_context,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities,
        schema_context=schema_context,
        generated_sql=validated_sql,
        query_result=query_result,
        query_report=query_report,
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
    """Emite una notificacion de avance si la interfaz registró un callback."""

    if callback is None:
        return
    callback(stage_name, message, current_step, total_steps)
