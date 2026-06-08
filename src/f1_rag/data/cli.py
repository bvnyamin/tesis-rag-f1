"""Pequeno wrapper CLI para ejecutar el pipeline minimo de datos estructurados."""

from __future__ import annotations

from .pipeline import run_minimal_pipeline


def main() -> None:
    """Ejecuta el pipeline e imprime las rutas de los artefactos generados."""

    try:
        output_paths = run_minimal_pipeline()
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"El pipeline fallo: {exc}")
        raise SystemExit(1) from exc

    print("Pipeline minimo completado correctamente.")
    for label, path in output_paths.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
