"""Utilidades para cargar datasets CSV de Formula 1 desde disco."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class DatasetBundle:
    """Contenedor para multiples tablas CSV relacionadas."""

    tables: dict[str, pd.DataFrame]
    source_dir: Path


def load_csv_bundle(raw_dir: str | Path) -> DatasetBundle:
    """Carga cada archivo CSV de ``raw_dir`` en un diccionario de tablas.

    El nombre del archivo sin extension se usa como nombre de la tabla.
    """

    source_dir = Path(raw_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"No se encontro el directorio de datos raw: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"La ruta de datos raw no es un directorio: {source_dir}")

    csv_files = sorted(source_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No se encontraron archivos CSV en: {source_dir}")

    tables: dict[str, pd.DataFrame] = {}
    for csv_file in csv_files:
        table_name = csv_file.stem
        try:
            tables[table_name] = pd.read_csv(
                csv_file,
                na_values=["\\N"],
                keep_default_na=True,
            )
        except Exception as exc:  # pragma: no cover - guardia defensiva
            raise ValueError(f"Error al leer el archivo CSV '{csv_file.name}': {exc}") from exc

    return DatasetBundle(tables=tables, source_dir=source_dir)
