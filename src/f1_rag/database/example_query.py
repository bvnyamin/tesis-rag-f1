"""Ejemplo de uso para ejecutar una consulta SELECT segura."""

from __future__ import annotations

import argparse

from .query_executor import execute_select_query


def main() -> None:
    """Ejecuta una consulta SQL de solo lectura desde linea de comandos."""

    parser = argparse.ArgumentParser(description="Ejecuta una consulta SELECT segura en PostgreSQL.")
    parser.add_argument("query", help="Consulta SQL SELECT a ejecutar.")
    args = parser.parse_args()

    result = execute_select_query(args.query)
    print(f"Consulta ejecutada: {result.query}")
    print(f"Columnas: {result.columns}")
    print(f"Filas devueltas: {result.row_count}")
    for row in result.rows[:10]:
        print(row)


if __name__ == "__main__":
    main()
