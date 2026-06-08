"""Pipeline hibrido completo: RAG + SQL + respuesta final."""

from __future__ import annotations

from dataclasses import dataclass

from f1_rag.config import AppConfig
from f1_rag.database.query_executor import QueryExecutionResult, execute_select_query
from f1_rag.database.sql_validator import validate_select_query
from f1_rag.generation import FinalAnswerResult, generate_final_response
from f1_rag.nl2sql import generate_sql_query, get_schema_context_text
from f1_rag.retrieval import RetrievedChunk, format_retrieved_context, retrieve_context


@dataclass(slots=True)
class HybridPipelineResult:
    """Resultado consolidado del pipeline hibrido end-to-end."""

    question: str
    retrieved_chunks: list[RetrievedChunk]
    rag_context: str
    schema_context: str
    generated_sql: str
    query_result: QueryExecutionResult
    final_answer: FinalAnswerResult


def run_hybrid_pipeline(
    question: str,
    config: AppConfig | None = None,
    top_k: int | None = None,
) -> HybridPipelineResult:
    """Ejecuta el flujo completo de pregunta a respuesta final."""

    app_config = config or AppConfig.from_env()
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("La pregunta del usuario no puede estar vacia.")

    retrieved_chunks = retrieve_context(normalized_question, config=app_config, top_k=top_k)
    rag_context = format_retrieved_context(retrieved_chunks)
    schema_context = get_schema_context_text()

    generated_sql = generate_sql_query(
        user_question=normalized_question,
        rag_context=rag_context,
        schema_context=schema_context,
        config=app_config,
    )
    validated_sql = validate_select_query(generated_sql)
    query_result = execute_select_query(validated_sql, config=app_config)
    final_answer = generate_final_response(
        user_question=normalized_question,
        rag_context=rag_context,
        sql_query=validated_sql,
        sql_result=query_result,
        config=app_config,
    )

    return HybridPipelineResult(
        question=normalized_question,
        retrieved_chunks=retrieved_chunks,
        rag_context=rag_context,
        schema_context=schema_context,
        generated_sql=validated_sql,
        query_result=query_result,
        final_answer=final_answer,
    )
