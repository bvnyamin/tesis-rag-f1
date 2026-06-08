"""Aplicacion del esquema SQL base para PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from psycopg import Connection


def load_schema_sql(schema_path: str | Path | None = None) -> str:
    """Carga el contenido del archivo ``schema.sql``."""

    path = Path(schema_path) if schema_path else Path(__file__).with_name("schema.sql")
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de esquema SQL: {path}")
    return path.read_text(encoding="utf-8")


def apply_schema(connection: Connection, schema_path: str | Path | None = None) -> None:
    """Crea las tablas base del proyecto en PostgreSQL."""

    schema_sql = load_schema_sql(schema_path)
    with connection.cursor() as cursor:
        cursor.execute(schema_sql)
    connection.commit()
