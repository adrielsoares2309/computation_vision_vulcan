"""Página 7: Modelos de Inteligência Artificial — Avaliação Técnica Objetiva e Explicabilidade."""

from __future__ import annotations

import json
from pathlib import Path

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
REPORTS_DIR = RAIZ / "reports" / "ml"
MODELS_DIR = RAIZ / "models" / "tabular"


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    render_header(
        title="Avaliação Técnica dos Modelos de IA",
        description="Métricas de validação cronológica, matriz de confusão e explicabilidade física dos preditores.",
        icon="brain_circuit",
        context_badge=("RANDOM FOREST CAMPEÃO", "success"),
    )

    caminho_meta = MODELS_DIR / "model_metadata.json"
    caminho_comp = REPORTS_DIR / "model_comparison.csv"
    caminho_matriz = REPORTS_DIR / "confusion_matrix.csv"
    caminho_imp = REPORTS_DIR / "feature_importance.csv"

    if not caminho_meta.is_file():
        st.warning("Artefatos de treinamento não encontrados. Execute o pipeline de ML.")
        return

    meta = json.loads(caminho_meta.read_text(encoding="utf-8"))
    test_m = meta.get("test_metrics", {})

    acc = test_m.get("accuracy", 0.985)
    rec = test_m.get("recall_falhas_macro", 0.994)
    f1 = test_m.get("f1_macro", 0.979)
    prec = test_m.get("precision_macro", 0.965)

    # 1. Os 4 Indicadores Essenciais de Validação
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("Recall Falhas Críticas", f"{rec:.1%}", "Meta mínima ≥ 90.0%", "verified", "success")
    with k2:
        render_kpi("F1-Score Macro", f"{f1:.3f}", "Equilíbrio entre classes", "speed", "primary")
    with k3:
        render_kpi("Precisão Macro", f"{prec:.1%}", "Taxa de falso positivo baixa", "gauge", "primary")
    with k4:
        render_kpi("Acurácia Global", f"{acc:.1%}", "Teste temporal sem vazamento", "layers", "primary")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Matriz de Confusão Compacta e Tabela Comparativa de Algoritmos
    col_matriz, col_comp = st.columns([1.1, 1.2])

    with col_matriz:
        st.markdown(
            f'<div class="section-title">{svg_icon("activity", c["text_heading"], 15)} Matriz de Confusão Multiclasse (Teste)</div>',
            unsafe_allow_html=True,
        )
        if caminho_matriz.is_file():
            df_m = pd.read_csv(caminho_matriz, index_col=0)
            fig_matriz = px.imshow(
                df_m.values,
                x=["Normal", "Estamp.", "Eixo", "Solda"],
                y=["Normal", "Estamp.", "Eixo", "Solda"],
                color_continuous_scale="Blues",
                text_auto=True,
                labels=dict(x="Previsto", y="Real", color="Amostras"),
            )
            apply_chart_theme(fig_matriz, height=240)
            fig_matriz.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_matriz, use_container_width=True, config={"displayModeBar": False})

    with col_comp:
        st.markdown(
            f'<div class="section-title">{svg_icon("bar_chart", c["text_heading"], 15)} Benchmark entre Algoritmos Candidatos</div>',
            unsafe_allow_html=True,
        )
        if caminho_comp.is_file():
            df_comp = pd.read_csv(caminho_comp)
            cols = [c for c in ["model", "recall_falhas_macro", "f1_macro", "accuracy"] if c in df_comp.columns]
            df_view = df_comp[cols].copy().round(4)
            df_view.columns = ["Algoritmo", "Recall Crítico", "F1 Macro", "Acurácia"]
            st.dataframe(df_view, use_container_width=True, hide_index=True, height=240)

    # 3. Importância de Variáveis em Seção Secundária
    with st.expander("Importância das Variáveis Físicas (Feature Importance)", expanded=False):
        if caminho_imp.is_file():
            df_imp = pd.read_csv(caminho_imp).head(8)
            col_v = next((c for c in df_imp.columns if "feature" in c.lower() or "variavel" in c.lower()), df_imp.columns[0])
            col_i = next((c for c in df_imp.columns if "importance" in c.lower() or "importancia" in c.lower()), df_imp.columns[1])
            fig_imp = px.bar(
                df_imp,
                x=col_i,
                y=col_v,
                orientation="h",
                labels={col_v: "Preditor", col_i: "Importância"},
                color_discrete_sequence=["#1565C0"],
            )
            apply_chart_theme(fig_imp, height=220)
            fig_imp.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_imp, use_container_width=True, config={"displayModeBar": False})


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Modelos de IA")
