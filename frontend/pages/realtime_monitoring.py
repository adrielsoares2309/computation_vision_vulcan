"""Página 2: Monitoramento em Tempo Real — Sensores industriais, IEM e telemetria por célula."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontend.services.api_client import get_api_client
from frontend.styles import DESIGN_TOKENS
from src.data.feature_engineering import calcular_iem
from src.simulation.sensor_simulator import generate_simulated_sensor_reading


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    st.markdown(
        """
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                MONITORAMENTO DE SENSORES EM TEMPO REAL
            </h1>
            <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                Telemetria multivariada, Índice de Esforço Mecânico (IEM) e controle estatístico por liga
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Controles de Filtro
    fcol1, fcol2, fcol3 = st.columns([1, 1, 1])
    with fcol1:
        celula_selecionada = st.selectbox(
            "Célula Operacional",
            options=["CEL-201", "CEL-202", "CEL-203", "CEL-204"],
            index=0,
        )
    with fcol2:
        liga_selecionada = st.selectbox(
            "Liga Metálica em Processo",
            options=["Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V"],
            index=0,
        )
    with fcol3:
        st.write("")
        st.write("")
        btn_amostrar = st.button("Capturar Leitura de Sensores", use_container_width=True)

    # Obter leitura atual (API ou simulador em tempo real)
    leitura: dict[str, Any] = {}
    try:
        leitura = client.get(f"/sensors/latest?equipment_id={celula_selecionada}")
    except Exception:
        leitura = generate_simulated_sensor_reading(
            mode="NORMAL",
            equipment_id=celula_selecionada,
            alloy=liga_selecionada,
        )

    # Cálculos derivados
    temp = float(leitura.get("temperatura_fuso_c", 52.0))
    vib = float(leitura.get("vibracao_triaxial_rms_mms", 1.8))
    torque = float(leitura.get("torque_fuso_nm", 110.0))
    vazao = float(leitura.get("vazao_refrigerante_lmin", 28.0))
    corrente = float(leitura.get("corrente_estator_amp", 28.0))
    pressao = float(leitura.get("pressao_hidraulica_bar", 160.0))
    ruido = float(leitura.get("nivel_ruido_db", 55.0))

    iem = (torque * vib) / (vazao + 1.0)

    # Indicador de severidade IEM
    if iem >= 50.0:
        cor_iem = "#DC2626"
        status_iem = "CRÍTICO (Risco Iminente)"
    elif iem >= 25.0:
        cor_iem = "#D97706"
        status_iem = "ALERTA (Esforço Elevado)"
    else:
        cor_iem = "#059669"
        status_iem = "NOMINAL (Normal)"

    # Bloco de destaque do IEM
    st.markdown(
        f"""
        <div class="vt-card" style="background:#FFFFFF; border-left: 6px solid {cor_iem}; padding: 18px; margin-bottom: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; letter-spacing:0.05em;">
                        Índice de Esforço Mecânico (IEM) — Feature Engineering Industrial
                    </span>
                    <div style="font-size:2.4rem; font-weight:900; color:{cor_iem}; line-height:1.1;">
                        {iem:.2f} <span style="font-size:1.0rem; font-weight:600; color:#64748B;">pontos</span>
                    </div>
                    <div style="font-size:0.85rem; color:#334155; margin-top:4px;">
                        Fórmula: <code>(Torque × Vibração) / (Vazão + 1)</code> | Status: <b>{status_iem}</b>
                    </div>
                </div>
                <div style="text-align:right;">
                    <span class="vt-badge" style="background:{cor_iem}20; color:{cor_iem}; font-size:0.85rem; padding:6px 14px; font-weight:700;">
                        {status_iem}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Painel dos 7 Sensores Principais
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A; margin-bottom:12px;'>Grandezas Físicas Monitoradas</h3>", unsafe_allow_html=True)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc5, sc6, sc7, sc8 = st.columns(4)

    with sc1:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">TEMP. FUSO</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{temp:.1f} °C</div>
                <div style="font-size:0.75rem; color:{'#DC2626' if temp > 80 else '#059669'};">Nominal: &lt; 75.0 °C</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc2:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">VIBRAÇÃO RMS</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{vib:.2f} mm/s</div>
                <div style="font-size:0.75rem; color:{'#DC2626' if vib > 4.5 else '#059669'};">ISO 10816: &lt; 4.5 mm/s</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc3:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">TORQUE DO FUSO</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{torque:.1f} Nm</div>
                <div style="font-size:0.75rem; color:#64748B;">Limite Máx: 220.0 Nm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc4:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">VAZÃO REFRIGERANTE</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{vazao:.1f} L/min</div>
                <div style="font-size:0.75rem; color:{'#DC2626' if vazao < 12 else '#059669'};">Mínimo: &gt; 15.0 L/min</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc5:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">CORRENTE ESTATOR</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{corrente:.1f} A</div>
                <div style="font-size:0.75rem; color:#64748B;">Potência Spindle</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc6:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">PRESSÃO HIDRÁULICA</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{pressao:.1f} bar</div>
                <div style="font-size:0.75rem; color:{'#DC2626' if pressao < 130 else '#059669'};">Faixa: 140 - 180 bar</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc7:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">NÍVEL DE RUÍDO</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">{ruido:.1f} dB</div>
                <div style="font-size:0.75rem; color:#64748B;">Acústica de Usinagem</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with sc8:
        st.markdown(
            f"""
            <div class="vt-card" style="padding:14px; border:1px solid #CBD5E1;">
                <div style="font-size:0.75rem; color:#64748B; font-weight:700;">TAXA AMOSTRAGEM</div>
                <div style="font-size:1.6rem; font-weight:800; color:#0F172A;">5 min</div>
                <div style="font-size:0.75rem; color:#059669;">288 leituras / 24h</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Gráficos de Série Temporal Simulado / Recente
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Tendência Temporal Recente (Últimas Leituras)</h3>", unsafe_allow_html=True)

    # Gera buffer de 30 pontos para visualização
    np.random.seed(42)
    pontos = 30
    tempo_idx = pd.date_range(end=datetime.now(timezone.utc), periods=pontos, freq="5min")
    df_tendencia = pd.DataFrame({
        "Timestamp": tempo_idx,
        "Vibração (mm/s)": np.clip(np.random.normal(vib, 0.4, pontos), 0.5, 12.0),
        "Temperatura (°C)": np.clip(np.random.normal(temp, 2.5, pontos), 25.0, 110.0),
        "IEM": np.clip(np.random.normal(iem, 3.0, pontos), 2.0, 150.0),
    })

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=df_tendencia["Timestamp"],
        y=df_tendencia["Vibração (mm/s)"],
        name="Vibração RMS (mm/s)",
        line=dict(color="#1D4ED8", width=2),
    ))
    fig_trend.add_trace(go.Scatter(
        x=df_tendencia["Timestamp"],
        y=df_tendencia["Temperatura (°C)"],
        name="Temperatura (°C)",
        line=dict(color="#DC2626", width=2),
        yaxis="y2",
    ))
    fig_trend.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Vibração (mm/s)"),
        yaxis2=dict(title="Temperatura (°C)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1, x=0),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig_trend, use_container_width=True)


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Monitoramento em Tempo Real')
