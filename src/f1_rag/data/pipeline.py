"""Pipeline minimo de raw a processed para el proyecto de tesis."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .loader import load_csv_bundle
from .preparation import prepare_dataset_bundle
from .serialization import document_to_dict, serialize_bundle_to_documents


def run_minimal_pipeline(
    raw_dir: str | Path = "data/raw",
    processed_dir: str | Path = "data/processed",
) -> dict[str, Path]:
    """Ejecuta el primer pipeline end-to-end de datos estructurados.

    Salidas:
    - un CSV limpio por tabla de entrada
    - un archivo JSONL con chunks semanticos para RAG
    - un archivo JSON con el resumen de preparacion
    """

    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)

    bundle = load_csv_bundle(raw_path)
    prepared_bundle, summaries = prepare_dataset_bundle(bundle)
    documents = serialize_bundle_to_documents(prepared_bundle)

    for table_name, dataframe in prepared_bundle.tables.items():
        dataframe.to_csv(processed_path / f"{table_name}.clean.csv", index=False)

    documents_path = processed_path / "rag_documents.jsonl"
    with documents_path.open("w", encoding="utf-8") as output_file:
        for document in documents:
            output_file.write(json.dumps(document_to_dict(document), ensure_ascii=True) + "\n")

    summary_path = processed_path / "preparation_summary.json"
    summary_payload = [asdict(summary) for summary in summaries]
    summary_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=True), encoding="utf-8")

    return {
        "processed_dir": processed_path,
        "documents_path": documents_path,
        "summary_path": summary_path,
    }
