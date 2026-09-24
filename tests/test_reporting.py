"""Pruebas de seleccion de metricas y graficos del reporte."""

from decimal import Decimal
import unittest

from f1_rag.database.query_executor import QueryExecutionResult
from f1_rag.ui.reporting import build_query_report


class ReportingTests(unittest.TestCase):
    def test_season_wins_with_decimal_cumulative_value_uses_line_chart(self):
        result = QueryExecutionResult(
            query="SELECT season_year, driver_name, season_wins, cumulative_wins FROM season_summary",
            columns=["season_year", "driver_name", "season_wins", "cumulative_wins"],
            rows=[
                {"season_year": 2007, "driver_name": "Lewis Hamilton", "season_wins": 4, "cumulative_wins": Decimal("4")},
                {"season_year": 2008, "driver_name": "Lewis Hamilton", "season_wins": 5, "cumulative_wins": Decimal("9")},
            ],
            row_count=2,
        )

        report = build_query_report(result)

        self.assertEqual(report.primary_metric, "season_wins")
        self.assertIsNotNone(report.chart_spec)
        self.assertEqual(report.chart_spec.chart_type, "line")
        self.assertEqual(report.chart_spec.x_column, "season_year")
        self.assertEqual(report.chart_spec.y_columns, ["season_wins"])
