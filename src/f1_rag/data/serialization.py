"""Funciones de serializacion que convierten datos de F1 en chunks semanticos para RAG."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .loader import DatasetBundle


@dataclass(slots=True)
class RagDocument:
    """Fragmento de texto minimo con metadatos para indexacion posterior."""

    document_id: str
    table_name: str
    row_index: int
    text: str
    metadata: dict[str, Any]


def serialize_bundle_to_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Serializa el dataset de F1 en documentos RAG utiles para consulta semantica."""

    serializers = [
        build_circuit_documents,
        build_driver_documents,
        build_constructor_documents,
        build_race_documents,
        build_result_documents,
        build_qualifying_documents,
        build_driver_standing_documents,
        build_constructor_standing_documents,
        build_sprint_result_documents,
        build_driver_analytics_documents,
        build_constructor_analytics_documents,
        build_season_analytics_documents,
    ]

    documents: list[RagDocument] = []
    for serializer in serializers:
        documents.extend(serializer(bundle))

    if documents:
        return documents

    fallback_documents: list[RagDocument] = []
    for table_name, dataframe in bundle.tables.items():
        fallback_documents.extend(
            build_generic_rag_documents(
                table_name=table_name,
                dataframe=dataframe,
                source_dir=bundle.source_dir,
            )
        )
    return fallback_documents


def build_generic_rag_documents(
    table_name: str,
    dataframe: pd.DataFrame,
    source_dir: str | Path | None = None,
) -> list[RagDocument]:
    """Crea fragmentos genericos a partir de una tabla.

    Se usa como respaldo cuando no existe una serializacion semantica especifica.
    """

    if dataframe.empty:
        return []

    documents: list[RagDocument] = []
    source_path = _build_source_path(source_dir, table_name)
    for row_index, row in dataframe.iterrows():
        non_null_fields = {
            column: _stringify_value(value)
            for column, value in row.items()
            if not pd.isna(value)
        }
        if not non_null_fields:
            continue

        facts = [f"{column}: {value}" for column, value in non_null_fields.items()]
        text = "\n".join(
            [
                f"table: {table_name}",
                f"row_id: {table_name}-{row_index}",
                "facts:",
                *facts,
            ]
        )

        documents.append(
            RagDocument(
                document_id=f"{table_name}-{row_index}",
                table_name=table_name,
                row_index=row_index,
                text=text,
                metadata=build_document_metadata(
                    document_id=f"{table_name}-{row_index}",
                    table_name=table_name,
                    row_index=row_index,
                    source_dir=source_dir,
                    source_path=source_path,
                    column_names=list(non_null_fields.keys()),
                    text=text,
                ),
            )
        )

    return documents


def build_circuit_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks descriptivos para circuitos."""

    circuits = bundle.tables.get("circuits")
    if circuits is None or circuits.empty:
        return []

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "circuits")
    for _, row in circuits.iterrows():
        circuit_id = _safe_int(row.get("circuitid"))
        if circuit_id is None:
            continue

        name = _safe_text(row.get("name"), "Circuito desconocido")
        location = _safe_text(row.get("location"), "ubicacion desconocida")
        country = _safe_text(row.get("country"), "pais desconocido")
        altitude = _safe_text(row.get("alt"), "sin dato")

        text = "\n".join(
            [
                f"Circuito de Formula 1: {name}.",
                f"Se encuentra en {location}, {country}.",
                f"Altitud registrada: {altitude}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"circuit-{circuit_id}",
                table_name="circuits",
                row_index=circuit_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="circuito",
                column_names=list(circuits.columns),
                extra_metadata={
                    "circuit_id": circuit_id,
                    "circuit_name": name,
                    "country": country,
                    "location": location,
                },
            )
        )

    return documents


def build_driver_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks descriptivos para pilotos."""

    drivers = bundle.tables.get("drivers")
    if drivers is None or drivers.empty:
        return []

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "drivers")
    for _, row in drivers.iterrows():
        driver_id = _safe_int(row.get("driverid"))
        if driver_id is None:
            continue

        full_name = _join_parts(row.get("forename"), row.get("surname")) or "Piloto desconocido"
        nationality = _safe_text(row.get("nationality"), "nacionalidad desconocida")
        code = _safe_text(row.get("code"), "sin codigo")
        number = _safe_text(row.get("number"), "sin numero")
        birth_date = _safe_text(row.get("dob"), "sin fecha de nacimiento")

        text = "\n".join(
            [
                f"Piloto de Formula 1: {full_name}.",
                f"Nacionalidad: {nationality}.",
                f"Codigo FIA: {code}. Numero historico: {number}.",
                f"Fecha de nacimiento: {birth_date}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"driver-{driver_id}",
                table_name="drivers",
                row_index=driver_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="piloto",
                column_names=list(drivers.columns),
                extra_metadata={
                    "driver_id": driver_id,
                    "driver_name": full_name,
                    "driver_code": code,
                    "nationality": nationality,
                },
            )
        )

    return documents


def build_constructor_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks descriptivos para escuderias."""

    constructors = bundle.tables.get("constructors")
    if constructors is None or constructors.empty:
        return []

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "constructors")
    for _, row in constructors.iterrows():
        constructor_id = _safe_int(row.get("constructorid"))
        if constructor_id is None:
            continue

        name = _safe_text(row.get("name"), "Escuderia desconocida")
        nationality = _safe_text(row.get("nationality"), "nacionalidad desconocida")

        text = "\n".join(
            [
                f"Escuderia de Formula 1: {name}.",
                f"Nacionalidad de la escuderia: {nationality}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"constructor-{constructor_id}",
                table_name="constructors",
                row_index=constructor_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="escuderia",
                column_names=list(constructors.columns),
                extra_metadata={
                    "constructor_id": constructor_id,
                    "constructor_name": name,
                    "nationality": nationality,
                },
            )
        )

    return documents


def build_race_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks descriptivos para carreras."""

    races = bundle.tables.get("races")
    circuits = bundle.tables.get("circuits")
    if races is None or races.empty:
        return []

    races_enriched = races.copy()
    if circuits is not None and not circuits.empty:
        circuits_lookup = circuits[["circuitid", "name", "location", "country"]].rename(
            columns={
                "name": "circuit_name",
                "location": "circuit_location",
                "country": "circuit_country",
            }
        )
        races_enriched = races_enriched.merge(circuits_lookup, how="left", on="circuitid")

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "races")
    for _, row in races_enriched.iterrows():
        race_id = _safe_int(row.get("raceid"))
        if race_id is None:
            continue

        race_name = _safe_text(row.get("name"), "Carrera desconocida")
        year = _safe_text(row.get("year"), "anio desconocido")
        round_number = _safe_text(row.get("round"), "sin ronda")
        date = _safe_text(row.get("date"), "sin fecha")
        circuit_name = _safe_text(row.get("circuit_name"), "circuito desconocido")
        circuit_location = _safe_text(row.get("circuit_location"), "ubicacion desconocida")
        circuit_country = _safe_text(row.get("circuit_country"), "pais desconocido")

        text = "\n".join(
            [
                f"Carrera de Formula 1: {race_name} del anio {year}.",
                f"Corresponde a la ronda {round_number} de la temporada.",
                f"Se disputo el {date} en el circuito {circuit_name}, ubicado en {circuit_location}, {circuit_country}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"race-{race_id}",
                table_name="races",
                row_index=race_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="carrera",
                column_names=list(races_enriched.columns),
                extra_metadata={
                    "race_id": race_id,
                    "race_name": race_name,
                    "season_year": _safe_int(row.get("year")),
                    "round": _safe_int(row.get("round")),
                    "circuit_name": circuit_name,
                },
            )
        )

    return documents


def build_result_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks semanticos para resultados de carrera."""

    results = bundle.tables.get("results")
    races = bundle.tables.get("races")
    drivers = bundle.tables.get("drivers")
    constructors = bundle.tables.get("constructors")
    circuits = bundle.tables.get("circuits")
    status = bundle.tables.get("status")
    if any(table is None or table.empty for table in [results, races, drivers, constructors]):
        return []

    enriched = results.copy()
    enriched = enriched.merge(
        races[["raceid", "year", "round", "circuitid", "name", "date"]],
        how="left",
        on="raceid",
        suffixes=("", "_race"),
    )
    enriched = enriched.merge(
        drivers[["driverid", "forename", "surname", "code", "nationality"]],
        how="left",
        on="driverid",
        suffixes=("", "_driver"),
    )
    enriched = enriched.merge(
        constructors[["constructorid", "name", "nationality"]],
        how="left",
        on="constructorid",
        suffixes=("", "_constructor"),
    )
    if circuits is not None and not circuits.empty:
        enriched = enriched.merge(
            circuits[["circuitid", "name", "location", "country"]].rename(
                columns={
                    "name": "circuit_name",
                    "location": "circuit_location",
                    "country": "circuit_country",
                }
            ),
            how="left",
            on="circuitid",
        )
    if status is not None and not status.empty:
        enriched = enriched.merge(status[["statusid", "status"]], how="left", on="statusid")

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "results")
    for _, row in enriched.iterrows():
        result_id = _safe_int(row.get("resultid"))
        if result_id is None:
            continue

        driver_name = _join_parts(row.get("forename"), row.get("surname")) or "Piloto desconocido"
        constructor_name = _safe_text(row.get("name_constructor"), "escuderia desconocida")
        race_name = _safe_text(row.get("name"), "carrera desconocida")
        season_year = _safe_text(row.get("year"), "anio desconocido")
        date = _safe_text(row.get("date"), "sin fecha")
        circuit_name = _safe_text(row.get("circuit_name"), "circuito desconocido")
        position = _safe_text(row.get("positiontext"), _safe_text(row.get("position"), "sin posicion"))
        points = _safe_text(row.get("points"), "0")
        laps = _safe_text(row.get("laps"), "sin dato")
        grid = _safe_text(row.get("grid"), "sin dato")
        race_status = _safe_text(row.get("status"), "estado desconocido")
        fastest_lap = _safe_text(row.get("fastestlaptime"), "sin vuelta rapida registrada")

        text = "\n".join(
            [
                f"Resultado de carrera de Formula 1: {driver_name} en {race_name} {season_year}.",
                f"El piloto compitio para {constructor_name} y finalizo en la posicion {position}.",
                f"La carrera se disputo el {date} en {circuit_name}.",
                f"Largada desde la grilla {grid}, vueltas completadas: {laps}, puntos obtenidos: {points}.",
                f"Estado final: {race_status}. Vuelta rapida registrada: {fastest_lap}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"result-{result_id}",
                table_name="results",
                row_index=result_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="resultado_carrera",
                column_names=list(enriched.columns),
                extra_metadata={
                    "result_id": result_id,
                    "race_id": _safe_int(row.get("raceid")),
                    "driver_id": _safe_int(row.get("driverid")),
                    "constructor_id": _safe_int(row.get("constructorid")),
                    "driver_name": driver_name,
                    "constructor_name": constructor_name,
                    "race_name": race_name,
                    "season_year": _safe_int(row.get("year")),
                    "round": _safe_int(row.get("round")),
                    "position": _safe_text(row.get("positiontext"), ""),
                    "points": _safe_float(row.get("points")),
                    "status_text": race_status,
                },
            )
        )

    return documents


def build_qualifying_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks semanticos para clasificaciones."""

    qualifying = bundle.tables.get("qualifying")
    races = bundle.tables.get("races")
    drivers = bundle.tables.get("drivers")
    constructors = bundle.tables.get("constructors")
    if any(table is None or table.empty for table in [qualifying, races, drivers, constructors]):
        return []

    enriched = qualifying.copy()
    enriched = enriched.merge(races[["raceid", "year", "round", "name", "date"]], how="left", on="raceid")
    enriched = enriched.merge(drivers[["driverid", "forename", "surname"]], how="left", on="driverid")
    enriched = enriched.merge(
        constructors[["constructorid", "name"]].rename(columns={"name": "constructor_name"}),
        how="left",
        on="constructorid",
    )

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "qualifying")
    for _, row in enriched.iterrows():
        qualify_id = _safe_int(row.get("qualifyid"))
        if qualify_id is None:
            continue

        driver_name = _join_parts(row.get("forename"), row.get("surname")) or "Piloto desconocido"
        race_name = _safe_text(row.get("name"), "carrera desconocida")
        constructor_name = _safe_text(row.get("constructor_name"), "escuderia desconocida")
        season_year = _safe_text(row.get("year"), "anio desconocido")
        position = _safe_text(row.get("position"), "sin posicion")
        q1 = _safe_text(row.get("q1"), "sin tiempo en Q1")
        q2 = _safe_text(row.get("q2"), "sin tiempo en Q2")
        q3 = _safe_text(row.get("q3"), "sin tiempo en Q3")

        text = "\n".join(
            [
                f"Clasificacion de Formula 1: {driver_name} para {race_name} {season_year}.",
                f"El piloto represento a {constructor_name} y obtuvo la posicion {position}.",
                f"Tiempos registrados: Q1 {q1}, Q2 {q2}, Q3 {q3}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"qualifying-{qualify_id}",
                table_name="qualifying",
                row_index=qualify_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="clasificacion",
                column_names=list(enriched.columns),
                extra_metadata={
                    "qualify_id": qualify_id,
                    "race_id": _safe_int(row.get("raceid")),
                    "driver_id": _safe_int(row.get("driverid")),
                    "constructor_id": _safe_int(row.get("constructorid")),
                    "driver_name": driver_name,
                    "constructor_name": constructor_name,
                    "race_name": race_name,
                    "season_year": _safe_int(row.get("year")),
                    "position": _safe_text(row.get("position"), ""),
                },
            )
        )

    return documents


def build_driver_standing_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks semanticos para standings de pilotos."""

    standings = bundle.tables.get("driver_standings")
    races = bundle.tables.get("races")
    drivers = bundle.tables.get("drivers")
    if any(table is None or table.empty for table in [standings, races, drivers]):
        return []

    enriched = standings.copy()
    enriched = enriched.merge(races[["raceid", "year", "round", "name"]], how="left", on="raceid")
    enriched = enriched.merge(drivers[["driverid", "forename", "surname"]], how="left", on="driverid")

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "driver_standings")
    for _, row in enriched.iterrows():
        standing_id = _safe_int(row.get("driverstandingsid"))
        if standing_id is None:
            continue

        driver_name = _join_parts(row.get("forename"), row.get("surname")) or "Piloto desconocido"
        race_name = _safe_text(row.get("name"), "carrera desconocida")
        season_year = _safe_text(row.get("year"), "anio desconocido")
        position = _safe_text(row.get("positiontext"), _safe_text(row.get("position"), "sin posicion"))
        points = _safe_text(row.get("points"), "0")
        wins = _safe_text(row.get("wins"), "0")

        text = "\n".join(
            [
                f"Standing de pilotos de Formula 1 despues de {race_name} {season_year}.",
                f"{driver_name} ocupa la posicion {position} del campeonato.",
                f"Acumula {points} puntos y {wins} victorias hasta esa carrera.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"driver-standing-{standing_id}",
                table_name="driver_standings",
                row_index=standing_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="standing_piloto",
                column_names=list(enriched.columns),
                extra_metadata={
                    "driver_standing_id": standing_id,
                    "race_id": _safe_int(row.get("raceid")),
                    "driver_id": _safe_int(row.get("driverid")),
                    "driver_name": driver_name,
                    "race_name": race_name,
                    "season_year": _safe_int(row.get("year")),
                    "position": _safe_text(row.get("positiontext"), ""),
                    "points": _safe_float(row.get("points")),
                    "wins": _safe_int(row.get("wins")),
                },
            )
        )

    return documents


def build_constructor_standing_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks semanticos para standings de escuderias."""

    standings = bundle.tables.get("constructor_standings")
    races = bundle.tables.get("races")
    constructors = bundle.tables.get("constructors")
    if any(table is None or table.empty for table in [standings, races, constructors]):
        return []

    enriched = standings.copy()
    enriched = enriched.merge(races[["raceid", "year", "round", "name"]], how="left", on="raceid")
    enriched = enriched.merge(
        constructors[["constructorid", "name"]].rename(columns={"name": "constructor_name"}),
        how="left",
        on="constructorid",
    )

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "constructor_standings")
    for _, row in enriched.iterrows():
        standing_id = _safe_int(row.get("constructorstandingsid"))
        if standing_id is None:
            continue

        constructor_name = _safe_text(row.get("constructor_name"), "Escuderia desconocida")
        race_name = _safe_text(row.get("name"), "carrera desconocida")
        season_year = _safe_text(row.get("year"), "anio desconocido")
        position = _safe_text(row.get("positiontext"), _safe_text(row.get("position"), "sin posicion"))
        points = _safe_text(row.get("points"), "0")
        wins = _safe_text(row.get("wins"), "0")

        text = "\n".join(
            [
                f"Standing de constructores de Formula 1 despues de {race_name} {season_year}.",
                f"{constructor_name} ocupa la posicion {position} del campeonato de constructores.",
                f"Acumula {points} puntos y {wins} victorias hasta esa carrera.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"constructor-standing-{standing_id}",
                table_name="constructor_standings",
                row_index=standing_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="standing_constructores",
                column_names=list(enriched.columns),
                extra_metadata={
                    "constructor_standing_id": standing_id,
                    "race_id": _safe_int(row.get("raceid")),
                    "constructor_id": _safe_int(row.get("constructorid")),
                    "constructor_name": constructor_name,
                    "race_name": race_name,
                    "season_year": _safe_int(row.get("year")),
                    "position": _safe_text(row.get("positiontext"), ""),
                    "points": _safe_float(row.get("points")),
                    "wins": _safe_int(row.get("wins")),
                },
            )
        )

    return documents


def build_sprint_result_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye chunks semanticos para resultados sprint."""

    sprint_results = bundle.tables.get("sprint_results")
    races = bundle.tables.get("races")
    drivers = bundle.tables.get("drivers")
    constructors = bundle.tables.get("constructors")
    status = bundle.tables.get("status")
    if any(table is None or table.empty for table in [sprint_results, races, drivers, constructors]):
        return []

    enriched = sprint_results.copy()
    enriched = enriched.merge(
        races[["raceid", "year", "round", "name", "date"]],
        how="left",
        on="raceid",
    )
    enriched = enriched.merge(
        drivers[["driverid", "forename", "surname", "code"]],
        how="left",
        on="driverid",
    )
    enriched = enriched.merge(
        constructors[["constructorid", "name"]].rename(columns={"name": "constructor_name"}),
        how="left",
        on="constructorid",
    )
    if status is not None and not status.empty:
        enriched = enriched.merge(status[["statusid", "status"]], how="left", on="statusid")

    documents: list[RagDocument] = []
    source_path = _build_source_path(bundle.source_dir, "sprint_results")
    for _, row in enriched.iterrows():
        result_id = _safe_int(row.get("resultid"))
        if result_id is None:
            continue

        driver_name = _join_parts(row.get("forename"), row.get("surname")) or "Piloto desconocido"
        race_name = _safe_text(row.get("name"), "carrera desconocida")
        constructor_name = _safe_text(row.get("constructor_name"), "escuderia desconocida")
        season_year = _safe_text(row.get("year"), "anio desconocido")
        date = _safe_text(row.get("date"), "sin fecha")
        position = _safe_text(row.get("positiontext"), _safe_text(row.get("position"), "sin posicion"))
        grid = _safe_text(row.get("grid"), "sin dato")
        points = _safe_text(row.get("points"), "0")
        laps = _safe_text(row.get("laps"), "sin dato")
        sprint_status = _safe_text(row.get("status"), "estado desconocido")

        text = "\n".join(
            [
                f"Resultado sprint de Formula 1: {driver_name} en {race_name} {season_year}.",
                f"El piloto compitio para {constructor_name} y termino en la posicion {position}.",
                f"El sprint se disputo el {date}, saliendo desde la grilla {grid}.",
                f"Vueltas completadas: {laps}. Puntos obtenidos en sprint: {points}. Estado final: {sprint_status}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"sprint-result-{result_id}",
                table_name="sprint_results",
                row_index=result_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="resultado_sprint",
                column_names=list(enriched.columns),
                extra_metadata={
                    "sprint_result_id": result_id,
                    "race_id": _safe_int(row.get("raceid")),
                    "driver_id": _safe_int(row.get("driverid")),
                    "constructor_id": _safe_int(row.get("constructorid")),
                    "driver_name": driver_name,
                    "constructor_name": constructor_name,
                    "race_name": race_name,
                    "season_year": _safe_int(row.get("year")),
                    "round": _safe_int(row.get("round")),
                    "position": _safe_text(row.get("positiontext"), ""),
                    "points": _safe_float(row.get("points")),
                    "status_text": sprint_status,
                },
            )
        )

    return documents


def build_driver_analytics_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye resúmenes analíticos históricos por piloto."""

    results = bundle.tables.get("results")
    drivers = bundle.tables.get("drivers")
    qualifying = bundle.tables.get("qualifying")
    if results is None or results.empty or drivers is None or drivers.empty:
        return []

    wins_summary = (
        results.assign(
            is_win=results["positionorder"].fillna(-1).eq(1).astype(int),
            is_podium=results["positionorder"].fillna(-1).isin([1, 2, 3]).astype(int),
            points_numeric=pd.to_numeric(results["points"], errors="coerce").fillna(0.0),
        )
        .groupby("driverid", as_index=False)
        .agg(
            total_races=("resultid", "count"),
            total_wins=("is_win", "sum"),
            total_podiums=("is_podium", "sum"),
            total_points=("points_numeric", "sum"),
        )
    )

    analytics = wins_summary.merge(
        drivers[["driverid", "forename", "surname", "nationality", "code"]],
        how="left",
        on="driverid",
    )

    if qualifying is not None and not qualifying.empty:
        poles_summary = (
            qualifying.assign(is_pole=qualifying["position"].fillna(-1).eq(1).astype(int))
            .groupby("driverid", as_index=False)
            .agg(total_poles=("is_pole", "sum"))
        )
        analytics = analytics.merge(poles_summary, how="left", on="driverid")
    else:
        analytics["total_poles"] = 0

    analytics["total_poles"] = analytics["total_poles"].fillna(0).astype(int)

    documents: list[RagDocument] = []
    source_path = "derived://driver_analytics"
    for _, row in analytics.iterrows():
        driver_id = _safe_int(row.get("driverid"))
        if driver_id is None:
            continue

        driver_name = _join_parts(row.get("forename"), row.get("surname")) or "Piloto desconocido"
        nationality = _safe_text(row.get("nationality"), "nacionalidad desconocida")
        code = _safe_text(row.get("code"), "sin codigo")
        total_races = _safe_int(row.get("total_races")) or 0
        total_wins = _safe_int(row.get("total_wins")) or 0
        total_podiums = _safe_int(row.get("total_podiums")) or 0
        total_poles = _safe_int(row.get("total_poles")) or 0
        total_points = _safe_float(row.get("total_points")) or 0.0

        text = "\n".join(
            [
                f"Resumen historico de piloto de Formula 1: {driver_name}.",
                f"Nacionalidad: {nationality}. Codigo FIA: {code}.",
                f"Estadisticas acumuladas: {total_races} carreras, {total_wins} victorias, {total_podiums} podios, {total_poles} poles.",
                f"Puntos historicos acumulados en results: {total_points:.1f}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"driver-analytics-{driver_id}",
                table_name="driver_analytics",
                row_index=driver_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="analitica_piloto",
                column_names=list(analytics.columns),
                extra_metadata={
                    "driver_id": driver_id,
                    "driver_name": driver_name,
                    "nationality": nationality,
                    "total_races": total_races,
                    "total_wins": total_wins,
                    "total_podiums": total_podiums,
                    "total_poles": total_poles,
                    "total_points": total_points,
                },
            )
        )

    return documents


def build_constructor_analytics_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye resúmenes analíticos históricos por escudería."""

    results = bundle.tables.get("results")
    constructors = bundle.tables.get("constructors")
    qualifying = bundle.tables.get("qualifying")
    if results is None or results.empty or constructors is None or constructors.empty:
        return []

    wins_summary = (
        results.assign(
            is_win=results["positionorder"].fillna(-1).eq(1).astype(int),
            is_podium=results["positionorder"].fillna(-1).isin([1, 2, 3]).astype(int),
            points_numeric=pd.to_numeric(results["points"], errors="coerce").fillna(0.0),
        )
        .groupby("constructorid", as_index=False)
        .agg(
            total_races=("resultid", "count"),
            total_wins=("is_win", "sum"),
            total_podiums=("is_podium", "sum"),
            total_points=("points_numeric", "sum"),
        )
    )

    analytics = wins_summary.merge(
        constructors[["constructorid", "name", "nationality"]],
        how="left",
        on="constructorid",
    )

    if qualifying is not None and not qualifying.empty:
        poles_summary = (
            qualifying.assign(is_pole=qualifying["position"].fillna(-1).eq(1).astype(int))
            .groupby("constructorid", as_index=False)
            .agg(total_poles=("is_pole", "sum"))
        )
        analytics = analytics.merge(poles_summary, how="left", on="constructorid")
    else:
        analytics["total_poles"] = 0

    analytics["total_poles"] = analytics["total_poles"].fillna(0).astype(int)

    documents: list[RagDocument] = []
    source_path = "derived://constructor_analytics"
    for _, row in analytics.iterrows():
        constructor_id = _safe_int(row.get("constructorid"))
        if constructor_id is None:
            continue

        constructor_name = _safe_text(row.get("name"), "Escuderia desconocida")
        nationality = _safe_text(row.get("nationality"), "nacionalidad desconocida")
        total_races = _safe_int(row.get("total_races")) or 0
        total_wins = _safe_int(row.get("total_wins")) or 0
        total_podiums = _safe_int(row.get("total_podiums")) or 0
        total_poles = _safe_int(row.get("total_poles")) or 0
        total_points = _safe_float(row.get("total_points")) or 0.0

        text = "\n".join(
            [
                f"Resumen historico de escuderia de Formula 1: {constructor_name}.",
                f"Nacionalidad de la escuderia: {nationality}.",
                f"Estadisticas acumuladas: {total_races} participaciones, {total_wins} victorias, {total_podiums} podios, {total_poles} poles.",
                f"Puntos historicos acumulados en results: {total_points:.1f}.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"constructor-analytics-{constructor_id}",
                table_name="constructor_analytics",
                row_index=constructor_id,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="analitica_constructores",
                column_names=list(analytics.columns),
                extra_metadata={
                    "constructor_id": constructor_id,
                    "constructor_name": constructor_name,
                    "nationality": nationality,
                    "total_races": total_races,
                    "total_wins": total_wins,
                    "total_podiums": total_podiums,
                    "total_poles": total_poles,
                    "total_points": total_points,
                },
            )
        )

    return documents


def build_season_analytics_documents(bundle: DatasetBundle) -> list[RagDocument]:
    """Construye resúmenes analíticos por temporada."""

    races = bundle.tables.get("races")
    results = bundle.tables.get("results")
    if races is None or races.empty or results is None or results.empty:
        return []

    results_with_year = results.merge(
        races[["raceid", "year", "name", "date"]],
        how="left",
        on="raceid",
    )
    analytics = (
        results_with_year.assign(
            is_win=results_with_year["positionorder"].fillna(-1).eq(1).astype(int),
            points_numeric=pd.to_numeric(results_with_year["points"], errors="coerce").fillna(0.0),
        )
        .groupby("year", as_index=False)
        .agg(
            total_results=("resultid", "count"),
            total_races=("raceid", "nunique"),
            total_wins=("is_win", "sum"),
            total_points=("points_numeric", "sum"),
        )
    )

    documents: list[RagDocument] = []
    source_path = "derived://season_analytics"
    for _, row in analytics.iterrows():
        season_year = _safe_int(row.get("year"))
        if season_year is None:
            continue

        total_results = _safe_int(row.get("total_results")) or 0
        total_races = _safe_int(row.get("total_races")) or 0
        total_wins = _safe_int(row.get("total_wins")) or 0
        total_points = _safe_float(row.get("total_points")) or 0.0

        text = "\n".join(
            [
                f"Resumen historico de temporada de Formula 1: {season_year}.",
                f"La temporada contiene {total_races} carreras y {total_results} registros de resultado.",
                f"En total se registran {total_wins} victorias y {total_points:.1f} puntos repartidos en los resultados.",
            ]
        )

        documents.append(
            _build_document(
                document_id=f"season-analytics-{season_year}",
                table_name="season_analytics",
                row_index=season_year,
                text=text,
                source_dir=bundle.source_dir,
                source_path=source_path,
                content_type="analitica_temporada",
                column_names=list(analytics.columns),
                extra_metadata={
                    "season_year": season_year,
                    "total_results": total_results,
                    "total_races": total_races,
                    "total_wins": total_wins,
                    "total_points": total_points,
                },
            )
        )

    return documents


def document_to_dict(document: RagDocument) -> dict[str, Any]:
    """Convierte un ``RagDocument`` en un diccionario serializable a JSON."""

    return asdict(document)


def build_document_metadata(
    document_id: str,
    table_name: str,
    row_index: int,
    source_dir: str | Path | None,
    source_path: str,
    column_names: list[str],
    text: str,
) -> dict[str, Any]:
    """Construye una estructura estable de metadatos para cada fragmento serializado."""

    return {
        "document_id": document_id,
        "table_name": table_name,
        "row_index": row_index,
        "row_id": document_id,
        "content_type": "table_row",
        "source_file": f"{table_name}.csv",
        "source_path": source_path,
        "source_dir": str(source_dir) if source_dir else "",
        "schema_version": "v2",
        "column_count": len(column_names),
        "columns_csv": ",".join(column_names),
        "text_char_count": len(text),
    }


def _build_document(
    document_id: str,
    table_name: str,
    row_index: int,
    text: str,
    source_dir: str | Path | None,
    source_path: str,
    content_type: str,
    column_names: list[str],
    extra_metadata: dict[str, Any] | None = None,
) -> RagDocument:
    """Construye un documento RAG y combina metadatos base con metadatos especificos."""

    metadata = build_document_metadata(
        document_id=document_id,
        table_name=table_name,
        row_index=row_index,
        source_dir=source_dir,
        source_path=source_path,
        column_names=column_names,
        text=text,
    )
    metadata["content_type"] = content_type
    if extra_metadata:
        metadata.update(extra_metadata)

    return RagDocument(
        document_id=document_id,
        table_name=table_name,
        row_index=row_index,
        text=text,
        metadata=metadata,
    )


def load_documents_from_jsonl(path: str | Path) -> list[RagDocument]:
    """Carga documentos RAG serializados desde un artefacto JSONL."""

    documents_path = Path(path)
    if not documents_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de documentos RAG: {documents_path}")

    documents: list[RagDocument] = []
    with documents_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue

            try:
                payload = json.loads(line)
                documents.append(RagDocument(**payload))
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(
                    f"Documento RAG invalido en la linea {line_number} de {documents_path}: {exc}"
                ) from exc

    if not documents:
        raise ValueError(f"El archivo de documentos RAG esta vacio: {documents_path}")

    return documents


def iter_documents_from_jsonl(
    path: str | Path,
    *,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = 500,
):
    """Itera documentos JSONL por lotes para indexacion incremental.

    Este iterador evita cargar todo el archivo en memoria y permite procesar
    ventanas acotadas del dataset serializado.
    """

    if offset < 0:
        raise ValueError("offset no puede ser negativo.")
    if limit is not None and limit <= 0:
        raise ValueError("limit debe ser mayor que cero cuando se informa.")
    if batch_size <= 0:
        raise ValueError("batch_size debe ser mayor que cero.")

    documents_path = Path(path)
    if not documents_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de documentos RAG: {documents_path}")

    current_batch: list[RagDocument] = []
    emitted_documents = 0

    with documents_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue

            if line_number <= offset:
                continue

            if limit is not None and emitted_documents >= limit:
                break

            try:
                payload = json.loads(line)
                current_batch.append(RagDocument(**payload))
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(
                    f"Documento RAG invalido en la linea {line_number} de {documents_path}: {exc}"
                ) from exc

            emitted_documents += 1
            if len(current_batch) >= batch_size:
                yield current_batch
                current_batch = []

    if current_batch:
        yield current_batch


def _stringify_value(value: Any) -> str:
    """Convierte valores de pandas en texto estable."""

    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _safe_text(value: Any, default: str = "") -> str:
    """Devuelve texto limpio o un valor por defecto cuando falta informacion."""

    if pd.isna(value):
        return default
    return str(value).strip()


def _safe_int(value: Any) -> int | None:
    """Convierte un valor numerico a entero cuando es posible."""

    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    """Convierte un valor numerico a float cuando es posible."""

    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _join_parts(*parts: Any) -> str:
    """Une partes de texto no vacias con espacios."""

    cleaned = [_safe_text(part) for part in parts if _safe_text(part)]
    return " ".join(cleaned)


def _build_source_path(source_dir: str | Path | None, table_name: str) -> str:
    """Construye una ruta de origen estable para trazabilidad."""

    if source_dir is None:
        return f"{table_name}.csv"
    return str(Path(source_dir) / f"{table_name}.csv")
