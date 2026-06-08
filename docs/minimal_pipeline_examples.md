# Minimal Pipeline Examples

## Input assumption

If `data/raw/races.csv` contains rows like:

```csv
raceId,year,round,name,date
1,2009,1,Australian Grand Prix,2009-03-29
2,2009,2,Malaysian Grand Prix,2009-04-05
```

## Cleaned output

The pipeline writes a cleaned table to `data/processed/races.clean.csv`:

```csv
raceid,year,round,name,date
1,2009,1,Australian Grand Prix,2009-03-29
2,2009,2,Malaysian Grand Prix,2009-04-05
```

## RAG text output

The pipeline also writes `data/processed/rag_documents.jsonl` with entries like:

```json
{"document_id":"races-0","table_name":"races","row_index":0,"text":"table: races\nrow_id: races-0\nfacts:\nraceid: 1\nyear: 2009\nround: 1\nname: Australian Grand Prix\ndate: 2009-03-29","metadata":{"table_name":"races","row_index":0,"column_count":5,"columns":["raceid","year","round","name","date"]}}
```

## Summary output

The file `data/processed/preparation_summary.json` looks like:

```json
[
  {
    "table_name": "races",
    "input_rows": 2,
    "output_rows": 2,
    "dropped_duplicate_rows": 0,
    "normalized_columns": ["raceid", "year", "round", "name", "date"]
  }
]
```
