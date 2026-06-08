"""Generacion de respuesta final en lenguaje natural para el pipeline hibrido."""

from __future__ import annotations

from datetime import date, datetime
import json
from dataclasses import dataclass

from openai import OpenAI

from f1_rag.config import AppConfig
from f1_rag.database.query_executor import QueryExecutionResult


@dataclass(slots=True)
class FinalAnswerResult:
    """Respuesta final producida a partir de SQL y contexto recuperado."""

    answer: str
    prompt: str


def generate_final_response(
    user_question: str,
    rag_context: str,
    sql_query: str,
    sql_result: QueryExecutionResult,
    config: AppConfig | None = None,
) -> FinalAnswerResult:
    """Genera una respuesta final en lenguaje natural para el usuario."""

    app_config = config or AppConfig.from_env()
    if not app_config.openai_api_key:
        raise ValueError("OPENAI_API_KEY es obligatorio para generar la respuesta final.")

    prompt = build_final_response_prompt(
        user_question=user_question,
        rag_context=rag_context,
        sql_query=sql_query,
        sql_result=sql_result,
    )

    client = OpenAI(api_key=app_config.openai_api_key)
    try:
        response = client.responses.create(
            model=app_config.final_response_model,
            input=prompt,
        )
    except Exception as exc:  # pragma: no cover - depende del entorno externo
        raise RuntimeError(f"La generacion de la respuesta final fallo: {exc}") from exc

    answer = getattr(response, "output_text", "").strip()
    if not answer:
        raise RuntimeError("El modelo no devolvio una respuesta final.")

    return FinalAnswerResult(answer=answer, prompt=prompt)


def build_final_response_prompt(
    user_question: str,
    rag_context: str,
    sql_query: str,
    sql_result: QueryExecutionResult,
) -> str:
    """Construye el prompt para responder al usuario con evidencia estructurada."""

    compact_rows = sql_result.rows[:20]
    sql_result_payload = {
        "columns": sql_result.columns,
        "row_count": sql_result.row_count,
        "rows": _make_json_safe(compact_rows),
    }

    return f"""
Eres un asistente de analisis de Formula 1.

Tu tarea es responder la pregunta del usuario usando:
- el contexto recuperado por RAG
- la consulta SQL generada
- el resultado real de esa consulta

Reglas:
- Responde en espanol claro y preciso.
- Basa tu respuesta en la evidencia disponible.
- Si el resultado SQL esta vacio, dilo explicitamente.
- No inventes datos que no aparezcan en el contexto o en el resultado SQL.
- Si es util, menciona nombres de pilotos, carreras, escuderias y temporadas.
- No menciones el prompt ni hables de ti mismo.

Pregunta del usuario:
{user_question.strip()}

Contexto recuperado por RAG:
{rag_context.strip() or "No se recupero contexto adicional."}

Consulta SQL ejecutada:
{sql_query.strip()}

Resultado SQL:
{json.dumps(sql_result_payload, ensure_ascii=True, indent=2)}
""".strip()


def _make_json_safe(value: object) -> object:
    """Convierte resultados SQL a un formato serializable para el prompt final."""

    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
