"""Construccion de prompts para generar SQL a partir de lenguaje natural."""

from __future__ import annotations


def build_nl2sql_prompt(
    user_question: str,
    rag_context: str,
    schema_context: str,
    intent_guidance: str | None = None,
    entity_context: str | None = None,
) -> str:
    """Construye el prompt que guia al modelo para producir SQL seguro."""

    normalized_question = user_question.strip()
    if not normalized_question:
        raise ValueError("La pregunta del usuario no puede estar vacia.")

    normalized_rag_context = rag_context.strip() or "No se recupero contexto adicional."
    normalized_schema_context = schema_context.strip()
    if not normalized_schema_context:
        raise ValueError("El contexto de esquema SQL no puede estar vacio.")
    normalized_intent_guidance = intent_guidance.strip() if intent_guidance else "Sin pista heuristica adicional."
    normalized_entity_context = entity_context.strip() if entity_context else "No se resolvieron entidades adicionales."

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
- Si la pregunta es comparativa, ranking o evolucion temporal, devuelve varias filas utiles para analisis; no fuerces LIMIT 1.
- Si la pregunta pide top, ranking, mas, menos o comparacion, considera GROUP BY, agregaciones y ORDER BY.
- Si la pregunta pide evolucion o serie historica, incluye year, date o round para que la salida se pueda graficar.
- Si la pregunta se refiere a ganadores, usa posicion 1 o position_order = 1 cuando corresponda.
- Si la pregunta pide pole position o clasificacion, prioriza la tabla qualifying.
- Si la pregunta pide lider del campeonato, posicion en el campeonato o puntos acumulados despues de una carrera, usa driver_standings o constructor_standings.
- Si la pregunta se refiere a sprint, usa sprint_results.
- Si la pregunta pide estado final, abandono o descalificacion, considera la tabla status unida a results o sprint_results.
- Si el contexto recuperado aclara nombres de pilotos, escuderias, circuitos o carreras, usalo.
- No escribas explicaciones, markdown ni bloques de codigo.
- Usa aliases legibles para columnas clave, por ejemplo driver_name, constructor_name, race_name, season_year, total_points o total_wins cuando ayuden a interpretar el resultado.

Pregunta del usuario:
{normalized_question}

Contexto recuperado por RAG:
{normalized_rag_context}

Pista heuristica para esta pregunta:
{normalized_intent_guidance}

Entidades resueltas:
{normalized_entity_context}

Contexto del esquema SQL:
{normalized_schema_context}
""".strip()
