"""Página 6: Análise de Dados (EDA) — Exploração estatística multivariada do dataset industrial."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

    st.markdown(
        """
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                ANÁLISE EXPLORATÓRIA DE DADOS INDUSTRIAIS (EDA)
            </h1>
            <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                Caracterização do comportamento dos sensores por liga metálica, célula e classe de falha
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = carregar_dados_eda()
    if df.empty:
        st.warning("Dataset processado não encontrado em data/processed. Execute o pipeline de dados primeiro.")
        return

    # 1. Indicadores de Volume e Período
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total de Leituras", f"{len(df):,}")
    with m2:
        st.metric("Variáveis Totais", f"{df.shape[1]}")
    with m3:
        st.metric("Células Monitoradas", f"{df['id_celula'].nunique() if 'id_celula' in df else 4}")
    with m4:
        st.metric("Ligas Metálicas", f"{df['liga_metalica'].nunique() if 'liga_metalica' in df else 3}")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Distribuição por Liga e por Falha
    col_dist1, col_dist2 = st.columns(2)

    with col_dist1:
        st.markdown("<h4 style='font-size:0.95rem; font-weight:700;'>Distribuição de Leituras por Liga Metálica</h4>", unsafe_allow_html=True)
        if "liga_metalica" in df.columns:
            counts_liga = df["liga_metalica"].value_counts().reset_index()
            counts_liga.columns = ["Liga Metálica", "Contagem"]
            fig_pie = px.pie(
                counts_liga,
                names="Liga Metálica",
                values="Contagem",
                color="Liga Metálica",
                color_discrete_map={
                    "Aco_Carbono_316L": "#1D4ED8",
                    "Aluminio_7075": "#059669",
                    "Liga_Titanio_Ti6Al4V": "#7C3AED",
                },
                hole=0.45,
            )
            fig_pie.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_dist2:
        st.markdown("<h4 style='font-size:0.95rem; font-weight:700;'>Distribuição da Variável-Alvo (Classes de Falha)</h4>", unsafe_allow_html=True)
        if "tipo_falha" in df.columns:
            nomes_classes = {0: "0 - Normal", 1: "1 - Desgaste Ferramenta", 2: "2 - Falha Refrigeração", 3: "3 - Desalinhamento/Trinca"}
            counts_falha = df["tipo_falha"].map(nomes_classes).value_counts().reset_index()
            counts_falha.columns = ["Condição", "Registros"]
            fig_bar = px.bar(
                counts_falha,
                x="Condição",
                y="Registros",
                color="Condição",
                color_discrete_sequence=["#10B981", "#F59E0B", "#EF4444", "#8B5CF6"],
                text="Registros",
            )
            fig_bar.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 3. Análise do IEM (Índice de Esforço Mecânico)
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Comportamento do Índice de Esforço Mecânico (IEM)</h3>", unsafe_allow_html=True)

    if "indice_esforco_mecanico" in df.columns:
        iem_col1, iem_col2 = st.columns(2)
        with iem_col1:
            fig_box_iem = px.box(
                df,
                x="liga_metalica",
                y="indice_esforco_mecanico",
                color="liga_metalica",
                title="IEM por Liga Metálica (Esforço de Usinagem)",
                labels={"liga_metalica": "Liga Metálica", "indice_esforco_mecanico": "IEM"},
                color_discrete_sequence=["#1D4ED8", "#059669", "#7C3AED"],
            )
            fig_box_iem.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig_box_iem, use_container_width=True)

        with iem_col2:
            fig_hist_iem = px.histogram(
                df,
                x="indice_esforco_mecanico",
                color="tipo_falha",
                barmode="overlay",
                title="Distribuição do IEM por Classe de Falha",
                labels={"tipo_falha": "Tipo de Falha", "indice_esforco_mecanico": "IEM"},
                nbins=40,
            )
            fig_hist_iem.update_layout(height=320)
            st.plotly_chart(fig_hist_iem, use_container_width=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 4. Matriz de Correlação dos Sensores
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Matriz de Correlação Cruzada entre Sensores</h3>", unsafe_allow_html=True)
    sensores = [
        "temperatura_fuso_c",
        "vibracao_triaxial_rms_mms",
        "torque_fuso_nm",
        "vazao_refrigerante_lmin",
        "corrente_estator_amp",
        "pressao_hidraulica_bar",
        "nivel_ruido_db",
    ]
    cols_corr = [s for s in sensores if s in df.columns]
    if len(cols_corr) >= 4:
        matriz_corr = df[cols_corr].corr().round(2)
        fig_heat = px.imshow(
            matriz_corr,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            labels=dict(color="Correlação de Pearson"),
        )
        fig_heat.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_heat, use_container_width=True)

    # 5. Tabela Estatística Resumida
    st.markdown("<h4 style='font-size:0.95rem; font-weight:700;'>Tabela Resumo Estatístico dos Sensores</h4>", unsafe_allow_html=True)
    st.dataframe(df[cols_corr].describe().round(2).T, use_container_width=True)


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Análise de Dados (EDA)')
