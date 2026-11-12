"""Página 2: Monitoramento em Tempo Real — Sensores Industriais, IEM e Telemetria Operacional."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import get_api_client
from frontend.styles import DESIGN_TOKENS
from src.simulation.sensor_simulator import generate_simulated_sensor_reading


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    render_header(
        title="Monitoramento em Tempo Real",
        description="Telemetria de variáveis de processo, grandezas de usinagem e Índice de Esforço Mecânico (IEM).",
        icon="activity",
        context_badge=("TELEMETRIA ATIVA", "success"),
    )

    # 1. Barra Compacta de Filtros de Processo
    fc1, fc2, fc3 = st.columns([1.2, 1.2, 1.0], vertical_alignment="center")
    with fc1:
        celula = st.selectbox(
            "Célula Operacional",
            options=["CEL-201", "CEL-202", "CEL-203", "CEL-204"],
            index=0,
            key="rt_cell_select",
        )
    with fc2:
        liga = st.selectbox(
            "Liga em Usinagem",
            options=["Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V"],
            index=0,
            key="rt_alloy_select",
        )
    with fc3:
        capturar = st.button("Capturar Leitura", type="primary", use_container_width=True, key="rt_btn_capture")

    # 2. Obtenção de Leitura Real ou Simulação com Inércia
    leitura: dict[str, Any] = {}
    try:
        leitura = client.get(f"/sensors/latest?equipment_id={celula}", timeout=2.0)
    except Exception:
        leitura = generate_simulated_sensor_reading(
            mode="NORMAL",
            equipment_id=celula,
            alloy=liga,
        )

    temp = float(leitura.get("temperatura_fuso_c", 52.0))
    vib = float(leitura.get("vibracao_triaxial_rms_mms", 1.8))
    torque = float(leitura.get("torque_fuso_nm", 110.0))
    vazao = float(leitura.get("vazao_refrigerante_lmin", 28.0))
    pressao = float(leitura.get("pressao_hidraulica_bar", 160.0))

    iem = (torque * vib) / (vazao + 1.0)

    # 3. Bloco de Destaque IEM (Minimalismo Funcional)
    if iem >= 50.0:
        iem_tone = "danger"
        iem_status = "CRÍTICO (Sobrecarga Severa)"
        border_c = "#EF4444"
    elif iem >= 25.0:
        iem_tone = "warning"
        iem_status = "ALERTA (Esforço Elevado)"
        border_c = "#F59E0B"
    else:
        iem_tone = "success"
        iem_status = "NOMINAL (Operação Estável)"
        border_c = "#10B981"

    st.markdown(
        f"""
        <div class="vt-card" style="border-left: 6px solid {border_c}; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">
                        Índice de Esforço Mecânico (IEM) · Célula {celula}
                    </div>
                    <div style="font-size:2.0rem; font-weight:900; color:{border_c}; line-height:1.2;">
                        {iem:.2f} <span style="font-size:0.85rem; font-weight:600; color:#64748B;">pts</span>
                    </div>
                    <div style="font-size:0.78rem; color:#334E68;">
                        Fórmula: <code>(Torque × Vibração) / (Vazão + 1)</code> · Estado: <b>{iem_status}</b>
                    </div>
                </div>
                <div style="text-align:right;">
                    <span class="vt-badge vt-badge-{'success' if iem_tone=='success' else ('warning' if iem_tone=='warning' else 'danger')}">
                        {iem_status}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4. Indicadores de Grandezas Críticas (Siemens SCADA)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("Temperatura do Fuso", f"{temp:.1f} °C", "Limite: < 75.0 °C", "activity", "danger" if temp >= 75 else "primary")
    with k2:
        render_kpi("Vibração RMS", f"{vib:.2f} mm/s", "ISO 10816: < 4.5 mm/s", "sensors", "danger" if vib >= 4.5 else "primary")
    with k3:
        render_kpi("Torque Mecânico", f"{torque:.1f} Nm", "Nominal: 90 - 150 Nm", "gauge", "primary")
    with k4:
        render_kpi("Vazão Refrigerante", f"{vazao:.1f} L/min", "Mínimo Seguro: > 15 L/min", "speed", "danger" if vazao < 15 else "success")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 5. Série Temporal Unificada (Somente o que responde a perguntas operacionais)
    st.markdown(
        f'<div class="section-title">{svg_icon("activity", c["text_heading"], 15)} Evolução Temporal Recente (Últimos 30 Ciclos)</div>',
        unsafe_allow_html=True,
    )

    # Histórico sintético determinístico com base na leitura atual
    passos = 30
    tempo_idx = pd.date_range(end=pd.Timestamp.now(), periods=passos, freq="10s")
    np.random.seed(int(temp + torque) % 1000)
    arr_iem = np.clip(iem + np.cumsum(np.random.normal(0, 0.4, passos)), 5.0, 95.0)
    arr_vib = np.clip(vib + np.cumsum(np.random.normal(0, 0.05, passos)), 0.5, 6.0)

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(x=tempo_idx, y=arr_iem, mode="lines", name="IEM (Pontos)", line=dict(color="#1565C0", width=2.2)))
    fig_hist.add_trace(go.Scatter(x=tempo_idx, y=arr_vib * 10.0, mode="lines", name="Vibração × 10 (mm/s)", line=dict(color="#D97706", width=1.8, dash="dot")))
    fig_hist.add_hline(y=50.0, line_dash="dash", line_color="#EF4444", annotation_text="Limiar Crítico IEM (50 pts)")
    apply_chart_theme(fig_hist, height=240)
    fig_hist.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Horário"),
        yaxis=dict(title="Índice"),
    )
    st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Monitoramento em Tempo Real")
