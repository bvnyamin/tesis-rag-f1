"""Ejemplo end-to-end del pipeline hibrido desde consola."""

from __future__ import annotations

import argparse

from .hybrid_pipeline import run_hybrid_pipeline


def main() -> None:
    """Ejecuta el pipeline hibrido completo para una pregunta."""

    parser = argparse.ArgumentParser(description="Ejecuta el pipeline hibrido completo de F1.")
    parser.add_argument("question", help="Pregunta del usuario en lenguaje natural.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Cantidad de fragmentos RAG a recuperar para apoyar el pipeline.",
    )
    args = parser.parse_args()

    result = run_hybrid_pipeline(args.question, top_k=args.top_k)
    print("=== SQL generada ===")
    print(result.generated_sql)
    print()
    print("=== Filas devueltas ===")
    print(result.query_result.row_count)
    print(result.query_result.rows[:10])
    print()
    print("=== Respuesta final ===")
    print(result.final_answer.answer)


if __name__ == "__main__":
    main()
