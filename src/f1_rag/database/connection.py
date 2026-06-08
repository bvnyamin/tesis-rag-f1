"""Utilidades de conexion a PostgreSQL."""

from __future__ import annotations

from psycopg import Connection, connect

from f1_rag.config import AppConfig


def create_connection_string(config: AppConfig) -> str:
    """Construye la cadena de conexion a PostgreSQL."""

    return (
        f"host={config.postgres_host} "
        f"port={config.postgres_port} "
        f"dbname={config.postgres_db} "
        f"user={config.postgres_user} "
        f"password={config.postgres_password}"
    )


def create_connection(config: AppConfig) -> Connection:
    """Abre una conexion a PostgreSQL con la configuracion de la aplicacion."""

    try:
        return connect(create_connection_string(config))
    except Exception as exc:  # pragma: no cover - depende del entorno externo
        raise RuntimeError(f"No fue posible conectarse a PostgreSQL: {exc}") from exc
