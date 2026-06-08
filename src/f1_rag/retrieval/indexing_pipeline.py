"""Pipeline para generar embeddings de fragmentos serializados e indexarlos en Chroma."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from f1_rag.config import AppConfig
from f1_rag.data.serialization import load_documents_from_jsonl
from f1_rag.embeddings import OpenAIEmbedder

from .chroma_indexer import ChromaIndexer


def run_indexing_pipeline(
    documents_path: str | Path = "data/processed/rag_documents.jsonl",
    processed_dir: str | Path = "data/processed",
    config: AppConfig | None = None,
) -> dict[str, Path]:
    """Genera embeddings para fragmentos serializados y los sube a Chroma."""

    app_config = config or AppConfig.from_env()
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)

    documents = load_documents_from_jsonl(documents_path)
    embedder = OpenAIEmbedder(app_config)
    embedded_documents = embedder.embed_documents(documents)

    indexer = ChromaIndexer(app_config)
    summary = indexer.upsert_documents(embedded_documents)

    summary_path = processed_path / "indexing_summary.json"
    summary_path.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=True), encoding="utf-8")

    return {
        "documents_path": Path(documents_path),
        "summary_path": summary_path,
    }
