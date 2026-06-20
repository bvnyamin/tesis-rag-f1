"""CLI para ejecutar benchmark del pipeline híbrido."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1_rag.config import AppConfig

from .benchmark import (
    benchmark_suite_to_dict,
    load_benchmark_cases,
    render_benchmark_summary,
    run_benchmark_suite,
)


def main() -> None:
    """Ejecuta el benchmark híbrido y guarda un reporte JSON."""

    parser = argparse.ArgumentParser(description="Ejecuta el benchmark del pipeline híbrido de F1.")
    parser.add_argument(
        "--cases-path",
        default="benchmarks/hybrid_benchmark_cases.json",
        help="Ruta del archivo JSON con los casos del benchmark.",
    )
    parser.add_argument(
        "--output-path",
        default="data/processed/benchmark_report.json",
        help="Ruta donde se guardará el reporte JSON.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        help="Permite ejecutar uno o más case_id específicos.",
    )
    args = parser.parse_args()

    try:
        all_cases = load_benchmark_cases(args.cases_path)
        selected_cases = _filter_cases(all_cases, args.case_id)
        suite_result = run_benchmark_suite(selected_cases, config=AppConfig.from_env())
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"El benchmark falló: {exc}")
        raise SystemExit(1) from exc

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(benchmark_suite_to_dict(suite_result), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(render_benchmark_summary(suite_result))
    print(f"Reporte JSON guardado en: {output_path}")


def _filter_cases(cases, selected_case_ids):
    """Filtra casos por id si se solicitaron explícitamente."""

    if not selected_case_ids:
        return cases

    selected = [case for case in cases if case.case_id in set(selected_case_ids)]
    if not selected:
        raise ValueError("Ningún case_id solicitado coincide con los casos del benchmark.")
    return selected


if __name__ == "__main__":
    main()
