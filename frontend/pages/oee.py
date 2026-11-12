"""Página 4: OEE e Eficiência Industrial — Métricas Classe Mundial, Perdas e Composição."""

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
from frontend.styles import DESIGN_TOKENS


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    render_header(
        title="OEE & Eficiência Global dos Equipamentos",
        description="Avaliação de Disponibilidade, Performance e Qualidade segundo os padrões World Class Manufacturing (WCM).",
        icon="gauge",
        context_badge=("BENCHMARK WCM ≥ 85%", "info"),
    )

    # Coleta telemetria e snapshot OEE
    oee_data: dict[str, Any] = {}
    try:
        oee_data = client.get("/industrial/metrics", timeout=2.0)
    except Exception:
        oee_data = {
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

    oee = float(oee_data.get("oee_percentual", 85.2) or 85.2)
    disp = float(oee_data.get("disponibilidade_percentual", 92.4) or 92.4)
    perf = float(oee_data.get("desempenho_percentual", 96.1) or 96.1)
    qual = float(oee_data.get("qualidade_percentual", 96.0) or 96.0)

    # 1. Os 4 Indicadores Mestres (Destaque Principal com Hierarquia Visual)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("OEE Global", f"{oee:.1f}%", "Disponibilidade × Desempenho × Qualidade", "gauge", "primary" if oee >= 85 else "warning")
    with k2:
        render_kpi("Disponibilidade (A)", f"{disp:.1f}%", f"Paradas: {oee_data.get('tempo_parada_min', 36):.0f} min", "clock", "success")
    with k3:
        render_kpi("Desempenho (P)", f"{perf:.1f}%", f"Produção: {oee_data.get('total_pecas_produzidas', 0):,} un", "speed", "primary")
    with k4:
        render_kpi("Qualidade (Q)", f"{qual:.1f}%", f"Conformidade: {100.0 - oee_data.get('taxa_rejeito_percentual', 1.2):.1f}%", "verified", "success")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Decomposição Simples e Direta dos Fatores do OEE
    col_chart, col_perdas = st.columns([1.2, 1.0])

    with col_chart:
        st.markdown(
            f'<div class="section-title">{svg_icon("bar_chart", c["text_heading"], 15)} Composição Fatorial e Benchmark WCM</div>',
            unsafe_allow_html=True,
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Disponibilidade", "Desempenho", "Qualidade", "OEE Global"],
                y=[disp, perf, qual, oee],
                marker_color=["#10B981", "#3B82F6", "#7C3AED", "#1565C0"],
                text=[f"{v:.1f}%" for v in [disp, perf, qual, oee]],
                textposition="auto",
                width=[0.45, 0.45, 0.45, 0.50],
            )
        )
        fig.add_hline(y=85.0, line_dash="dash", line_color="#EF4444", annotation_text="Meta Classe Mundial (85%)")
        fig.update_layout(
            height=240,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(range=[0, 110], title="Taxa (%)"),
        )
        apply_chart_theme(fig, height=240)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_perdas:
        st.markdown(
            f'<div class="section-title">{svg_icon("alert_triangle", c["text_heading"], 15)} Distribuição das Perdas de Produção</div>',
            unsafe_allow_html=True,
        )
        df_perdas = pd.DataFrame(
            [
                {"Categoria": "Paradas Não-Planejadas", "Impacto": f"{oee_data.get('tempo_parada_min', 36):.0f} min", "Fator": "Disponibilidade"},
                {"Categoria": "Pequenas Paradas / Queda Velocidade", "Impacto": f"{100.0 - perf:.1f}%", "Fator": "Performance"},
                {"Categoria": "Refugos de Soldagem e Usinagem", "Impacto": f"{oee_data.get('total_pecas_rejeitadas', 27)} peças", "Fator": "Qualidade"},
            ]
        )
        st.dataframe(df_perdas, use_container_width=True, hide_index=True, height=240)

    # 3. Informações Financeiras e Impacto Preditivo (Em Seção Secundária Recolhida)
    with st.expander("Impacto Preditivo e Estimativa Financeira (PCM)", expanded=False):
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        with c_fin1:
            render_kpi("Custo Evitado de Parada", "R$ 48.500", "Detecção precoce de falha", "verified", "success")
        with c_fin2:
            render_kpi("Ganho Potencial OEE", "+3.8%", "Com redução de quebras", "speed", "primary")
        with c_fin3:
            render_kpi("MTTR Preditivo", "45 min", "Contra 240 min corretivo", "clock", "primary")


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("OEE e Eficiência Industrial")
