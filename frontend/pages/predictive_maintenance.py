"""Página 3: Manutenção Preditiva — Classificação Multiclasse, Detecção de Anomalias e Fila de Equipamentos."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import APIConnectionError, APIResponseError, get_api_client
from frontend.styles import DESIGN_TOKENS, render_status_badge


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    render_header(
        title="Manutenção Preditiva & Diagnóstico de Falhas",
        description="Classificação supervisionada (XGBoost/Random Forest), detecção não-supervisionada de anomalias (Isolation Forest) e risco de parada.",
        icon="wrench",
        context_badge=("RECALL CRÍTICO 99.4%", "success"),
    )

    # 1. Carregamento de Dados com Fallback Resiliente
    overview_data: dict[str, Any] = {}
    try:
        overview_data = client.get("/industrial/status", timeout=2.0)
    except Exception:
        pass

    # 2. Visão Executiva de Risco das Células Industriais
    st.markdown(
        f'<div class="section-title">{svg_icon("activity", c["text_heading"], 15)} Diagnóstico de Condição por Equipamento</div>',
        unsafe_allow_html=True,
    )

    equipamentos = [
        {"id": "CEL-201", "falha_prevista": "Operação Normal", "prob": 0.98, "risco": "Baixo", "anomalia": "Não", "recomendacao": "Manter plano preventivo quinzenal."},
        {"id": "CEL-202", "falha_prevista": "Operação Normal", "prob": 0.95, "risco": "Baixo", "anomalia": "Não", "recomendacao": "Operação estável."},
        {"id": "CEL-203", "falha_prevista": "Desgaste Eixo-Árvore CNC", "prob": 0.78, "risco": "Moderado", "anomalia": "Sim (Score 0.62)", "recomendacao": "Inspecionar folga radial e lubrificação do mancal."},
        {"id": "CEL-204", "falha_prevista": "Operação Normal", "prob": 0.96, "risco": "Baixo", "anomalia": "Não", "recomendacao": "Operação nominal."},
    ]

    eq_cols = st.columns(4)
    for eq, col in zip(equipamentos, eq_cols):
        r_color = "#10B981" if eq["risco"] == "Baixo" else ("#F59E0B" if eq["risco"] == "Moderado" else "#EF4444")
        with col:
            st.markdown(
                f"""
                <div class="vt-card" style="border-left: 5px solid {r_color}; padding: 12px 14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.0rem; font-weight:800; color:#102A43;">{eq['id']}</span>
                        <span class="vt-badge vt-badge-{'success' if eq['risco']=='Baixo' else 'warning'}">{eq['risco']}</span>
                    </div>
                    <div style="font-size:0.82rem; font-weight:700; color:{r_color}; margin: 6px 0 2px 0;">
                        {eq['falha_prevista']}
                    </div>
                    <div style="font-size:0.75rem; color:#64748B;">
                        Confiança: <b>{eq['prob']:.0%}</b> · Anomalia: <b>{eq['anomalia']}</b>
                    </div>
                    <div style="font-size:0.73rem; color:#334E68; margin-top:6px; border-top:1px solid #E2E8F0; padding-top:4px;">
                        {eq['recomendacao']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Distribuição de Probabilidades e Fila de Ações de Manutenção
    c_left, c_right = st.columns([1.1, 1.0])

    with c_left:
        st.markdown(
            f'<div class="section-title">{svg_icon("brain_circuit", c["text_heading"], 15)} Probabilidades Multiclasse (Célula Crítica: CEL-203)</div>',
            unsafe_allow_html=True,
        )
        classes_falha = [
            "Normal (Classe 0)",
            "Falha Hidráulica (Classe 1)",
            "Desgaste Eixo CNC (Classe 2)",
            "Instabilidade Solda (Classe 3)",
        ]
        probs = [0.18, 0.04, 0.74, 0.04]

        fig_prob = go.Figure()
        fig_prob.add_trace(
            go.Bar(
                x=probs,
                y=classes_falha,
                orientation="h",
                marker_color=["#10B981", "#3B82F6", "#F59E0B", "#EF4444"],
                text=[f"{p:.1%}" for p in probs],
                textposition="auto",
            )
        )
        fig_prob.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(range=[0, 1.0], tickformat=".0%"),
            yaxis=dict(autorange="reversed"),
        )
        apply_chart_theme(fig_prob, height=200)
        st.plotly_chart(fig_prob, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        st.markdown(
            f'<div class="section-title">{svg_icon("file_check", c["text_heading"], 15)} Recomendações Prioritárias para o PCM</div>',
            unsafe_allow_html=True,
        )
        df_pcm = pd.DataFrame(
            [
                {"Célula": "CEL-203", "Modo de Falha": "Desgaste Spindle", "Ação Recomendada": "Inspeção e relubrificação de rolamentos", "Prioridade": "Alta"},
                {"Célula": "CEL-201", "Modo de Falha": "Preventiva Estampagem", "Ação Recomendada": "Checagem de vedações hidráulicas", "Prioridade": "Normal"},
                {"Célula": "CEL-204", "Modo de Falha": "Tocha MIG/MAG", "Ação Recomendada": "Troca de bico de contato e difusor", "Prioridade": "Normal"},
            ]
        )
        st.dataframe(df_pcm, use_container_width=True, hide_index=True, height=200)


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Manutenção Preditiva")
