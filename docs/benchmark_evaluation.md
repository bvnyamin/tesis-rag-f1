# Benchmark y evaluación inicial

Este proyecto incluye un benchmark base para medir el comportamiento del
pipeline híbrido sobre preguntas representativas del dominio de Fórmula 1.

## Objetivo

El benchmark busca apoyar la tesis en tres frentes:

- evaluar si el pipeline responde preguntas reales del dominio
- comparar mejoras antes y después de cambios en retrieval, NL2SQL o reportería
- dejar evidencia reproducible del estado del sistema

## Casos incluidos

El archivo base de casos está en:

- `benchmarks/hybrid_benchmark_cases.json`

Incluye categorías como:

- `results`
- `driver_standings`
- `qualifying`
- `sprint_results`
- `race_status`
- `constructor_standings`
- `analytical_ranking`
- `analytical_trend`

## Qué valida cada caso

Cada caso puede verificar:

- cantidad mínima de filas devueltas por SQL
- tablas esperadas en el contexto recuperado
- palabras clave esperadas dentro de la SQL generada
- palabras clave esperadas dentro de la respuesta final

## Cómo ejecutar el benchmark completo

```text
docker compose exec app python scripts/run_benchmark.py
```

## Cómo ejecutar solo un caso

```text
docker compose exec app python scripts/run_benchmark.py --case-id pole_australia_2008
```

También se pueden pasar varios:

```text
docker compose exec app python scripts/run_benchmark.py --case-id pole_australia_2008 --case-id sprint_saopaulo_2021
```

## Salida generada

Por defecto se guarda un reporte en:

- `data/processed/benchmark_report.json`

Ese reporte contiene:

- resumen global de aprobación
- duración total
- resultados por caso
- checks individuales por caso

## Uso recomendado en la tesis

Una forma práctica de usarlo es:

1. ejecutar el benchmark con una versión base del sistema
2. aplicar una mejora concreta, por ejemplo en retrieval o SQL
3. volver a ejecutar el benchmark
4. comparar qué casos mejoraron, empeoraron o se mantuvieron

## Limitaciones actuales

- la evaluación todavía es heurística y no sustituye juicio humano
- las respuestas del LLM pueden variar ligeramente entre ejecuciones
- algunos checks validan palabras clave, no equivalencia semántica completa

## Próximos pasos recomendados

- ampliar el número de preguntas
- agregar benchmark para consultas comparativas y gráficas
- registrar métricas agregadas por categoría
- separar evaluación automática y evaluación cualitativa manual
