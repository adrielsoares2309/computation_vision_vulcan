"""Página 1: Dashboard Geral — Cockpit Executivo e Operacional Minimalista (Siemens/SAP Fiori)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import get_api_client
from frontend.styles import DESIGN_TOKENS, render_status_badge


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    render_header(
        title="Cockpit Executivo SCADA / MES",
        description="Visão consolidada da operação: OEE global, sinóptico de células e qualidade de soldagem.",
        icon="layout_dashboard",
        context_badge=("PLANTA SÃO PAULO", "info"),
    )

    # 1. Coleta de Telemetria e Indicadores da API
    status_fabrica: dict[str, Any] = {}
    metricas_fabrica: dict[str, Any] = {}
    try:
        status_fabrica = client.get("/industrial/status", timeout=2.0)
        metricas_fabrica = client.get("/industrial/metrics", timeout=2.0)
    except Exception:
        status_fabrica = {
            "status_fabrica": "PRODUCAO_ATIVA",
            "detalhes_celulas": {
                "CEL-201": {"id_celula": "CEL-201", "estado": "OPERACAO_NORMAL", "nivel_seguranca_clp": 0, "alimentacao_fuso_pct": 100},
                "CEL-202": {"id_celula": "CEL-202", "estado": "OPERACAO_NORMAL", "nivel_seguranca_clp": 0, "alimentacao_fuso_pct": 100},
                "CEL-203": {"id_celula": "CEL-203", "estado": "ALERTA_PREVENTIVO_AMARELO", "nivel_seguranca_clp": 1, "alimentacao_fuso_pct": 90},
                "CEL-204": {"id_celula": "CEL-204", "estado": "OPERACAO_NORMAL", "nivel_seguranca_clp": 0, "alimentacao_fuso_pct": 100},
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
        }

    oee_val = float(metricas_fabrica.get("oee_percentual", 85.0) or 85.0)
    disp_val = float(metricas_fabrica.get("disponibilidade_percentual", 92.0) or 92.0)
    perf_val = float(metricas_fabrica.get("desempenho_percentual", 96.0) or 96.0)
    qual_val = float(metricas_fabrica.get("qualidade_percentual", 96.0) or 96.0)

    # 2. Indicadores Principais (Sem cards decorativos ou repetição)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("OEE Global", f"{oee_val:.1f}%", "Meta Classe Mundial ≥ 85.0%", "gauge", "primary")
    with k2:
        render_kpi("Disponibilidade (A)", f"{disp_val:.1f}%", f"Tempo Ativo: {metricas_fabrica.get('tempo_operacao_min', 440):.0f} min", "clock", "success")
    with k3:
        render_kpi("Desempenho (P)", f"{perf_val:.1f}%", f"Produção: {metricas_fabrica.get('total_pecas_produzidas', 0):,} peças", "speed", "primary")
    with k4:
        render_kpi("Qualidade (Q)", f"{qual_val:.1f}%", f"Refugo: {metricas_fabrica.get('taxa_rejeito_percentual', 1.2):.2f}%", "verified", "success")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Sinóptico Industrial das 4 Células (CEL-201 a CEL-204) — Padrão SCADA Siemens
    st.markdown(
        f'<div class="section-title">{svg_icon("factory", c["text_heading"], 15)} Estado Operacional das Células Flexíveis</div>',
        unsafe_allow_html=True,
    )

    cel_cols = st.columns(4)
    celulas_info = status_fabrica.get("detalhes_celulas", {})

    for cid, col in zip(["CEL-201", "CEL-202", "CEL-203", "CEL-204"], cel_cols):
        c_data = celulas_info.get(cid, {})
        nivel = c_data.get("nivel_seguranca_clp", 0)

        if nivel >= 4:
            borda = "border-left: 5px solid #EF4444;"
            tag_status = '<span class="vt-badge vt-badge-danger">PARADA / E-STOP</span>'
            estado_label = "Parada de Segurança"
            dot_color = "#EF4444"
        elif nivel >= 2:
            borda = "border-left: 5px solid #F59E0B;"
            tag_status = '<span class="vt-badge vt-badge-warning">ATENÇÃO</span>'
            estado_label = "Inspeção Requerida"
            dot_color = "#F59E0B"
        elif nivel == 1:
            borda = "border-left: 5px solid #3B82F6;"
            tag_status = '<span class="vt-badge vt-badge-info">ATENÇÃO LEVE</span>'
            estado_label = "Ajuste de Avanço"
            dot_color = "#3B82F6"
        else:
            borda = "border-left: 5px solid #10B981;"
            tag_status = '<span class="vt-badge vt-badge-success">OPERACIONAL</span>'
            estado_label = "Operação Nominal"
            dot_color = "#10B981"

        feed = c_data.get("alimentacao_fuso_pct", 100)

        with col:
            st.markdown(
                f"""
                <div class="vt-card" style="{borda} padding: 12px 14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-size:1.0rem; font-weight:800; color:#102A43;">{cid}</span>
                        {tag_status}
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                        <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:{dot_color};"></span>
                        <span style="font-size:0.82rem; font-weight:600; color:#334E68;">{estado_label}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#64748B;">
                        Avanço CNC: <b>{feed}%</b> · CLP Nível <b>{nivel}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. Qualidade das Soldas e Alertas Recentes
    g_left, g_right = st.columns([1.1, 1.0])

    with g_left:
        st.markdown(
            f'<div class="section-title">{svg_icon("scan_eye", c["text_heading"], 15)} Qualidade das Soldas (Aprovação vs. Reprovação)</div>',
            unsafe_allow_html=True,
        )
        total_p = metricas_fabrica.get("total_pecas_produzidas", 1840)
        rejeitadas = metricas_fabrica.get("total_pecas_rejeitadas", 27)
        aprovadas = max(0, total_p - rejeitadas)
        taxa_aprov = (aprovadas / max(1, total_p)) * 100.0

        fig_qual = go.Figure()
        fig_qual.add_trace(
            go.Bar(
                x=["Aprovadas", "Reprovadas"],
                y=[aprovadas, rejeitadas],
                marker_color=["#10B981", "#EF4444"],
                text=[f"{aprovadas:,} ({taxa_aprov:.1f}%)", f"{rejeitadas:,} ({100.0 - taxa_aprov:.1f}%)"],
                textposition="auto",
                width=[0.45, 0.45],
            )
        )
        fig_qual.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="Quantidade"),
            xaxis=dict(tickfont=dict(size=12, color="#102A43")),
        )
        apply_chart_theme(fig_qual, height=220)
        st.plotly_chart(fig_qual, use_container_width=True, config={"displayModeBar": False})

    with g_right:
        st.markdown(
            f'<div class="section-title">{svg_icon("alert_triangle", c["text_heading"], 15)} Alertas Operacionais Recentes</div>',
            unsafe_allow_html=True,
        )
        try:
            from src.simulation.plc_controller import obter_historico_acoes_clp
            acoes = obter_historico_acoes_clp(limite=4)
        except Exception:
            acoes = []

        if acoes:
            df_alertas = pd.DataFrame(acoes)[["timestamp", "id_celula", "comando_clp"]]
            df_alertas["timestamp"] = pd.to_datetime(df_alertas["timestamp"]).dt.strftime("%H:%M:%S")
            df_alertas.columns = ["Hora", "Célula", "Ação do CLP"]
            st.dataframe(df_alertas, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("Nenhuma condição anormal ou intervenção de emergência ativa no momento.")


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Dashboard Geral")
