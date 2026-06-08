# Carga del dataset en PostgreSQL

Esta etapa carga un subconjunto estructural minimo del dataset de Formula 1 en
PostgreSQL para soportar futuras consultas SQL.

## Tablas incluidas

- `drivers`
- `constructors`
- `circuits`
- `races`
- `results`

## Archivo de esquema

El esquema SQL base se define en:

- `src/f1_rag/database/schema.sql`

## Como ejecutar la carga

Con Docker levantado:

```text
docker compose exec app python scripts/load_postgres.py
```

## Que hace la carga

1. Se conecta a PostgreSQL usando las variables de entorno del proyecto.
2. Crea las tablas si no existen.
3. Vacia las tablas objetivo en orden seguro.
4. Carga los CSV desde `data/raw/`.

## Observaciones

- Esta etapa todavia no implementa NL2SQL.
- Esta etapa tampoco genera respuestas finales.
- El objetivo es dejar la capa estructurada lista para futuras consultas SQL.
