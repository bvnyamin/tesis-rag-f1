# Carga del dataset en PostgreSQL

Esta etapa carga un subconjunto estructural ampliado del dataset de Formula 1 en
PostgreSQL para soportar consultas SQL e hibridas mas ricas.

## Tablas incluidas

- `drivers`
- `constructors`
- `circuits`
- `races`
- `status`
- `results`
- `qualifying`
- `driver_standings`
- `constructor_standings`
- `sprint_results`

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
4. Carga los CSV desde `data/raw/` en orden seguro segun sus dependencias.

## Observaciones

- Esta etapa deja mas tablas listas para consultas exactas, comparativas y de temporada.
- La app puede aprovechar estas tablas para preguntas mas ricas una vez que el pipeline hibrido las empiece a usar mejor.
