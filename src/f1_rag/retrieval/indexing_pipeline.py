"""Pipeline para generar embeddings de fragmentos serializados e indexarlos en Chroma."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from f1_rag.config import AppConfig
from f1_rag.data.serialization import iter_documents_from_jsonl
from f1_rag.embeddings import OpenAIEmbedder

from .chroma_indexer import ChromaIndexer


@dataclass(slots=True)
class BatchProgress:
    """Describe el avance de un lote durante la indexacion."""

    batch_number: int
    batch_size: int
    processed_documents: int
    target_documents: int | None


@dataclass(slots=True)
class BatchIndexingSummary:
    """Resumen extendido de una ejecucion de indexacion por lotes."""

    collection_name: str
    indexed_documents: int
    embedding_model: str
    documents_path: str
    offset: int
    limit: int | None
    batch_size: int
    processed_batches: int


def run_indexing_pipeline(
    documents_path: str | Path = "data/processed/rag_documents.jsonl",
    processed_dir: str | Path = "data/processed",
    config: AppConfig | None = None,
    offset: int = 0,
    limit: int | None = None,
    batch_size: int = 500,
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> dict[str, Path]:
    """Genera embeddings para fragmentos serializados y los sube a Chroma por lotes."""

    if offset < 0:
        raise ValueError("offset no puede ser negativo.")
    if limit is not None and limit <= 0:
        raise ValueError("limit debe ser mayor que cero cuando se informa.")
    if batch_size <= 0:
        raise ValueError("batch_size debe ser mayor que cero.")

    app_config = config or AppConfig.from_env()
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)

    documents_file = Path(documents_path)
    if not documents_file.exists():
        raise FileNotFoundError(f"No se encontro el archivo de documentos RAG: {documents_file}")

    embedder = OpenAIEmbedder(app_config)
    indexer = ChromaIndexer(app_config)
    target_documents = limit
    indexed_documents = 0
    processed_batches = 0
    last_collection_name = app_config.chroma_collection

    for batch_number, document_batch in enumerate(
        iter_documents_from_jsonl(
            documents_file,
            offset=offset,
            limit=limit,
            batch_size=batch_size,
        ),
        start=1,
    ):
        embedded_documents = embedder.embed_documents(document_batch)
        summary = indexer.upsert_documents(embedded_documents)
        last_collection_name = summary.collection_name
        indexed_documents += len(document_batch)
        processed_batches = batch_number

        if progress_callback is not None:
            progress_callback(
                BatchProgress(
                    batch_number=batch_number,
                    batch_size=len(document_batch),
                    processed_documents=indexed_documents,
                    target_documents=target_documents,
                )
            )

    if indexed_documents == 0:
        raise ValueError("No se encontraron documentos para indexar con los parametros entregados.")

    summary_path = processed_path / "indexing_summary.json"
    summary_payload = BatchIndexingSummary(
        collection_name=last_collection_name,
        indexed_documents=indexed_documents,
        embedding_model=app_config.embedding_model,
        documents_path=str(documents_file),
        offset=offset,
        limit=limit,
        batch_size=batch_size,
        processed_batches=processed_batches,
    )
    summary_path.write_text(
        json.dumps(asdict(summary_payload), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    return {
        "documents_path": documents_file,
        "summary_path": summary_path,
    }
