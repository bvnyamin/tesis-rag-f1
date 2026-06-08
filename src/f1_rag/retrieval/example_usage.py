"""Script de ejemplo para recuperar contexto desde Chroma."""

from __future__ import annotations

import argparse

from f1_rag.config import AppConfig

from .retriever import format_retrieved_context, retrieve_context


def main() -> None:
    """Ejecuta un ejemplo de recuperacion desde linea de comandos."""

    parser = argparse.ArgumentParser(description="Recupera contexto relevante de F1 RAG desde Chroma.")
    parser.add_argument("query", help="Pregunta en lenguaje natural para buscar sobre los chunks indexados.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Cantidad de chunks a devolver. Por defecto usa RETRIEVAL_TOP_K o 5.",
    )
    args = parser.parse_args()

    config = AppConfig.from_env()
    chunks = retrieve_context(query=args.query, config=config, top_k=args.top_k)
    print(format_retrieved_context(chunks))


if __name__ == "__main__":
    main()
