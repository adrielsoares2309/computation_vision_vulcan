"""Página 6: Análise de Dados (EDA) — Exploração Técnica e Diagnóstico de Sensores por Liga Metálica."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.styles import DESIGN_TOKENS

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_FEATURES = RAIZ / "data" / "processed" / "dados_sensores_vulcantech_features.parquet"
CAMINHO_TRATADO = RAIZ / "data" / "processed" / "dados_sensores_vulcantech_tratados.parquet"


@st.cache_data
def carregar_dados_eda() -> pd.DataFrame:
    caminho = CAMINHO_FEATURES if CAMINHO_FEATURES.is_file() else CAMINHO_TRATADO
    if not caminho.is_file():
        return pd.DataFrame()
    return pd.read_parquet(caminho)


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    render_header(
        title="Análise de Dados Operacionais (EDA)",
        description="Caracterização estatística multivariada, comportamento do IEM e correlação de sensores por liga metálica.",
        icon="chart_no_axes_combined",
        context_badge=("12.000 LEITURAS", "info"),
    )

    df = carregar_dados_eda()
    if df.empty:
        st.warning("Base analítica processada não encontrada em data/processed. Execute o pipeline de engenharia de dados.")
        return

    # 1. Indicadores Resumidos de Escopo
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("Total de Amostras", f"{len(df):,}", "Observações industriais", "activity", "primary")
    with k2:
        render_kpi("Variáveis / Atributos", f"{df.shape[1]} colunas", "Telemetria + Features", "layers", "primary")
    with k3:
        render_kpi("Células Monitoradas", "4 Células", "CEL-201 a CEL-204", "factory", "primary")
    with k4:
        render_kpi("Ligas Analisadas", "3 Ligas", "Aço, Alumínio e Titânio", "box", "primary")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Resposta Direta a Perguntas Operacionais
    col_iem, col_classes = st.columns([1.1, 1.0])

    with col_iem:
        st.markdown(
            f'<div class="section-title">{svg_icon("gauge", c["text_heading"], 15)} Comportamento do IEM por Liga Metálica</div>',
            unsafe_allow_html=True,
        )
        if "indice_esforco_mecanico" in df.columns and "liga_metalica" in df.columns:
            fig_iem = px.box(
                df,
                x="liga_metalica",
                y="indice_esforco_mecanico",
                color="liga_metalica",
                labels={"liga_metalica": "Liga", "indice_esforco_mecanico": "IEM (pts)"},
                color_discrete_sequence=["#1565C0", "#10B981", "#7C3AED"],
            )
            apply_chart_theme(fig_iem, height=250)
            fig_iem.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_iem, use_container_width=True, config={"displayModeBar": False})

    with col_classes:
        st.markdown(
            f'<div class="section-title">{svg_icon("activity", c["text_heading"], 15)} Distribuição de Classes de Falha</div>',
            unsafe_allow_html=True,
        )
        if "tipo_falha" in df.columns:
            nomes_classes = {0: "0 - Normal", 1: "1 - Estampagem", 2: "2 - Eixo CNC", 3: "3 - Solda"}
            counts = df["tipo_falha"].map(nomes_classes).value_counts().reset_index()
            counts.columns = ["Condição", "Registros"]
            fig_classes = px.bar(
                counts,
                x="Condição",
                y="Registros",
                color="Condição",
                color_discrete_sequence=["#10B981", "#3B82F6", "#F59E0B", "#EF4444"],
                text="Registros",
            )
            apply_chart_theme(fig_classes, height=250)
            fig_classes.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_classes, use_container_width=True, config={"displayModeBar": False})

    # 3. Matriz de Correlação dos Preditores (Em Seção Secundária Recolhida)
    with st.expander("Matriz de Correlação Cruzada entre Preditores de Sensores", expanded=False):
        cols_sensor = [
            "temperatura_fuso_c",
            "vibracao_triaxial_rms_mms",
            "torque_fuso_nm",
            "vazao_refrigerante_lmin",
            "corrente_estator_amp",
            "pressao_hidraulica_bar",
            "indice_esforco_mecanico",
        ]
        cols_existentes = [c for c in cols_sensor if c in df.columns]
        if len(cols_existentes) >= 2:
            corr = df[cols_existentes].corr()
            labels_curtos = [c.replace("_c", "").replace("_nm", "").replace("_mms", "").replace("_bar", "").replace("_amp", "") for c in cols_existentes]
            fig_corr = go.Figure(
                data=go.Heatmap(
                    z=corr.values,
                    x=labels_curtos,
                    y=labels_curtos,
                    colorscale="Blues",
                    zmin=-1.0,
                    zmax=1.0,
                    text=np.round(corr.values, 2),
                    texttemplate="%{text}",
                )
            )
            apply_chart_theme(fig_corr, height=300)
            fig_corr.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Análise de Dados (EDA)")
