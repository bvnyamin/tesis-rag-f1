# Generacion de SQL con apoyo de RAG

Esta etapa agrega la capa inicial de NL2SQL para transformar preguntas en
lenguaje natural en consultas SQL `SELECT`.

## Modulos

- `src/f1_rag/nl2sql/schema_context.py`
- `src/f1_rag/nl2sql/prompt_builder.py`
- `src/f1_rag/nl2sql/sql_generator.py`

## Entradas de la generacion

- pregunta del usuario
- contexto recuperado por RAG
- contexto del esquema SQL

## Salida

- una consulta SQL limpia y validada

## Ejemplo desde Docker

```text
docker compose exec app python -m f1_rag.nl2sql.example_usage "Quien gano el Australian Grand Prix de 2008?" --top-k 3
```

## Observaciones

- Esta etapa genera SQL, pero no ejecuta la consulta desde la interfaz.
- La salida pasa por el validador SQL actual para asegurar que sea un `SELECT`
  unico y seguro.
