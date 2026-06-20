"""Enrutamiento heuristico de preguntas hacia tablas y objetivos SQL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SqlIntentHint:
    """Pista estructurada para ayudar a la generacion de SQL."""

    intent_name: str
    target_tables: list[str]
    guidance: str


def infer_sql_intent_hint(user_question: str) -> SqlIntentHint:
    """Infere una pista SQL liviana a partir de palabras clave de la pregunta."""

    normalized_question = user_question.strip().lower()
    ranking_keywords = ["top", "ranking", "mas", "más", "mayores", "menores", "compar", "lista"]
    trend_keywords = ["evolucion", "evolución", "progresion", "progresión", "historia", "a lo largo", "por temporada"]

    if any(keyword in normalized_question for keyword in ranking_keywords):
        return SqlIntentHint(
            intent_name="analytical_ranking",
            target_tables=[
                "results",
                "driver_standings",
                "constructor_standings",
                "qualifying",
                "sprint_results",
                "races",
                "drivers",
                "constructors",
            ],
            guidance=(
                "La pregunta parece comparativa o de ranking. "
                "Devuelve varias filas, usa agregaciones, GROUP BY y ORDER BY cuando corresponda, "
                "y evita LIMIT 1 salvo que la pregunta pida explícitamente solo el primero."
            ),
        )

    if any(keyword in normalized_question for keyword in trend_keywords):
        return SqlIntentHint(
            intent_name="analytical_trend",
            target_tables=[
                "results",
                "driver_standings",
                "constructor_standings",
                "qualifying",
                "sprint_results",
                "races",
                "drivers",
                "constructors",
            ],
            guidance=(
                "La pregunta parece pedir evolución temporal o serie histórica. "
                "Devuelve varias filas, incluye year, date o round cuando ayude, "
                "ordena cronológicamente y evita LIMIT 1 salvo que el usuario lo pida."
            ),
        )

    if any(keyword in normalized_question for keyword in ["pole", "clasificacion", "q1", "q2", "q3"]):
        return SqlIntentHint(
            intent_name="qualifying",
            target_tables=["qualifying", "races", "drivers", "constructors"],
            guidance=(
                "La pregunta parece referirse a clasificacion o pole position. "
                "Prioriza la tabla qualifying en lugar de inferir la pole solo desde la grilla de results."
            ),
        )

    if any(keyword in normalized_question for keyword in ["campeonato", "lider", "standings", "lideraba"]):
        if any(keyword in normalized_question for keyword in ["constructor", "equipo", "escuderia"]):
            return SqlIntentHint(
                intent_name="constructor_standings",
                target_tables=["constructor_standings", "races", "constructors"],
                guidance=(
                    "La pregunta parece referirse al campeonato de constructores. "
                    "Prioriza constructor_standings y usa races para ubicar la carrera o temporada."
                ),
            )
        return SqlIntentHint(
            intent_name="driver_standings",
            target_tables=["driver_standings", "races", "drivers"],
            guidance=(
                "La pregunta parece referirse al campeonato de pilotos. "
                "Prioriza driver_standings y usa races para ubicar la carrera o temporada."
            ),
        )

    if "sprint" in normalized_question:
        return SqlIntentHint(
            intent_name="sprint_results",
            target_tables=["sprint_results", "races", "drivers", "constructors", "status"],
            guidance=(
                "La pregunta parece referirse a una carrera sprint. "
                "Prioriza sprint_results y usa status si se pregunta por abandonos o estados finales."
            ),
        )

    if any(keyword in normalized_question for keyword in ["abandono", "abandono?", "descalificado", "estado", "finished"]):
        return SqlIntentHint(
            intent_name="race_status",
            target_tables=["results", "status", "races", "drivers", "constructors"],
            guidance=(
                "La pregunta parece referirse al estado final de una carrera. "
                "Usa status unido a results para obtener el texto correcto del estado."
            ),
        )

    if any(keyword in normalized_question for keyword in ["gano", "gano?", "resultado", "termino", "podio", "puntos"]):
        return SqlIntentHint(
            intent_name="results",
            target_tables=["results", "races", "drivers", "constructors", "status"],
            guidance=(
                "La pregunta parece referirse a resultados de carrera. "
                "Prioriza la tabla results y une con races, drivers y constructors."
            ),
        )

    return SqlIntentHint(
        intent_name="general_f1_query",
        target_tables=["races", "results", "drivers", "constructors", "circuits"],
        guidance=(
            "La pregunta parece general. Usa las tablas principales y apóyate en el contexto RAG para desambiguar."
        ),
    )
