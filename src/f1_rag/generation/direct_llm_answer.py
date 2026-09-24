"""Generacion de respuesta directa con LLM, sin RAG ni consulta SQL."""

from __future__ import annotations

from openai import OpenAI

from f1_rag.config import AppConfig

from .final_response import FinalAnswerResult


def generate_direct_llm_answer(
    user_question: str,
    config: AppConfig | None = None,
) -> FinalAnswerResult:
    """Genera una respuesta directa usando solo el modelo de lenguaje."""

    app_config = config or AppConfig.from_env()
    if not app_config.openai_api_key:
        raise ValueError("OPENAI_API_KEY es obligatorio para generar la respuesta directa con LLM.")

    prompt = build_direct_llm_prompt(user_question)
    client = OpenAI(api_key=app_config.openai_api_key)

    try:
        response = client.responses.create(
            model=app_config.final_response_model,
            input=prompt,
        )
    except Exception as exc:  # pragma: no cover - depende del entorno externo
        raise RuntimeError(f"La generacion de la respuesta directa con LLM fallo: {exc}") from exc

    answer = getattr(response, "output_text", "").strip()
    if not answer:
        raise RuntimeError("El modelo no devolvio una respuesta en modo LLM puro.")

    return FinalAnswerResult(answer=answer, prompt=prompt)


def build_direct_llm_prompt(user_question: str) -> str:
    """Construye el prompt para comparar un modo LLM puro con el enfoque hibrido."""

    return f"""
Eres un asistente conversacional general.

Responderas una pregunta sobre Formula 1 usando solo tu conocimiento general.
No tienes acceso a PostgreSQL, Chroma, SQL, archivos locales ni fuentes externas activas.

Reglas:
- Responde en espanol claro y breve.
- Si no estas seguro de un dato exacto, dilo explicitamente.
- No inventes que consultaste una base de datos o evidencia.
- No muestres SQL.
- No agregues tablas ni secciones extra.
- Si corresponde, puedes indicar que la respuesta es tentativa porque no hubo verificacion contra datos reales.

Pregunta:
{user_question.strip()}
""".strip()
