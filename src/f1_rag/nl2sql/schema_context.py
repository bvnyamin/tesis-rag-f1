"""Contexto de esquema SQL para apoyar la generacion de consultas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TableSchemaContext:
    """Representa una tabla relevante para la generacion de SQL."""

    table_name: str
    description: str
    columns: list[str]
    joins: list[str]


def get_default_schema_context() -> list[TableSchemaContext]:
    """Devuelve un resumen curado del esquema minimo de F1 en PostgreSQL."""

    return [
        TableSchemaContext(
            table_name="drivers",
            description="Pilotos de Formula 1.",
            columns=[
                "driver_id",
                "driver_ref",
                "number",
                "code",
                "forename",
                "surname",
                "dob",
                "nationality",
            ],
            joins=["results.driver_id = drivers.driver_id"],
        ),
        TableSchemaContext(
            table_name="constructors",
            description="Escuderias o constructores de Formula 1.",
            columns=[
                "constructor_id",
                "constructor_ref",
                "name",
                "nationality",
            ],
            joins=["results.constructor_id = constructors.constructor_id"],
        ),
        TableSchemaContext(
            table_name="circuits",
            description="Circuitos donde se disputan las carreras.",
            columns=[
                "circuit_id",
                "circuit_ref",
                "name",
                "location",
                "country",
                "lat",
                "lng",
                "alt",
            ],
            joins=["races.circuit_id = circuits.circuit_id"],
        ),
        TableSchemaContext(
            table_name="races",
            description="Carreras de Formula 1 por temporada y ronda.",
            columns=[
                "race_id",
                "year",
                "round",
                "circuit_id",
                "name",
                "date",
                "time",
            ],
            joins=[
                "races.circuit_id = circuits.circuit_id",
                "results.race_id = races.race_id",
            ],
        ),
        TableSchemaContext(
            table_name="results",
            description="Resultados por piloto y carrera.",
            columns=[
                "result_id",
                "race_id",
                "driver_id",
                "constructor_id",
                "grid",
                "position",
                "position_text",
                "position_order",
                "points",
                "laps",
                "milliseconds",
                "fastest_lap",
                "rank",
                "fastest_lap_time",
                "fastest_lap_speed",
                "status_id",
            ],
            joins=[
                "results.race_id = races.race_id",
                "results.driver_id = drivers.driver_id",
                "results.constructor_id = constructors.constructor_id",
            ],
        ),
    ]


def get_schema_context_text(
    schema_context: list[TableSchemaContext] | None = None,
    schema_path: str | Path | None = None,
) -> str:
    """Convierte el esquema relevante en un bloque de texto para prompts."""

    curated_context = schema_context or get_default_schema_context()
    parts = ["Esquema SQL disponible:"]
    for table in curated_context:
        parts.append(f"- Tabla `{table.table_name}`: {table.description}")
        parts.append(f"  Columnas: {', '.join(table.columns)}")
        if table.joins:
            parts.append(f"  Joins comunes: {', '.join(table.joins)}")

    if schema_path is not None:
        path = Path(schema_path)
        if path.exists():
            parts.append("")
            parts.append("Referencia adicional del esquema SQL:")
            parts.append(path.read_text(encoding='utf-8').strip())

    return "\n".join(parts)
