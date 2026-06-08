"""Punto de entrada CLI para la etapa de embeddings e indexacion en Chroma."""

from __future__ import annotations

from .indexing_pipeline import run_indexing_pipeline


def main() -> None:
    """Ejecuta el pipeline de indexacion e imprime las rutas generadas."""

    try:
        output_paths = run_indexing_pipeline()
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError) as exc:
        print(f"El pipeline de indexacion fallo: {exc}")
        raise SystemExit(1) from exc

    print("Pipeline de indexacion completado correctamente.")
    for label, path in output_paths.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
