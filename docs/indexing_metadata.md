# Embeddings and Indexing Metadata

Each serialized fragment is indexed in Chroma with a metadata payload designed
for traceability and future filtering.

## Metadata fields

- `document_id`: stable identifier such as `races-0`
- `table_name`: source table name
- `row_index`: zero-based row number after preparation
- `row_id`: row identifier repeated for readability
- `content_type`: currently `table_row`
- `source_file`: original CSV file name
- `source_path`: full logical path used by the pipeline
- `source_dir`: raw dataset directory
- `schema_version`: internal serialization version
- `column_count`: number of non-null fields in the row
- `columns_csv`: comma-separated list of columns present in the fragment
- `text_char_count`: fragment length in characters
- `embedding_model`: embedding model used during indexing

## Intended use

This structure supports:

- provenance tracking
- filtering by source table
- debugging serialized rows
- comparing future serialization versions
