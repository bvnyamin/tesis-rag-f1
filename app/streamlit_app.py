"""Aplicacion Streamlit minima para el pipeline hibrido de F1."""

from __future__ import annotations

from pathlib import Path
import sys

import altair as alt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from f1_rag.orchestration import run_hybrid_pipeline
st.set_page_config(page_title="RAG Hibrido F1", layout="wide")

st.title("RAG Hibrido F1")
st.caption("Consulta hibrida sobre Formula 1 usando RAG, SQL y generacion final con modelos de lenguaje.")

st.write(
    """
    Esta app recibe una pregunta en lenguaje natural, recupera contexto semantico,
    genera SQL, consulta PostgreSQL y construye una respuesta final basada en evidencia.
    """
)

default_question = "Quien gano el Australian Grand Prix de 2008?"

with st.form("hybrid_query_form"):
    question = st.text_area(
        "Pregunta",
        value=default_question,
        height=100,
        help="Escribe una pregunta sobre pilotos, carreras, resultados o temporadas de Formula 1.",
    )
    top_k = st.slider("Cantidad de fragmentos RAG", min_value=1, max_value=10, value=3)
    submitted = st.form_submit_button("Consultar")

if submitted:
    try:
        with st.spinner("Ejecutando pipeline hibrido..."):
            result = run_hybrid_pipeline(question=question, top_k=top_k)
    except Exception as exc:
        st.error(f"La consulta fallo: {exc}")
    else:
        report = result.query_report

        st.subheader("Respuesta final")
        st.write(result.final_answer.answer)

        st.subheader("Resumen analítico")
        st.write(report.summary_text)
        st.caption(report.headline_text)

        if report.chart_spec is not None and not report.dataframe.empty:
            st.subheader("Visualización")
            st.caption(report.chart_spec.title)
            chart_dataframe = report.dataframe.copy()
            if report.chart_spec.sort_by and report.chart_spec.sort_by in chart_dataframe.columns:
                chart_dataframe = chart_dataframe.sort_values(
                    by=report.chart_spec.sort_by,
                    ascending=report.chart_spec.sort_ascending,
                    kind="stable",
                )
            if report.chart_spec.chart_type == "line":
                value_column = report.chart_spec.y_columns[0]
                chart = (
                    alt.Chart(chart_dataframe)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(
                            f"{report.chart_spec.x_column}:Q",
                            title=report.chart_spec.x_column,
                        ),
                        y=alt.Y(f"{value_column}:Q", title=value_column),
                        tooltip=[
                            alt.Tooltip(f"{report.chart_spec.x_column}:Q", title=report.chart_spec.x_column),
                            alt.Tooltip(f"{value_column}:Q", title=value_column),
                        ],
                    )
                )
                st.altair_chart(chart, use_container_width=True)
            elif report.chart_spec.chart_type == "bar":
                value_column = report.chart_spec.y_columns[0]
                chart = (
                    alt.Chart(chart_dataframe)
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            f"{report.chart_spec.x_column}:N",
                            sort=chart_dataframe[report.chart_spec.x_column].tolist(),
                            title=report.chart_spec.x_column,
                            axis=alt.Axis(labelAngle=-45),
                        ),
                        y=alt.Y(f"{value_column}:Q", title=value_column),
                        tooltip=[
                            alt.Tooltip(f"{report.chart_spec.x_column}:N", title=report.chart_spec.x_column),
                            alt.Tooltip(f"{value_column}:Q", title=value_column),
                        ],
                    )
                )
                st.altair_chart(chart, use_container_width=True)
        elif report.no_chart_reason and report.no_chart_reason not in report.summary_text:
            st.info(report.no_chart_reason)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("SQL generada")
            st.code(result.generated_sql, language="sql")

            st.subheader("Resultado tabular")
            st.caption(f"Filas devueltas: {result.query_result.row_count}")
            if result.query_result.rows:
                st.dataframe(report.dataframe, use_container_width=True)
            else:
                st.info("La consulta SQL no devolvio filas.")

        with col2:
            st.subheader("Contexto recuperado")
            st.text(result.rag_context)

        with st.expander("Ver fragmentos recuperados"):
            for index, chunk in enumerate(result.retrieved_chunks, start=1):
                st.markdown(f"**Chunk {index}**")
                st.write(chunk.text)
                st.caption(chunk.metadata)
