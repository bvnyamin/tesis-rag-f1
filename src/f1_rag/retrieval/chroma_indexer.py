"""Utilidades de indexacion en Chroma para fragmentos RAG embebidos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb

from f1_rag.config import AppConfig
from f1_rag.embeddings import EmbeddedDocument


@dataclass(slots=True)
class IndexingSummary:
    """Resumen pequeno que describe una ejecucion de indexacion."""

    collection_name: str
    indexed_documents: int
    embedding_model: str


class ChromaIndexer:
    """Persiste documentos embebidos dentro de una coleccion de Chroma."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        try:
            self.client = chromadb.HttpClient(
                host=self.config.chroma_host,
                port=self.config.chroma_port,
                ssl=self.config.chroma_ssl,
            )
        except Exception as exc:  # pragma: no cover - guardia de transporte del cliente
            raise RuntimeError(f"No fue posible conectarse a Chroma: {exc}") from exc

    def upsert_documents(self, embedded_documents: list[EmbeddedDocument]) -> IndexingSummary:
        """Crea o actualiza registros en Chroma para fragmentos RAG embebidos."""

        if not embedded_documents:
            raise ValueError("No se entregaron documentos embebidos para indexar.")

        collection = self.client.get_or_create_collection(
            name=self.config.chroma_collection,
            metadata={
                "project": "thesis-rag-f1",
                "embedding_model": self.config.embedding_model,
                "content_type": "structured_rag_documents",
            },
        )

        try:
            collection.upsert(
                ids=[item.document.document_id for item in embedded_documents],
                embeddings=[item.embedding for item in embedded_documents],
                documents=[item.document.text for item in embedded_documents],
                metadatas=[
                    build_chroma_metadata(item, embedding_model=self.config.embedding_model)
                    for item in embedded_documents
                ],
            )
        except Exception as exc:  # pragma: no cover - guardia de API de Chroma
            raise RuntimeError(f"Fallo el upsert de documentos en Chroma: {exc}") from exc

        return IndexingSummary(
            collection_name=self.config.chroma_collection,
            indexed_documents=len(embedded_documents),
            embedding_model=self.config.embedding_model,
        )


def build_chroma_metadata(item: EmbeddedDocument, embedding_model: str) -> dict[str, Any]:
    """Aplana los metadatos del documento a un diccionario escalar compatible con Chroma."""

    document = item.document
    metadata = dict(document.metadata)
    metadata.update(
        {
            "document_id": document.document_id,
            "table_name": document.table_name,
            "row_index": document.row_index,
            "embedding_model": embedding_model,
        }
    )
    return metadata
