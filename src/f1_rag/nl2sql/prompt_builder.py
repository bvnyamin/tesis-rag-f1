"""Construccion de prompts para generar SQL a partir de lenguaje natural."""

from __future__ import annotations


def build_nl2sql_prompt(
    user_question: str,
    rag_context: str,
    schema_context: str,
) -> str:
    """Construye el prompt que guia al modelo para producir SQL seguro."""

    normalized_question = user_question.strip()
    if not normalized_question:
        raise ValueError("La pregunta del usuario no puede estar vacia.")

    normalized_rag_context = rag_context.strip() or "No se recupero contexto adicional."
    normalized_schema_context = schema_context.strip()
    if not normalized_schema_context:
        raise ValueError("El contexto de esquema SQL no puede estar vacio.")

    return f"""
Eres un asistente experto en SQL para PostgreSQL y analisis de Formula 1.

Tu tarea es convertir la pregunta del usuario en una consulta SQL valida y util
para el esquema disponible.

Reglas obligatorias:
- Devuelve solo una consulta SQL.
- La consulta debe comenzar con SELECT.
- No uses UPDATE, DELETE, INSERT, DROP, ALTER ni TRUNCATE.
- No generes multiples statements.
- Usa solo tablas y columnas presentes en el esquema.
- Si necesitas unir tablas, usa joins explicitos.
- Si la pregunta pide pocas filas o ejemplos, agrega LIMIT.
- Si la pregunta se refiere a ganadores, usa posicion 1 o position_order = 1 cuando corresponda.
- Si el contexto recuperado aclara nombres de pilotos, escuderias, circuitos o carreras, usalo.
- No escribas explicaciones, markdown ni bloques de codigo.

Pregunta del usuario:
{normalized_question}

Contexto recuperado por RAG:
{normalized_rag_context}

Contexto del esquema SQL:
{normalized_schema_context}
""".strip()
