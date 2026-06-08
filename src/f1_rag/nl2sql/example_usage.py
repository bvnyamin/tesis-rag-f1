"""Ejemplo de uso para generar SQL con contexto RAG y esquema SQL."""

from __future__ import annotations

import argparse

from f1_rag.retrieval import format_retrieved_context, retrieve_context

from .schema_context import get_schema_context_text
from .sql_generator import generate_sql_query


def main() -> None:
    """Genera una consulta SQL a partir de una pregunta en lenguaje natural."""

    parser = argparse.ArgumentParser(description="Genera SQL con apoyo de RAG y esquema SQL.")
    parser.add_argument("question", help="Pregunta del usuario en lenguaje natural.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Cantidad de fragmentos RAG a recuperar para apoyar la generacion.",
    )
    args = parser.parse_args()

    retrieved_chunks = retrieve_context(args.question, top_k=args.top_k)
    rag_context = format_retrieved_context(retrieved_chunks)
    schema_context = get_schema_context_text()
    sql_query = generate_sql_query(
        user_question=args.question,
        rag_context=rag_context,
        schema_context=schema_context,
    )
    print(sql_query)


if __name__ == "__main__":
    main()
