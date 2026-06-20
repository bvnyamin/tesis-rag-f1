# Pipeline hibrido completo

Esta etapa conecta:

- recuperacion de contexto con Chroma
- generacion de SQL apoyada por RAG
- validacion SQL
- ejecucion en PostgreSQL
- generacion de respuesta final en lenguaje natural

## Modulos principales

- `src/f1_rag/orchestration/hybrid_pipeline.py`
- `src/f1_rag/generation/final_response.py`

## Flujo

1. recibe una pregunta
2. recupera contexto semantico con Chroma
3. construye SQL con apoyo del contexto recuperado
4. valida la consulta SQL
5. ejecuta la consulta en PostgreSQL
6. genera una respuesta final usando el resultado SQL y el contexto RAG

## Extension analitica

El pipeline tambien puede responder preguntas comparativas o evolutivas, por
ejemplo rankings, comparaciones entre pilotos o escuderias, y series por
temporada.

En esos casos:

1. la intencion heuristica intenta detectar si la pregunta es de ranking o evolucion
2. el generador SQL recibe una instruccion para devolver varias filas utiles
3. la reportería intenta construir un resumen analítico y un gráfico simple

## Ejemplo desde Docker

```text
docker compose exec app python -m f1_rag.orchestration.example_usage "Quien gano el Australian Grand Prix de 2008?" --top-k 3
```

## Observaciones

- Esta etapa no integra todavia la consulta desde la interfaz Streamlit.
- El resultado del pipeline queda listo para conectarse despues a la UI.
