"""Pipeline de carga del dataset de F1 hacia PostgreSQL."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from psycopg import Connection, sql

from f1_rag.config import AppConfig

from .connection import create_connection
from .schema import apply_schema


@dataclass(slots=True)
class TableLoadConfig:
    """Configuracion de carga para una tabla del dataset."""

    csv_name: str
    table_name: str
    columns: list[str]


TABLE_LOAD_ORDER = [
    TableLoadConfig(
        csv_name="drivers.csv",
        table_name="drivers",
        columns=[
            "driver_id",
            "driver_ref",
            "number",
            "code",
            "forename",
            "surname",
            "dob",
            "nationality",
            "url",
        ],
    ),
    TableLoadConfig(
        csv_name="constructors.csv",
        table_name="constructors",
        columns=[
            "constructor_id",
            "constructor_ref",
            "name",
            "nationality",
            "url",
        ],
    ),
    TableLoadConfig(
        csv_name="circuits.csv",
        table_name="circuits",
        columns=[
            "circuit_id",
            "circuit_ref",
            "name",
            "location",
            "country",
            "lat",
            "lng",
            "alt",
            "url",
        ],
    ),
    TableLoadConfig(
        csv_name="races.csv",
        table_name="races",
        columns=[
            "race_id",
            "year",
            "round",
            "circuit_id",
            "name",
            "date",
            "time",
            "url",
            "fp1_date",
            "fp1_time",
            "fp2_date",
            "fp2_time",
            "fp3_date",
            "fp3_time",
            "quali_date",
            "quali_time",
            "sprint_date",
            "sprint_time",
        ],
    ),
    TableLoadConfig(
        csv_name="results.csv",
        table_name="results",
        columns=[
            "result_id",
            "race_id",
            "driver_id",
            "constructor_id",
            "number",
            "grid",
            "position",
            "position_text",
            "position_order",
            "points",
            "laps",
            "time",
            "milliseconds",
            "fastest_lap",
            "rank",
            "fastest_lap_time",
            "fastest_lap_speed",
            "status_id",
        ],
    ),
]


CSV_TO_DB_COLUMNS = {
    "drivers": {
        "driver_id": "driverId",
        "driver_ref": "driverRef",
    },
    "constructors": {
        "constructor_id": "constructorId",
        "constructor_ref": "constructorRef",
    },
    "circuits": {
        "circuit_id": "circuitId",
        "circuit_ref": "circuitRef",
    },
    "races": {
        "race_id": "raceId",
        "circuit_id": "circuitId",
    },
    "results": {
        "result_id": "resultId",
        "race_id": "raceId",
        "driver_id": "driverId",
        "constructor_id": "constructorId",
        "position_text": "positionText",
        "position_order": "positionOrder",
        "fastest_lap": "fastestLap",
        "fastest_lap_time": "fastestLapTime",
        "fastest_lap_speed": "fastestLapSpeed",
        "status_id": "statusId",
    },
}


def run_postgres_load_pipeline(
    raw_dir: str | Path = "data/raw",
    config: AppConfig | None = None,
) -> dict[str, int]:
    """Carga las tablas principales de F1 en PostgreSQL."""

    app_config = config or AppConfig.from_env()
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"No se encontro el directorio de datos raw: {raw_path}")

    with create_connection(app_config) as connection:
        apply_schema(connection)
        loaded_counts: dict[str, int] = {}
        for table_config in TABLE_LOAD_ORDER:
            loaded_counts[table_config.table_name] = load_csv_into_table(
                connection=connection,
                raw_dir=raw_path,
                table_config=table_config,
            )
        return loaded_counts


def load_csv_into_table(
    connection: Connection,
    raw_dir: Path,
    table_config: TableLoadConfig,
) -> int:
    """Carga un CSV especifico en su tabla de PostgreSQL."""

    csv_path = raw_dir / table_config.csv_name
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo CSV requerido: {csv_path}")

    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
            sql.Identifier(table_config.table_name)
        ))
    connection.commit()

    copied_rows = 0
    copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table_config.table_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in table_config.columns),
    )

    source_columns = [
        CSV_TO_DB_COLUMNS.get(table_config.table_name, {}).get(column, column)
        for column in table_config.columns
    ]

    with csv_path.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        missing_columns = [column for column in source_columns if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"El archivo {csv_path.name} no contiene las columnas esperadas: {missing_columns}"
            )

        with connection.cursor() as cursor, cursor.copy(copy_sql) as copy:
            for row in reader:
                copy.write_row([_normalize_csv_value(row[column]) for column in source_columns])
                copied_rows += 1

    connection.commit()
    return copied_rows


def _normalize_csv_value(value: str | None) -> str | None:
    """Normaliza valores del CSV para PostgreSQL."""

    if value is None:
        return None
    cleaned = value.strip()
    if cleaned in {"", "\\N"}:
        return None
    return cleaned
