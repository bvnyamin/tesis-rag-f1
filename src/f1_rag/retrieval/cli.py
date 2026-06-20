"""Punto de entrada CLI para la etapa de embeddings e indexacion en Chroma."""

from __future__ import annotations

import argparse

from .indexing_pipeline import BatchProgress, run_indexing_pipeline


def main() -> None:
    """Ejecuta el pipeline de indexacion e imprime las rutas generadas."""

    parser = argparse.ArgumentParser(
        description="Genera embeddings e indexa fragmentos RAG en Chroma por lotes."
    )
    parser.add_argument(
        "--documents-path",
        default="data/processed/rag_documents.jsonl",
        help="Ruta del archivo JSONL con documentos serializados para RAG.",
    )
    parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Carpeta donde se deja el resumen de indexacion.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Cantidad de documentos iniciales a saltar antes de indexar.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad maxima de documentos a indexar desde el offset indicado.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Tamano del lote de documentos que se procesa e indexa en cada iteracion.",
    )
    args = parser.parse_args()

    try:
        output_paths = run_indexing_pipeline(
            documents_path=args.documents_path,
            processed_dir=args.processed_dir,
            offset=args.offset,
            limit=args.limit,
            batch_size=args.batch_size,
            progress_callback=_print_batch_progress,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError) as exc:
        print(f"El pipeline de indexacion fallo: {exc}")
        raise SystemExit(1) from exc

    print("Pipeline de indexacion completado correctamente.")
    for label, path in output_paths.items():
        print(f"- {label}: {path}")


def _print_batch_progress(progress: BatchProgress) -> None:
    """Imprime el avance de la indexacion en consola."""

    if progress.target_documents is None:
        print(
            f"Lote {progress.batch_number}: {progress.batch_size} documentos indexados "
            f"(acumulado: {progress.processed_documents}).",
            flush=True,
        )
        return

    percentage = (progress.processed_documents / progress.target_documents) * 100
    print(
        f"Lote {progress.batch_number}: {progress.batch_size} documentos indexados "
        f"(acumulado: {progress.processed_documents}/{progress.target_documents}, "
        f"{percentage:.1f}%).",
        flush=True,
    )


if __name__ == "__main__":
    main()
