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

Además, el plan alineado con el capítulo 6 del informe está en:

- `benchmarks/thesis_benchmark_cases.json`

Y se incluyen dos subconjuntos prácticos para el análisis principal:

- `benchmarks/thesis_benchmark_selected_20.json`
- `benchmarks/thesis_benchmark_selected_24.json`

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

## Cómo ejecutar el benchmark del capítulo 6

Sistema completo con RAG:

```text
docker compose exec app python scripts/run_benchmark.py --cases-path benchmarks/thesis_benchmark_cases.json --mode hybrid --output-path data/processed/thesis_benchmark_hybrid.json --manual-output-path data/processed/thesis_benchmark_hybrid_manual.csv
```

Línea base sin RAG, solo categorías A, B y C:

```text
docker compose exec app python scripts/run_benchmark.py --cases-path benchmarks/thesis_benchmark_cases.json --mode baseline --output-path data/processed/thesis_benchmark_baseline.json --manual-output-path data/processed/thesis_benchmark_baseline_manual.csv
```

## Cómo ejecutar la muestra principal recomendada

Muestra principal de 20 con RAG:

```text
docker compose exec app python scripts/run_benchmark.py --cases-path benchmarks/thesis_benchmark_selected_20.json --mode hybrid --output-path data/processed/thesis_benchmark_selected_20_hybrid.json --manual-output-path data/processed/thesis_benchmark_selected_20_hybrid_manual.csv
```

Muestra principal de 20 sin RAG:

```text
docker compose exec app python scripts/run_benchmark.py --cases-path benchmarks/thesis_benchmark_selected_20.json --mode baseline --output-path data/processed/thesis_benchmark_selected_20_baseline.json --manual-output-path data/processed/thesis_benchmark_selected_20_baseline_manual.csv
```

Muestra extendida de 24 con RAG:

```text
docker compose exec app python scripts/run_benchmark.py --cases-path benchmarks/thesis_benchmark_selected_24.json --mode hybrid --output-path data/processed/thesis_benchmark_selected_24_hybrid.json --manual-output-path data/processed/thesis_benchmark_selected_24_hybrid_manual.csv
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
- resumen agregado por categoría
- resultados por caso
- métricas automáticas M-01, M-02, M-03, M-06 y M-07 cuando corresponda
- checks individuales por caso

Y además se genera una plantilla CSV para registrar:

- M-04 pertinencia del contexto
- M-05 coherencia de la explicación
- M-05E claridad del rechazo
- M-07 adecuación de la visualización

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

## Alineación con el capítulo 6

El benchmark extendido sigue la estructura del capítulo:

- Categoría A: recuperación simple
- Categoría B: agregación y cálculo
- Categoría C: relacional compleja
- Categoría D: comparativa con visualización
- Categoría E: seguridad y límites

Totales definidos:

- 8 consultas en A
- 8 consultas en B
- 10 consultas en C
- 8 consultas en D
- 8 consultas en E

Total:

- 42 consultas

## Próximos pasos recomendados

- ejecutar una corrida híbrida completa
- ejecutar la línea base sin RAG
- completar la planilla manual por ambos evaluadores
- consolidar métricas agregadas para el capítulo de resultados
