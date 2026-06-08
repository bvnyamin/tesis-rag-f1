"""Funciones de preparacion inicial para datos estructurados de Formula 1."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .loader import DatasetBundle


@dataclass(slots=True)
class PreparationSummary:
    """Resumen liviano de lo ocurrido durante la preparacion."""

    table_name: str
    input_rows: int
    output_rows: int
    dropped_duplicate_rows: int
    normalized_columns: list[str]


def prepare_dataset_bundle(bundle: DatasetBundle) -> tuple[DatasetBundle, list[PreparationSummary]]:
    """Aplica una limpieza minima a cada tabla del bundle.

    La preparacion actual es intencionalmente conservadora:
    - elimina espacios alrededor de los nombres de columnas
    - normaliza columnas a snake_case en minusculas
    - recorta espacios en valores de texto
    - reemplaza strings vacios por valores faltantes
    - elimina filas completamente duplicadas
    """

    prepared_tables: dict[str, pd.DataFrame] = {}
    summaries: list[PreparationSummary] = []

    for table_name, dataframe in bundle.tables.items():
        prepared_df = prepare_table(dataframe)
        prepared_tables[table_name] = prepared_df
        summaries.append(
            PreparationSummary(
                table_name=table_name,
                input_rows=len(dataframe),
                output_rows=len(prepared_df),
                dropped_duplicate_rows=len(dataframe) - len(prepared_df),
                normalized_columns=list(prepared_df.columns),
            )
        )

    return DatasetBundle(tables=prepared_tables, source_dir=bundle.source_dir), summaries


def prepare_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia limpia de un DataFrame."""

    if dataframe.empty:
        return dataframe.copy()

    prepared = dataframe.copy()
    prepared.columns = [_normalize_column_name(column) for column in prepared.columns]

    for column in prepared.columns:
        if pd.api.types.is_object_dtype(prepared[column]) or pd.api.types.is_string_dtype(
            prepared[column]
        ):
            prepared[column] = prepared[column].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
            prepared[column] = prepared[column].replace("", pd.NA)

    prepared = prepared.drop_duplicates().reset_index(drop=True)
    return prepared


def _normalize_column_name(column_name: object) -> str:
    """Normaliza nombres de columna libres a un formato snake_case estable."""

    normalized = str(column_name).strip().lower()
    for old, new in ((" ", "_"), ("-", "_"), ("/", "_")):
        normalized = normalized.replace(old, new)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized
