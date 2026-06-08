"""Utilidades de embeddings con OpenAI para fragmentos RAG serializados."""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from f1_rag.config import AppConfig
from f1_rag.data.serialization import RagDocument


@dataclass(slots=True)
class EmbeddedDocument:
    """Documento RAG junto con su vector de embedding."""

    document: RagDocument
    embedding: list[float]


class OpenAIEmbedder:
    """Generador de embeddings por lotes usando la API de OpenAI."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY es obligatorio para generar embeddings.")
        self.client = OpenAI(api_key=self.config.openai_api_key)

    def embed_documents(self, documents: list[RagDocument]) -> list[EmbeddedDocument]:
        """Genera embeddings para una lista de documentos RAG serializados por lotes."""

        if not documents:
            raise ValueError("No se entregaron documentos para generar embeddings.")

        embedded_documents: list[EmbeddedDocument] = []
        for start in range(0, len(documents), self.config.embedding_batch_size):
            batch = documents[start : start + self.config.embedding_batch_size]
            batch_texts = [document.text for document in batch]
            request_kwargs = {
                "model": self.config.embedding_model,
                "input": batch_texts,
                "encoding_format": "float",
            }
            if self.config.embedding_dimensions is not None:
                request_kwargs["dimensions"] = self.config.embedding_dimensions

            try:
                response = self.client.embeddings.create(**request_kwargs)
            except Exception as exc:  # pragma: no cover - guardia de red / API
                raise RuntimeError(f"La solicitud de embeddings a OpenAI fallo: {exc}") from exc

            if len(response.data) != len(batch):
                raise RuntimeError(
                    "La cantidad de embeddings devuelta no coincide con la cantidad de documentos."
                )

            for document, item in zip(batch, response.data):
                embedded_documents.append(
                    EmbeddedDocument(document=document, embedding=list(item.embedding))
                )

        return embedded_documents

    def embed_query(self, query: str) -> list[float]:
        """Genera el embedding de una consulta en lenguaje natural."""

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("El texto de la consulta no puede estar vacio.")

        request_kwargs = {
            "model": self.config.embedding_model,
            "input": normalized_query,
            "encoding_format": "float",
        }
        if self.config.embedding_dimensions is not None:
            request_kwargs["dimensions"] = self.config.embedding_dimensions

        try:
            response = self.client.embeddings.create(**request_kwargs)
        except Exception as exc:  # pragma: no cover - guardia de red / API
            raise RuntimeError(f"La solicitud de embedding de consulta a OpenAI fallo: {exc}") from exc

        if not response.data:
            raise RuntimeError("OpenAI no devolvio ningun embedding para la consulta.")

        return list(response.data[0].embedding)
