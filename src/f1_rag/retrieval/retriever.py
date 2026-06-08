"""Utilidades de recuperacion de contexto construidas sobre Chroma."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb

from f1_rag.config import AppConfig
from f1_rag.embeddings import OpenAIEmbedder


@dataclass(slots=True)
class RetrievedChunk:
    """Fragmento recuperado junto con sus metadatos de trazabilidad."""

    document_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None


def embed_query_text(query: str, config: AppConfig | None = None) -> list[float]:
    """Genera un vector de embedding para una consulta en lenguaje natural."""

    app_config = config or AppConfig.from_env()
    embedder = OpenAIEmbedder(app_config)
    return embedder.embed_query(query)


def search_similar_chunks(
    query_embedding: list[float],
    config: AppConfig | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Busca en Chroma los fragmentos indexados mas relevantes."""

    if not query_embedding:
        raise ValueError("El embedding de la consulta no puede estar vacio.")

    app_config = config or AppConfig.from_env()
    effective_top_k = top_k or app_config.retrieval_top_k
    if effective_top_k <= 0:
        raise ValueError("top_k debe ser mayor que cero.")

    try:
        client = chromadb.HttpClient(
            host=app_config.chroma_host,
            port=app_config.chroma_port,
            ssl=app_config.chroma_ssl,
        )
        collection = client.get_collection(name=app_config.chroma_collection)
    except Exception as exc:  # pragma: no cover - guardia de cliente / transporte
        raise RuntimeError(f"No fue posible conectarse a la coleccion de Chroma: {exc}") from exc

    try:
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:  # pragma: no cover - guardia de API de Chroma
        raise RuntimeError(f"La busqueda vectorial en Chroma fallo: {exc}") from exc

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    retrieved_chunks: list[RetrievedChunk] = []
    for document_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
        retrieved_chunks.append(
            RetrievedChunk(
                document_id=document_id,
                text=text or "",
                metadata=metadata or {},
                distance=distance,
            )
        )

    return retrieved_chunks


def format_retrieved_context(chunks: list[RetrievedChunk]) -> str:
    """Formatea los fragmentos recuperados en un bloque de contexto legible."""

    if not chunks:
        return "No se recupero contexto relevante."

    parts: list[str] = []
    for position, chunk in enumerate(chunks, start=1):
        header = f"[{position}] id={chunk.document_id}"
        if chunk.distance is not None:
            header += f" distance={chunk.distance:.6f}"

        metadata_preview = ", ".join(
            [
                f"table={chunk.metadata.get('table_name', 'unknown')}",
                f"row_index={chunk.metadata.get('row_index', 'unknown')}",
                f"source_file={chunk.metadata.get('source_file', 'unknown')}",
            ]
        )

        parts.append("\n".join([header, metadata_preview, chunk.text]))

    return "\n\n".join(parts)


def retrieve_context(
    query: str,
    config: AppConfig | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Wrapper conveniente que combina embedding de consulta y busqueda vectorial."""

    app_config = config or AppConfig.from_env()
    query_embedding = embed_query_text(query=query, config=app_config)
    return search_similar_chunks(
        query_embedding=query_embedding,
        config=app_config,
        top_k=top_k,
    )
