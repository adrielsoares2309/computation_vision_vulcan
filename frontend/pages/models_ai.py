"""Página 7: Modelos de IA — Benchmark, métricas, matriz de confusão e explicabilidade."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.services.api_client import get_api_client
from frontend.styles import DESIGN_TOKENS

RAIZ = Path(__file__).resolve().parents[2]
REPORTS_DIR = RAIZ / "reports" / "ml"
MODELS_DIR = RAIZ / "models" / "tabular"


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    st.markdown(
        """
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                INTELIGÊNCIA ARTIFICIAL & MODELOS PREDITIVOS
            </h1>
            <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                Avaliação comparativa de algoritmos, matriz de confusão temporal e explicabilidade de features
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Carrega métricas reais dos relatórios
    caminho_meta = MODELS_DIR / "model_metadata.json"
    caminho_comp = REPORTS_DIR / "model_comparison.csv"
    caminho_matriz = REPORTS_DIR / "confusion_matrix.csv"
    caminho_imp = REPORTS_DIR / "feature_importance.csv"

    if not caminho_meta.is_file():
        st.warning("Metadados dos modelos não encontrados. Execute 'python -m src.ml.train' para treinar os algoritmos.")
        return

    meta = json.loads(caminho_meta.read_text(encoding="utf-8"))
    test_metrics = meta.get("test_metrics", {})
    val_metrics = meta.get("validation_metrics", {})

    # 1. Quatro Cards Principais de Desempenho no Teste Cronológico
    col1, col2, col3, col4 = st.columns(4)

    acc = test_metrics.get("accuracy", 0.0)
    rec_falhas = test_metrics.get("recall_falhas_macro", 0.0)
    f1_macro = test_metrics.get("f1_macro", 0.0)
    roc_auc = test_metrics.get("roc_auc_ovr_macro", 0.0)

    with col1:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #1D4ED8; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569;">MODELO VENCEDOR</div>
                <div style="font-size:1.5rem; font-weight:800; color:#0F172A;">{meta.get('model_name', 'RandomForest')}</div>
                <div style="font-size:0.75rem; color:#059669; font-weight:600;">Validação Temporal Estrita</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #059669; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569;">RECALL DE FALHAS (TESTE)</div>
                <div style="font-size:1.5rem; font-weight:800; color:#059669;">{rec_falhas:.1%}</div>
                <div style="font-size:0.75rem; color:#059669;">Meta do Projeto: &ge; 90.0%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #D97706; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569;">F1-SCORE MACRO</div>
                <div style="font-size:1.5rem; font-weight:800; color:#0F172A;">{f1_macro:.3f}</div>
                <div style="font-size:0.75rem; color:#475569;">Acurácia: {acc:.1%}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #7C3AED; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569;">ROC-AUC OVR MACRO</div>
                <div style="font-size:1.5rem; font-weight:800; color:#0F172A;">{roc_auc:.4f}</div>
                <div style="font-size:0.75rem; color:#475569;">Capacidade de Separação</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Tabela de Comparação de Algoritmos
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Comparação de Famílias de Algoritmos (Validação Cronológica)</h3>", unsafe_allow_html=True)

    if caminho_comp.is_file():
        df_comp = pd.read_csv(caminho_comp)
        colunas_exibir = [c for c in ["model", "recall_falhas_macro", "f1_macro", "precision_macro", "accuracy"] if c in df_comp.columns]
        df_exibir = df_comp[colunas_exibir].copy().round(4)
        df_exibir.columns = ["Algoritmo", "Recall Falhas Macro", "F1 Macro", "Precisão Macro", "Acurácia"]
        st.dataframe(df_exibir, use_container_width=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 3. Matriz de Confusão e Importância de Variáveis
    mcol1, mcol2 = st.columns([1, 1.2])

    with mcol1:
        st.markdown("<h4 style='font-size:0.95rem; font-weight:700;'>Matriz de Confusão (Teste Temporal)</h4>", unsafe_allow_html=True)
        if caminho_matriz.is_file():
            df_matriz = pd.read_csv(caminho_matriz, index_col=0)
            fig_matriz = px.imshow(
                df_matriz.values,
                x=df_matriz.columns.tolist(),
                y=df_matriz.index.tolist(),
                color_continuous_scale="Blues",
                text_auto=True,
                labels=dict(x="Classe Prevista", y="Classe Real", color="Registros"),
            )
            fig_matriz.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_matriz, use_container_width=True)

    with mcol2:
        st.markdown("<h4 style='font-size:0.95rem; font-weight:700;'>Importância de Variáveis (Feature Importance)</h4>", unsafe_allow_html=True)
        if caminho_imp.is_file():
            df_imp = pd.read_csv(caminho_imp).head(12)
            fig_imp = px.bar(
                df_imp.sort_values("importance", ascending=True),
                x="importance",
                y="feature",
                orientation="h",
                color="importance",
                color_continuous_scale="Viridis",
                labels={"importance": "Importância Relativa", "feature": "Feature"},
            )
            fig_imp.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig_imp, use_container_width=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 4. Detector de Anomalias Não Supervisionado (Isolation Forest)
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Detector de Anomalias (Isolation Forest)</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        O modelo não supervisionado <b>Isolation Forest</b> atua em paralelo como redundância analítica,
        isolando anomalias térmicas e mecânicas sem depender de rótulos prévios de falha.
        Permite identificar desgastes incipientes e desvios de processo antes mesmo da manifestação
        de uma falha funcional catalogada.
        """,
        unsafe_allow_html=True,
    )


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Modelos de IA')
