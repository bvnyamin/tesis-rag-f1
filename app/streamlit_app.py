"""Aplicacion Streamlit minima para el pipeline hibrido de F1."""

from __future__ import annotations

from pathlib import Path
import re
import sys

import altair as alt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from f1_rag.orchestration import run_direct_llm_pipeline, run_hybrid_pipeline
from f1_rag.nl2sql import OutOfDomainQuestionError, UnsafeQuestionError


UTEM_CUSTOM_CSS = """
<style>
    :root {
        --utem-blue: #004EAA;
        --utem-blue-deep: #0B2341;
        --utem-green: #78BF26;
        --utem-white: #FFFFFF;
        --utem-ink: #EAF1FB;
        --utem-muted: #A9BAD3;
        --utem-surface: rgba(11, 35, 65, 0.72);
        --utem-surface-strong: rgba(7, 24, 46, 0.92);
        --utem-border: rgba(120, 191, 38, 0.22);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(0, 78, 170, 0.26), transparent 32%),
            radial-gradient(circle at top right, rgba(120, 191, 38, 0.18), transparent 24%),
            linear-gradient(180deg, #061425 0%, #091B31 48%, #081423 100%);
        color: var(--utem-ink);
    }

    .stApp, .stMarkdown, .stText, .stCaption, .stCodeBlock, .st-emotion-cache-10trblm, .st-emotion-cache-16idsys {
        font-family: "Montserrat", "Aptos", "Segoe UI", sans-serif;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 1.7rem;
        padding-bottom: 3.25rem;
    }

    .project-hero {
        background:
            linear-gradient(135deg, rgba(0, 78, 170, 0.22), rgba(11, 35, 65, 0.94)),
            linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.00));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 5px solid var(--utem-green);
        border-radius: 22px;
        padding: 1.35rem 1.45rem 1.1rem 1.45rem;
        margin-bottom: 1.05rem;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
    }

    .project-kicker {
        display: inline-block;
        margin-bottom: 0.65rem;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        background: rgba(120, 191, 38, 0.14);
        color: #DFF4C7;
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }

    .project-title {
        margin: 0;
        color: var(--utem-white);
        font-size: clamp(1.85rem, 2.7vw, 2.7rem);
        line-height: 1.12;
        font-weight: 800;
        letter-spacing: -0.03em;
    }

    .project-subtitle {
        margin-top: 0.75rem;
        margin-bottom: 0;
        max-width: 62rem;
        color: var(--utem-ink);
        font-size: 0.98rem;
        line-height: 1.58;
    }

    .stForm {
        background: var(--utem-surface-strong);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 0.95rem 0.95rem 0.35rem 0.95rem;
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
    }

    .stForm [data-testid="stWidgetLabel"] p {
        color: var(--utem-white);
        font-weight: 600;
        letter-spacing: 0.01em;
    }

    .stTextArea textarea, .stTextInput input {
        background: linear-gradient(180deg, rgba(7, 22, 40, 0.96), rgba(11, 29, 50, 0.94)) !important;
        color: var(--utem-white) !important;
        border: 1px solid rgba(90, 136, 194, 0.34) !important;
        border-radius: 18px !important;
        line-height: 1.55 !important;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.03),
            0 0 0 1px rgba(0, 0, 0, 0.10),
            0 12px 28px rgba(0, 0, 0, 0.16);
        padding-top: 0.85rem !important;
        padding-bottom: 0.85rem !important;
    }

    .stTextArea textarea:hover, .stTextInput input:hover {
        border-color: rgba(120, 191, 38, 0.34) !important;
        background: linear-gradient(180deg, rgba(8, 24, 44, 0.98), rgba(12, 32, 55, 0.96)) !important;
    }

    .stTextArea textarea:focus, .stTextArea textarea:focus-visible,
    .stTextInput input:focus, .stTextInput input:focus-visible {
        border: 1px solid rgba(120, 191, 38, 0.82) !important;
        box-shadow:
            0 0 0 1px rgba(120, 191, 38, 0.20),
            0 0 0 4px rgba(120, 191, 38, 0.12),
            0 18px 36px rgba(0, 0, 0, 0.22) !important;
        outline: none !important;
    }

    .stButton > button, .stForm button[kind="primary"] {
        background: linear-gradient(135deg, var(--utem-blue), #0C63D4) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.65rem 1.15rem !important;
        font-weight: 700 !important;
        box-shadow: 0 12px 28px rgba(0, 78, 170, 0.28) !important;
    }

    .stButton > button:hover, .stForm button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 16px 34px rgba(0, 78, 170, 0.34) !important;
    }

    div[data-testid="stSlider"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 18px;
        padding: 0.8rem 0.95rem 0.5rem 0.95rem;
        margin-top: 0.15rem;
        margin-bottom: 0.2rem;
    }

    div[data-testid="stSlider"] [role="group"] > div {
        background: rgba(255, 255, 255, 0.12) !important;
        border-radius: 999px !important;
        min-height: 0.45rem !important;
    }

    div[data-testid="stSlider"] [role="group"] > div > div:first-child {
        background: linear-gradient(90deg, var(--utem-green), var(--utem-blue)) !important;
        border-radius: 999px !important;
        min-height: 0.45rem !important;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.04);
    }

    div[data-testid="stSliderThumbValue"] {
        background: linear-gradient(135deg, var(--utem-blue-deep), var(--utem-blue));
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: white !important;
        border-radius: 999px;
        padding: 0.08rem 0.45rem;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
    }

    div[data-testid="stSlider"] [data-testid="stSliderTickBar"] p {
        color: var(--utem-muted) !important;
        font-size: 0.8rem;
    }

    div[data-testid="stCheckbox"] {
        margin-top: 0.25rem;
    }

    div[data-testid="stCheckbox"] label {
        width: 100%;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
        padding: 0.72rem 0.88rem;
        transition: border-color 0.2s ease, background 0.2s ease;
    }

    div[data-testid="stCheckbox"] label > div:first-of-type {
        background: rgba(255, 255, 255, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 999px !important;
        padding: 0.1rem !important;
    }

    div[data-testid="stCheckbox"] label > div:first-of-type > div {
        background: #FFFFFF !important;
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.18);
    }

    div[data-testid="stCheckbox"] label:has(input[role="switch"]:checked) {
        background: rgba(120, 191, 38, 0.08);
        border-color: rgba(120, 191, 38, 0.35);
    }

    div[data-testid="stCheckbox"] label:has(input[role="switch"]:checked) > div:first-of-type {
        background: linear-gradient(135deg, var(--utem-green), #9DD84D) !important;
        border-color: rgba(255, 255, 255, 0.18);
    }

    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p {
        color: var(--utem-white) !important;
        font-weight: 700;
    }

    .mode-legend {
        margin-top: 0.2rem;
        margin-bottom: 0.4rem;
        padding: 0.8rem 0.95rem;
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        color: var(--utem-ink);
        line-height: 1.55;
        font-size: 0.93rem;
    }

    .mode-legend strong {
        color: var(--utem-white);
    }

    div[data-testid="stSegmentedControl"] {
        margin-top: 0.2rem;
        margin-bottom: 0.35rem;
    }

    div[data-testid="stSegmentedControl"] [role="radiogroup"] {
        background: rgba(11, 35, 65, 0.88);
        border: 1px solid rgba(0, 78, 170, 0.28);
        border-radius: 18px;
        padding: 0.38rem;
        gap: 0.35rem;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.03),
            0 12px 28px rgba(0, 0, 0, 0.18);
    }

    div[data-testid="stSegmentedControl"] [role="radio"] {
        border-radius: 14px !important;
        border: 1px solid rgba(0, 78, 170, 0.16) !important;
        background: rgba(255, 255, 255, 0.04) !important;
        color: var(--utem-ink) !important;
        min-height: 3rem !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
        transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }

    div[data-testid="stSegmentedControl"] [role="radio"]:hover {
        border-color: rgba(120, 191, 38, 0.34) !important;
        background: rgba(255, 255, 255, 0.06) !important;
        transform: translateY(-1px);
    }

    div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] {
        background: #004EAA !important;
        border-color: #78BF26 !important;
        color: white !important;
        box-shadow:
            inset 0 -3px 0 rgba(120, 191, 38, 0.88),
            0 0 0 1px rgba(255, 255, 255, 0.04),
            0 10px 24px rgba(0, 78, 170, 0.24) !important;
    }

    div[data-testid="stSegmentedControl"] [role="radio"] p {
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        line-height: 1.2 !important;
    }

    .stExpander {
        background: var(--utem-surface);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px !important;
        overflow: hidden;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
        margin-top: 0.45rem;
        margin-bottom: 0.45rem;
    }

    .stExpander summary {
        font-weight: 700;
        color: var(--utem-white);
    }

    .stAlert {
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .stDataFrame, .stCodeBlock {
        border-radius: 16px;
        overflow: hidden;
    }

    .stMarkdown h2, .stMarkdown h3 {
        color: var(--utem-white);
        letter-spacing: -0.02em;
    }

    .stProgress {
        margin-top: 0.15rem;
        margin-bottom: 0.35rem;
    }

    .stProgress [role="progressbar"] {
        background: linear-gradient(90deg, var(--utem-green), #A8DF5A) !important;
        border-radius: 999px !important;
        min-height: 0.52rem !important;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.05), 0 6px 18px rgba(120, 191, 38, 0.22) !important;
    }

    div[data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 0.25rem;
    }

    .element-container {
        margin-top: 0.2rem !important;
        margin-bottom: 0.45rem !important;
    }

    div[data-testid="stCodeBlock"] {
        border-radius: 16px;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2.5rem;
        }

        .project-hero {
            padding: 1.1rem 1.05rem 0.95rem 1.05rem;
            border-radius: 18px;
        }

        .project-title {
            font-size: 1.55rem;
            line-height: 1.18;
        }

        .project-subtitle {
            font-size: 0.93rem;
            line-height: 1.52;
        }
    }

    .stCaption {
        color: var(--utem-muted) !important;
    }
</style>
"""


def build_non_rag_sources(sql_query: str) -> list[str]:
    """Resume las fuentes estructuradas usadas cuando el modo RAG esta desactivado."""

    normalized_sql = sql_query.lower()
    tables = []
    for table_name in (
        "drivers",
        "constructors",
        "circuits",
        "races",
        "results",
        "qualifying",
        "driver_standings",
        "constructor_standings",
        "sprint_results",
        "status",
    ):
        if re.search(rf"\b{table_name}\b", normalized_sql):
            tables.append(table_name)

    if not tables:
        return ["PostgreSQL: consulta estructurada sobre el dataset de Formula 1."]

    table_list = ", ".join(tables)
    return [
        "PostgreSQL: respuesta generada exclusivamente desde datos estructurados.",
        f"Tablas consultadas: {table_list}.",
        "No se utilizaron fragmentos recuperados desde Chroma.",
    ]


st.set_page_config(page_title="RAG Hibrido F1", layout="wide")
st.markdown(UTEM_CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <section class="project-hero">
        <div class="project-kicker">Prototipo de tesis UTEM</div>
        <h1 class="project-title">Estudio de Retrieval-Augmented Generation para consultas en lenguaje natural sobre datos estructurados</h1>
        <p class="project-subtitle">
            Prototipo aplicado a Fórmula 1 que combina recuperación semántica, generación de SQL,
            consulta estructurada en PostgreSQL y apoyo analítico para responder preguntas en lenguaje natural
            con trazabilidad y evidencia.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

default_question = "Quien gano el Australian Grand Prix de 2008?"
MODE_HYBRID = "Híbrido completo"
MODE_SQL_ONLY = "SQL sin RAG"
MODE_LLM_ONLY = "LLM puro"

with st.form("hybrid_query_form"):
    question = st.text_area(
        "Pregunta",
        value=default_question,
        height=100,
        help="Escribe una pregunta sobre pilotos, carreras, resultados o temporadas de Formula 1.",
    )
    execution_mode = st.segmented_control(
        "Modo de ejecución",
        options=[MODE_HYBRID, MODE_SQL_ONLY, MODE_LLM_ONLY],
        default=MODE_HYBRID,
        help=(
            "Híbrido completo: usa RAG, genera SQL y responde con apoyo del LLM. "
            "SQL sin RAG: genera SQL y muestra solo la salida estructurada de PostgreSQL, sin recuperar fragmentos desde Chroma ni redactar una respuesta final. "
            "LLM puro: responde solo con conocimiento del modelo, sin consultar datos reales."
        ),
    )
    st.markdown(
        """
        <div class="mode-legend">
            <strong>Híbrido completo:</strong> usa Chroma + PostgreSQL + LLM para responder con evidencia.<br>
            <strong>SQL sin RAG:</strong> genera SQL y muestra únicamente la salida estructurada cruda.<br>
            <strong>LLM puro:</strong> responde solo con el conocimiento del modelo, sin verificar contra el dataset.
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_k = st.slider(
        "Cantidad de fragmentos RAG",
        min_value=1,
        max_value=10,
        value=3,
        disabled=execution_mode != MODE_HYBRID,
    )
    submitted = st.form_submit_button("Consultar")

if submitted:
    progress_placeholder = st.empty()
    progress_bar = st.progress(0, text="Preparando ejecucion...")

    def update_progress(_: str, message: str, current_step: int, total_steps: int) -> None:
        """Actualiza el progreso visible del pipeline para la interfaz."""

        progress_ratio = min(max(current_step / total_steps, 0.0), 1.0)
        progress_bar.progress(progress_ratio, text=message)
        progress_placeholder.caption(f"Paso {current_step} de {total_steps}: {message}")

    try:
        if execution_mode == MODE_LLM_ONLY:
            direct_result = run_direct_llm_pipeline(
                question=question,
                progress_callback=update_progress,
            )
            result = None
        else:
            use_rag = execution_mode == MODE_HYBRID
            result = run_hybrid_pipeline(
                question=question,
                top_k=top_k,
                enable_rag=use_rag,
                enable_final_response=use_rag,
                progress_callback=update_progress,
            )
            direct_result = None
    except OutOfDomainQuestionError as exc:
        progress_bar.empty()
        progress_placeholder.empty()
        st.warning(str(exc))
    except UnsafeQuestionError as exc:
        progress_bar.empty()
        progress_placeholder.empty()
        st.error(f"No se ejecutara la solicitud: {exc}")
    except Exception as exc:
        progress_bar.empty()
        progress_placeholder.empty()
        st.error(f"La consulta fallo: {exc}")
    else:
        progress_bar.progress(1.0, text="Pipeline completado.")
        progress_placeholder.caption("Consulta completada correctamente.")
        if direct_result is not None:
            if direct_result.advisory_message:
                st.info(direct_result.advisory_message)

            st.warning(
                "Modo activo: LLM puro. Esta respuesta no consulto PostgreSQL ni Chroma; "
                "se genera solo con el conocimiento previo del modelo."
            )

            if direct_result.stage_timings:
                timing_parts = [
                    f"{stage_name}: {duration:.2f}s"
                    for stage_name, duration in direct_result.stage_timings.items()
                ]
                st.caption("Tiempos por etapa: " + " | ".join(timing_parts))

            with st.expander("1. Respuesta del LLM puro", expanded=True):
                st.write(direct_result.final_answer.answer)

            with st.expander("2. Limitaciones de este modo", expanded=False):
                st.write(
                    "Este modo no usa recuperación RAG ni consulta SQL. "
                    "Por eso puede responder de forma fluida, pero sin verificar la información "
                    "contra datos reales del dataset."
                )
        else:
            report = result.query_report

            if result.advisory_message:
                st.info(result.advisory_message)

            if execution_mode == MODE_SQL_ONLY:
                st.info(
                    "Modo activo: SQL sin RAG. Se genera una consulta SQL y se muestra solo la evidencia estructurada cruda de PostgreSQL, "
                    "sin recuperación semántica ni redacción final."
                )
            else:
                st.info("Modo activo: pipeline híbrido completo con RAG + SQL + LLM.")

            if result.stage_timings:
                timing_parts = [
                    f"{stage_name}: {duration:.2f}s"
                    for stage_name, duration in result.stage_timings.items()
                ]
                st.caption("Tiempos por etapa: " + " | ".join(timing_parts))

            with st.expander("1. SQL generada", expanded=False):
                st.code(result.generated_sql, language="sql")

            with st.expander("2. Resultado tabular", expanded=True):
                st.caption(f"Filas devueltas: {result.query_result.row_count}")
                if result.query_result.rows:
                    st.dataframe(report.dataframe, use_container_width=True)
                else:
                    st.info("La consulta SQL no devolvio filas.")

            if execution_mode == MODE_SQL_ONLY:
                with st.expander("3. Fuentes estructuradas consultadas", expanded=False):
                    sources = build_non_rag_sources(result.generated_sql)
                    for source in sources:
                        st.write(f"- {source}")
            else:
                with st.expander("3. Contexto recuperado", expanded=False):
                    st.text(result.rag_context)

                    for index, chunk in enumerate(result.retrieved_chunks, start=1):
                        st.markdown(f"**Chunk {index}**")
                        st.write(chunk.text)
                        st.caption(chunk.metadata)

                with st.expander("4. Resumen analítico", expanded=True):
                    st.write(report.summary_text)
                    st.caption(report.headline_text)

                if report.chart_spec is not None and not report.dataframe.empty:
                    with st.expander("5. Visualización", expanded=True):
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

                if result.final_answer is not None:
                    with st.expander("6. Respuesta final", expanded=True):
                        st.write(result.final_answer.answer)
