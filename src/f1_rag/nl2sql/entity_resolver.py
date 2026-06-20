"""Resolucion simple de entidades para mejorar la generacion de SQL."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from f1_rag.config import AppConfig
from f1_rag.database.connection import create_connection


@dataclass(slots=True)
class ResolvedEntity:
    """Entidad resuelta desde la pregunta del usuario."""

    entity_type: str
    display_name: str
    canonical_value: str
    match_reason: str


def resolve_entities(
    user_question: str,
    config: AppConfig | None = None,
) -> list[ResolvedEntity]:
    """Resuelve entidades conocidas de F1 presentes en una pregunta."""

    app_config = config or AppConfig.from_env()
    normalized_question = _normalize_text(user_question)
    if not normalized_question:
        return []

    try:
        with create_connection(app_config) as connection:
            drivers = _fetch_drivers(connection)
            races = _fetch_races(connection)
            circuits = _fetch_circuits(connection)
            constructors = _fetch_constructors(connection)
    except Exception:
        # Si la resolucion falla, dejamos que el pipeline siga con el flujo actual.
        return []

    resolved_entities: list[ResolvedEntity] = []
    for entity in drivers + races + circuits + constructors:
        if _matches_entity(normalized_question, entity):
            resolved_entities.append(entity)

    return _deduplicate_entities(resolved_entities)


def format_resolved_entities(entities: list[ResolvedEntity]) -> str:
    """Convierte entidades resueltas en un bloque de texto para el prompt."""

    if not entities:
        return "No se resolvieron entidades canonicas adicionales."

    lines = ["Entidades resueltas desde la pregunta:"]
    for entity in entities:
        lines.append(
            f"- {entity.entity_type}: {entity.display_name} "
            f"(valor canonico: {entity.canonical_value}; motivo: {entity.match_reason})"
        )
    return "\n".join(lines)


def _fetch_drivers(connection) -> list[ResolvedEntity]:
    """Recupera pilotos para matching de nombres."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT driver_ref, forename, surname
            FROM drivers
            """
        )
        rows = cursor.fetchall()

    entities: list[ResolvedEntity] = []
    for driver_ref, forename, surname in rows:
        display_name = f"{forename} {surname}"
        entities.append(
            ResolvedEntity(
                entity_type="driver",
                display_name=display_name,
                canonical_value=str(driver_ref),
                match_reason=_build_match_key(display_name, driver_ref),
            )
        )
    return entities


def _fetch_races(connection) -> list[ResolvedEntity]:
    """Recupera carreras para matching de nombres."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT year, name
            FROM races
            """
        )
        rows = cursor.fetchall()

    entities: list[ResolvedEntity] = []
    for year, name in rows:
        display_name = f"{name} {year}"
        entities.append(
            ResolvedEntity(
                entity_type="race",
                display_name=display_name,
                canonical_value=str(name),
                match_reason=_build_match_key(display_name, name, str(year)),
            )
        )
    return entities


def _fetch_circuits(connection) -> list[ResolvedEntity]:
    """Recupera circuitos para matching de nombres."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT circuit_ref, name
            FROM circuits
            """
        )
        rows = cursor.fetchall()

    entities: list[ResolvedEntity] = []
    for circuit_ref, name in rows:
        entities.append(
            ResolvedEntity(
                entity_type="circuit",
                display_name=str(name),
                canonical_value=str(name),
                match_reason=_build_match_key(name, circuit_ref),
            )
        )
    return entities


def _fetch_constructors(connection) -> list[ResolvedEntity]:
    """Recupera escuderias para matching de nombres."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT constructor_ref, name
            FROM constructors
            """
        )
        rows = cursor.fetchall()

    entities: list[ResolvedEntity] = []
    for constructor_ref, name in rows:
        entities.append(
            ResolvedEntity(
                entity_type="constructor",
                display_name=str(name),
                canonical_value=str(name),
                match_reason=_build_match_key(name, constructor_ref),
            )
        )
    return entities


def _matches_entity(normalized_question: str, entity: ResolvedEntity) -> bool:
    """Determina si una entidad parece estar mencionada en la pregunta."""

    normalized_display = _normalize_text(entity.display_name)
    normalized_canonical = _normalize_text(entity.canonical_value)

    display_tokens = _significant_tokens(normalized_display)
    if display_tokens and all(token in normalized_question for token in display_tokens):
        return True

    if normalized_canonical and normalized_canonical in normalized_question:
        return True

    if entity.entity_type == "race":
        race_tokens = [token for token in display_tokens if token not in {"grand", "prix"}]
        if race_tokens and all(token in normalized_question for token in race_tokens):
            return True

    return False


def _deduplicate_entities(entities: list[ResolvedEntity]) -> list[ResolvedEntity]:
    """Elimina entidades duplicadas manteniendo el orden."""

    seen: set[tuple[str, str]] = set()
    deduplicated: list[ResolvedEntity] = []
    for entity in entities:
        key = (entity.entity_type, entity.canonical_value)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(entity)
    return deduplicated


def _normalize_text(value: str) -> str:
    """Normaliza texto para matching insensible a acentos."""

    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_accents.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _significant_tokens(value: str) -> list[str]:
    """Obtiene tokens significativos para matching sencillo."""

    return [token for token in value.split() if len(token) >= 4]


def _build_match_key(*parts: object) -> str:
    """Construye una explicacion breve del criterio de matching."""

    values = [str(part) for part in parts if part]
    return "coincidencia con " + " / ".join(values[:3])
