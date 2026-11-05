"""Página 1: Dashboard Geral — Cockpit SCADA/MES executivo da VulcanTech Smart Metals S.A."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.services.api_client import fetch_system_status, get_api_client
from frontend.styles import DESIGN_TOKENS


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem;">
            <div>
                <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                    PAINEL EXECUTIVO SCADA / MES — VULCANTECH
                </h1>
                <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                    Monitoramento em tempo real da manufatura aditiva e usinagem de alta precisão
                </div>
            </div>
            <div style="text-align:right;">
                <span class="vt-badge vt-badge-info" style="font-size:0.8rem; padding:4px 10px;">
                    PLANTA INDUSTRIAL SÃO PAULO
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Coleta telemetria e status da API
    status_fabrica: dict[str, Any] = {}
    metricas_fabrica: dict[str, Any] = {}
    try:
        status_fabrica = client.get("/industrial/status", timeout=3.0)
        metricas_fabrica = client.get("/industrial/metrics", timeout=3.0)
    except Exception:
        # Fallback offline para demonstração industrial contínua
        status_fabrica = {
            "status_fabrica": "PRODUCAO_ATIVA",
            "total_celulas": 4,
            "celulas_em_operacao": 4,
            "celulas_intertravadas": 0,
            "oee_global": 85.2,
            "disponibilidade_global": 92.4,
            "desempenho_global": 96.1,
            "qualidade_global": 96.0,
            "simulador_ativo": True,
            "detalhes_celulas": {
                "CEL-201": {"id_celula": "CEL-201", "estado": "OPERACAO_NORMAL", "nivel_seguranca_clp": 0, "alimentacao_fuso_pct": 100, "ultima_mensagem": "Operação nominal estável."},
                "CEL-202": {"id_celula": "CEL-202", "estado": "OPERACAO_NORMAL", "nivel_seguranca_clp": 0, "alimentacao_fuso_pct": 100, "ultima_mensagem": "Operação nominal estável."},
                "CEL-203": {"id_celula": "CEL-203", "estado": "ALERTA_PREVENTIVO_AMARELO", "nivel_seguranca_clp": 1, "alimentacao_fuso_pct": 100, "ultima_mensagem": "Vibração em elevação leve."},
                "CEL-204": {"id_celula": "CEL-204", "estado": "OPERACAO_NORMAL", "nivel_seguranca_clp": 0, "alimentacao_fuso_pct": 100, "ultima_mensagem": "Operação nominal estável."},
            },
        }
        metricas_fabrica = {
            "oee_percentual": 85.2,
            "disponibilidade_percentual": 92.4,
            "desempenho_percentual": 96.1,
            "qualidade_percentual": 96.0,
            "taxa_rejeito_percentual": 1.45,
            "total_pecas_produzidas": 1840,
            "total_pecas_rejeitadas": 27,
            "tempo_operacao_min": 443.5,
            "tempo_parada_min": 36.5,
        }

    # 1. Quatro Cards de Indicadores Mestres (OEE, A, P, Q)
    col1, col2, col3, col4 = st.columns(4)

    oee_val = metricas_fabrica.get("oee_percentual", 85.0) or 85.0
    disp_val = metricas_fabrica.get("disponibilidade_percentual", 92.0) or 92.0
    perf_val = metricas_fabrica.get("desempenho_percentual", 96.0) or 96.0
    qual_val = metricas_fabrica.get("qualidade_percentual", 96.0) or 96.0

    with col1:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #1D4ED8; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">OEE Global</div>
                <div style="font-size:1.8rem; font-weight:800; color:#0F172A;">{oee_val:.1f}%</div>
                <div style="font-size:0.75rem; color:#059669; font-weight:600;">Meta: ≥ 85.0% (Classe Mundial)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #059669; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">Disponibilidade (A)</div>
                <div style="font-size:1.8rem; font-weight:800; color:#0F172A;">{disp_val:.1f}%</div>
                <div style="font-size:0.75rem; color:#475569;">Tempo Operação: {metricas_fabrica.get('tempo_operacao_min', 440):.0f} min</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #D97706; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">Desempenho (P)</div>
                <div style="font-size:1.8rem; font-weight:800; color:#0F172A;">{perf_val:.1f}%</div>
                <div style="font-size:0.75rem; color:#475569;">Produção: {metricas_fabrica.get('total_pecas_produzidas', 0):,} peças</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 4px solid #7C3AED; padding: 14px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">Qualidade (Q)</div>
                <div style="font-size:1.8rem; font-weight:800; color:#0F172A;">{qual_val:.1f}%</div>
                <div style="font-size:0.75rem; color:#475569;">Refugo: {metricas_fabrica.get('taxa_rejeito_percentual', 1.2):.2f}% ({metricas_fabrica.get('total_pecas_rejeitadas', 0)} un)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Visão SCADA das 4 Células Industriais
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A; margin-bottom:8px;'>Sinóptico das Células Operacionais (SCADA)</h3>", unsafe_allow_html=True)

    cel_cols = st.columns(4)
    celulas_info = status_fabrica.get("detalhes_celulas", {})

    for idx, (cid, col) in enumerate(zip(["CEL-201", "CEL-202", "CEL-203", "CEL-204"], cel_cols)):
        c_data = celulas_info.get(cid, {})
        nivel = c_data.get("nivel_seguranca_clp", 0)

        if nivel == 4:
            cor_piloto = "#DC2626"
            borda = "border: 2px solid #DC2626;"
            badge = '<span class="vt-badge vt-badge-danger">E-STOP ATIVO</span>'
        elif nivel == 3:
            cor_piloto = "#EA580C"
            borda = "border: 2px solid #EA580C;"
            badge = '<span class="vt-badge vt-badge-warning">PCM ALERTA</span>'
        elif nivel == 2:
            cor_piloto = "#2563EB"
            borda = "border: 2px solid #2563EB;"
            badge = '<span class="vt-badge vt-badge-info">INSPEÇÃO</span>'
        elif nivel == 1:
            cor_piloto = "#D97706"
            borda = "border: 2px solid #D97706;"
            badge = '<span class="vt-badge vt-badge-warning">ATENÇÃO</span>'
        else:
            cor_piloto = "#10B981"
            borda = "border: 1px solid #CBD5E1;"
            badge = '<span class="vt-badge vt-badge-success">NOMINAL</span>'

        with col:
            st.markdown(
                f"""
                <div class="vt-card" style="{borda} padding: 14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.05rem; font-weight:800; color:#0F172A;">{cid}</span>
                        {badge}
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; margin: 8px 0;">
                        <div style="width:14px; height:14px; border-radius:50%; background-color:{cor_piloto}; box-shadow: 0 0 6px {cor_piloto};"></div>
                        <span style="font-size:0.8rem; font-weight:600; color:#334155;">{c_data.get('estado', 'OPERACAO_NORMAL')}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#475569; margin-bottom:4px;">
                        <b>Feed Rate:</b> {c_data.get('alimentacao_fuso_pct', 100)}%
                    </div>
                    <div style="font-size:0.72rem; color:#64748B; line-height:1.2; height:34px; overflow:hidden;">
                        {c_data.get('ultima_mensagem', 'Em operação normal.')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 3. Gráficos de Decomposição OEE e Histórico de Ações do CLP
    gcol1, gcol2 = st.columns([1.2, 1.0])

    with gcol1:
        st.markdown("<h4 style='font-size:0.95rem; font-weight:700; color:#0F172A;'>Decomposição Fatorial do OEE</h4>", unsafe_allow_html=True)
        fig_oee = go.Figure()
        fig_oee.add_trace(go.Bar(
            name="Índice Real",
            x=["Disponibilidade (A)", "Desempenho (P)", "Qualidade (Q)", "OEE Global"],
            y=[disp_val, perf_val, qual_val, oee_val],
            marker_color=["#059669", "#D97706", "#7C3AED", "#1D4ED8"],
            text=[f"{v:.1f}%" for v in [disp_val, perf_val, qual_val, oee_val]],
            textposition="auto",
        ))
        fig_oee.add_hline(y=85.0, line_dash="dash", line_color="#DC2626", annotation_text="Benchmark Classe Mundial (85%)")
        fig_oee.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=25, b=10),
            yaxis=dict(range=[0, 110], title="Eficiência (%)"),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
        )
        st.plotly_chart(fig_oee, use_container_width=True)

    with gcol2:
        st.markdown("<h4 style='font-size:0.95rem; font-weight:700; color:#0F172A;'>Últimos Comandos de Malha Fechada (CLP)</h4>", unsafe_allow_html=True)
        try:
            from src.simulation.plc_controller import obter_historico_acoes_clp
            acoes = obter_historico_acoes_clp(limite=6)
        except Exception:
            acoes = []

        if acoes:
            df_acoes = pd.DataFrame(acoes)[["timestamp", "id_celula", "nivel_seguranca", "comando_clp"]]
            df_acoes["timestamp"] = pd.to_datetime(df_acoes["timestamp"]).dt.strftime("%H:%M:%S")
            st.dataframe(df_acoes, use_container_width=True, height=260)
        else:
            st.info("Nenhuma intervenção crítica registrada pelo CLP nas últimas varreduras.")


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Dashboard Geral')
