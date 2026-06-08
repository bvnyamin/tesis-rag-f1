"""Punto de entrada CLI para cargar datos de F1 en PostgreSQL."""

from __future__ import annotations

from .load_pipeline import run_postgres_load_pipeline


def main() -> None:
    """Ejecuta la carga de las tablas principales en PostgreSQL."""

    try:
        loaded_counts = run_postgres_load_pipeline()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"La carga a PostgreSQL fallo: {exc}")
        raise SystemExit(1) from exc

    print("Carga a PostgreSQL completada correctamente.")
    for table_name, count in loaded_counts.items():
        print(f"- {table_name}: {count} filas")


if __name__ == "__main__":
    main()
