# Tesis RAG F1

Prototipo de tesis para explorar un enfoque hibrido sobre datos estructurados de
Formula 1:

- RAG semantico con Chroma
- consultas estructuradas con PostgreSQL
- generacion de SQL desde lenguaje natural
- respuesta final en lenguaje natural usando evidencia estructurada y contexto recuperado

## Objetivo

Este proyecto busca responder preguntas sobre Formula 1 combinando dos caminos:

- **camino semantico**: convertir datos estructurados en chunks, generar embeddings e
  indexarlos en Chroma
- **camino estructurado**: cargar tablas clave en PostgreSQL y responder preguntas
  exactas mediante SQL

El sistema final mezcla ambos enfoques en un pipeline hibrido.

## Tecnologias principales

- Python
- Streamlit
- PostgreSQL
- Chroma
- OpenAI API
- Docker Compose

## Estructura del proyecto

```text
.
|-- app/
|-- data/
|-- docs/
|-- notebooks/
|-- scripts/
|-- src/
|-- storage/
|-- tests/
|-- .env.example
|-- .gitignore
|-- CONTRIBUTING.md
|-- docker-compose.yml
|-- Dockerfile
|-- pyproject.toml
```

## Requisitos previos

Antes de empezar, la persona que monte el proyecto necesita:

- Docker Desktop instalado y funcionando
- una cuenta de OpenAI con API key activa y cuota disponible
- el dataset de Formula 1 ubicado en `data/raw/`

## Instalacion para otra persona

### 1. Clonar el repositorio

```text
git clone <repo-url>
cd tesis-rag-f1
```

### 2. Crear el archivo `.env`

Copiar el archivo de ejemplo:

```text
Copy-Item .env.example .env
```

Completar al menos:

```env
OPENAI_API_KEY=tu_api_key
```

Las variables mas importantes del proyecto son:

- `OPENAI_API_KEY`
- `OPENAI_SQL_MODEL`
- `OPENAI_FINAL_RESPONSE_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `CHROMA_HOST`
- `CHROMA_PORT`
- `CHROMA_COLLECTION`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `RETRIEVAL_TOP_K`

### 3. Verificar el dataset

El dataset debe quedar en:

- `data/raw/circuits.csv`
- `data/raw/constructors.csv`
- `data/raw/drivers.csv`
- `data/raw/races.csv`
- `data/raw/results.csv`

Y opcionalmente tambien:

- `data/raw/qualifying.csv`
- `data/raw/driver_standings.csv`
- `data/raw/constructor_standings.csv`
- otras tablas del dataset

## Primer arranque completo

Este es el orden recomendado para dejar el sistema listo desde cero.

### Paso 1. Levantar infraestructura

```text
docker compose up --build -d
```

Esto levanta:

- `app`
- `postgres`
- `chroma`

Verificar estado:

```text
docker compose ps
```

### Paso 2. Cargar PostgreSQL

```text
docker compose exec app python scripts/load_postgres.py
```

Esto carga:

- `drivers`
- `constructors`
- `circuits`
- `races`
- `results`

### Paso 3. Generar chunks semanticos para RAG

```text
docker compose exec app python scripts/run_minimal_pipeline.py
```

Esto genera:

- `data/processed/rag_documents.jsonl`
- `data/processed/preparation_summary.json`
- `data/processed/*.clean.csv`

### Paso 4. Indexar en Chroma

```text
docker compose exec app python -m f1_rag.retrieval.cli
```

Esto:

- lee `data/processed/rag_documents.jsonl`
- genera embeddings con OpenAI
- indexa en Chroma

Si el archivo tiene muchos miles de chunks, conviene indexar por lotes:

```text
docker compose exec app python -m f1_rag.retrieval.cli --offset 0 --limit 2000 --batch-size 500
```

Eso indexa 2000 documentos desde el inicio, en 4 lotes de 500, mostrando avance
en consola.

### Paso 5. Abrir la app

Con los servicios levantados, abrir:

- [http://localhost:8501](http://localhost:8501)

## Uso diario

### Encender el proyecto

Para uso normal diario:

```text
docker compose up -d
```

Usar `--build` solo si cambiaste codigo o dependencias:

```text
docker compose up --build -d
```

### Abrir la app

- [http://localhost:8501](http://localhost:8501)

### Apagar el proyecto

```text
docker compose down
```

Esto apaga contenedores, pero **no borra** los datos persistidos de:

- `storage/chroma/`
- `storage/postgres/`

### Ver el estado de los servicios

```text
docker compose ps
```

### Ver logs

Todos los servicios:

```text
docker compose logs -f
```

Solo la app:

```text
docker compose logs -f app
```

Solo PostgreSQL:

```text
docker compose logs -f postgres
```

Solo Chroma:

```text
docker compose logs -f chroma
```

## Como probar el sistema paso a paso

### Probar SQL directo

```text
docker compose exec app python -m f1_rag.database.example_query "SELECT race_id, name, year FROM races WHERE name ILIKE '%Australian Grand Prix%' LIMIT 5"
```

### Probar retrieval directo

```text
docker compose exec app python -m f1_rag.retrieval.example_usage "Who won the Australian Grand Prix in 2008?" --top-k 3
```

### Probar generacion de SQL con apoyo de RAG

```text
docker compose exec app python -m f1_rag.nl2sql.example_usage "Quien gano el Australian Grand Prix de 2008?" --top-k 3
```

### Probar pipeline hibrido completo desde consola

```text
docker compose exec app python -m f1_rag.orchestration.example_usage "Quien gano el Australian Grand Prix de 2008?" --top-k 3
```

### Ejecutar benchmark inicial del sistema

```text
docker compose exec app python scripts/run_benchmark.py
```

Para ejecutar solo un caso:

```text
docker compose exec app python scripts/run_benchmark.py --case-id pole_australia_2008
```

## Como funciona la interfaz

La app muestra varias capas del proceso porque este proyecto esta pensado como
prototipo de tesis y no solo como una app cerrada:

- **Respuesta final**: salida en lenguaje natural para el usuario
- **SQL generada**: consulta estructurada construida por el sistema
- **Contexto recuperado**: evidencia semantica recuperada desde Chroma
- **Resultado tabular**: evidencia exacta devuelta por PostgreSQL

Esto permite trazabilidad y explicabilidad del enfoque hibrido.

## Flujo interno del sistema

1. la app recibe una pregunta
2. se recuperan chunks relevantes desde Chroma
3. el sistema usa ese contexto para ayudar a generar SQL
4. la SQL se valida
5. la SQL se ejecuta en PostgreSQL
6. el resultado tabular y el contexto RAG se usan para construir la respuesta final

## Persistencia de datos

Los datos de servicios quedan en:

- `storage/chroma/`: persistencia local de Chroma
- `storage/postgres/`: persistencia local de PostgreSQL

Eso significa que al apagar y volver a encender con `docker compose up -d`,
normalmente no deberias perder:

- la base cargada en PostgreSQL
- la coleccion ya indexada en Chroma

## Problemas comunes

### PostgreSQL no inicia

Revisar logs:

```text
docker compose logs postgres
```

### La indexacion falla por cuota de OpenAI

Revisar:

- billing
- usage
- limites de uso del proyecto

Si cambias la API key en `.env`, luego reinicia:

```text
docker compose up -d
```

### La indexacion tarda demasiado

Puede pasar si `rag_documents.jsonl` contiene muchos miles de chunks. Para una
prueba inicial, se puede trabajar con una muestra pequena del archivo o usar
indexacion por lotes.

Ejemplo:

```text
docker compose exec app python -m f1_rag.retrieval.cli --offset 0 --limit 1000 --batch-size 250
docker compose exec app python -m f1_rag.retrieval.cli --offset 1000 --limit 1000 --batch-size 250
```

De esa forma se avanza por ventanas controladas del dataset sin reescribir el
archivo `rag_documents.jsonl`.

### La app no refleja cambios de codigo

Reconstruir:

```text
docker compose up --build -d
```

## Limpieza y espacio en disco

Docker puede ocupar bastante espacio por:

- imagenes
- cache de build
- datos persistidos

Ver uso de Docker:

```text
docker system df
```

Limpiar cache e imagenes no usadas:

```text
docker system prune
```

O solo cache de build:

```text
docker builder prune
```

## Documentacion complementaria

- `docs/postgres_loading.md`
- `docs/sql_query_execution.md`
- `docs/nl2sql_generation.md`
- `docs/hybrid_pipeline.md`
- `docs/indexing_metadata.md`
- `docs/minimal_pipeline_examples.md`
- `docs/f1_chunk_examples.md`
- `docs/benchmark_evaluation.md`

## Estado actual

Actualmente el proyecto ya incluye:

- carga de CSV
- limpieza y preparacion
- serializacion semantica para RAG
- embeddings con OpenAI
- indexacion y retrieval en Chroma
- carga de tablas principales en PostgreSQL
- validacion y ejecucion de SQL segura
- generacion de SQL con apoyo de RAG
- pipeline hibrido completo
- interfaz Streamlit conectada al backend
