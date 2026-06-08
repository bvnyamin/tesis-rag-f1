"""Utilidades compartidas de configuracion."""

from __future__ import annotations

import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    """Lugar central para la configuracion de la aplicacion."""

    openai_api_key: str = ""
    sql_generation_model: str = "gpt-5-mini"
    final_response_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100
    embedding_dimensions: int | None = None
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_collection: str = "f1_structured_rag"
    chroma_ssl: bool = False
    retrieval_top_k: int = 5
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "f1_rag"
    postgres_user: str = "f1_user"
    postgres_password: str = "f1_password"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Construye la configuracion desde variables de entorno con valores por defecto."""

        raw_dimensions = os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "").strip()
        raw_ssl = os.getenv("CHROMA_SSL", "false").strip().lower()

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            sql_generation_model=os.getenv("OPENAI_SQL_MODEL", "gpt-5-mini"),
            final_response_model=os.getenv("OPENAI_FINAL_RESPONSE_MODEL", "gpt-5-mini"),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_batch_size=int(os.getenv("OPENAI_EMBEDDING_BATCH_SIZE", "100")),
            embedding_dimensions=int(raw_dimensions) if raw_dimensions else None,
            chroma_host=os.getenv("CHROMA_HOST", "chroma"),
            chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
            chroma_collection=os.getenv("CHROMA_COLLECTION", "f1_structured_rag"),
            chroma_ssl=raw_ssl in {"1", "true", "yes", "on"},
            retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
            postgres_host=os.getenv("POSTGRES_HOST", "postgres"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_db=os.getenv("POSTGRES_DB", "f1_rag"),
            postgres_user=os.getenv("POSTGRES_USER", "f1_user"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "f1_password"),
        )
