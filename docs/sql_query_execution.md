# Validacion y ejecucion de consultas SQL

Esta etapa agrega una capa minima para ejecutar consultas SQL de solo lectura
sobre PostgreSQL.

## Modulos

- `src/f1_rag/database/sql_validator.py`
- `src/f1_rag/database/query_executor.py`

## Reglas actuales del validador

- permite solo consultas que comienzan con `SELECT`
- bloquea `UPDATE`, `DELETE`, `INSERT`, `DROP`, `ALTER`, `TRUNCATE`
- bloquea multiples statements

## Ejemplo desde Docker

```text
docker compose exec app python -m f1_rag.database.example_query "SELECT driver_id, forename, surname FROM drivers LIMIT 5"
```

## Ejemplo de uso en Python

```python
from f1_rag.database.query_executor import execute_select_query

result = execute_select_query("SELECT race_id, name, year FROM races LIMIT 3")
print(result.columns)
print(result.rows)
```
