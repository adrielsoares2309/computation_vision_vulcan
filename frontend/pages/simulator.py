"""Página 8: Simulador Industrial — Injeção de Falhas e Intertravamento Determinístico do CLP."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import get_api_client
from frontend.styles import DESIGN_TOKENS
from src.simulation.plc_controller import avaliar_acao_clp, obter_historico_acoes_clp
from src.simulation.sensor_simulator import SIMULATION_MODES


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    render_header(
        title="Simulador de Processo & CLP em Malha Fechada",
        description="Controle operacional de simulação estocástica e verificação de regras de intertravamento de segurança.",
        icon="sliders_horizontal",
        context_badge=("IEC 61131-3 / ISO 13849", "info"),
    )

    # 1. Controle Compacto da Simulação Contínua
    st.markdown(
        f'<div class="section-title">{svg_icon("activity", c["text_heading"], 15)} Parâmetros da Simulação Contínua</div>',
        unsafe_allow_html=True,
    )

    status_sim = {}
    try:
        status_sim = client.get("/simulation/status", timeout=2.0)
    except Exception:
        status_sim = {"running": False, "mode": "MISTO", "interval_seconds": 5.0}

    esta_rodando = status_sim.get("running", False)

    c1, c2, c3 = st.columns([1.5, 1.0, 1.2], vertical_alignment="center")
    with c1:
        modo = st.selectbox(
            "Regime de Operação da Planta",
            options=sorted(SIMULATION_MODES),
            index=sorted(SIMULATION_MODES).index(status_sim.get("mode", "MISTO")),
            key="sim_page_mode_select",
        )
    with c2:
        intervalo = st.number_input("Ciclo (s)", min_value=1.0, max_value=30.0, value=5.0, step=1.0, key="sim_interval")
    with c3:
        if esta_rodando:
            if st.button("Parar Simulação", type="secondary", use_container_width=True, key="sim_btn_stop"):
                try:
                    client.post("/simulation/stop")
                    st.rerun()
                except Exception:
                    pass
        else:
            if st.button("Iniciar Simulação", type="primary", use_container_width=True, key="sim_btn_start"):
                try:
                    client.post("/simulation/start", json_body={"mode": modo, "interval_seconds": intervalo})
                    st.rerun()
                except Exception:
                    pass

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Injeção de Falha Controlada & Teste do Intertravamento CLP
    st.markdown(
        f'<div class="section-title">{svg_icon("wrench", c["text_heading"], 15)} Injeção de Falha & Teste de Intertravamento (CLP)</div>',
        unsafe_allow_html=True,
    )

    ic1, ic2, ic3, ic4 = st.columns(4)
    with ic1:
        celula_alvo = st.selectbox("Célula Alvo", ["CEL-201", "CEL-202", "CEL-203", "CEL-204"], key="sim_target_cell")
    with ic2:
        vib_injetada = st.slider("Vibração RMS (mm/s)", 0.5, 12.0, 2.2, 0.1, key="sim_vib_slider")
    with ic3:
        temp_injetada = st.slider("Temp. Fuso (°C)", 25.0, 115.0, 52.0, 1.0, key="sim_temp_slider")
    with ic4:
        falha_injetada = st.selectbox(
            "Cenário de Falha",
            [0, 1, 2, 3],
            format_func=lambda x: {0: "0 - Normal", 1: "1 - Hidráulica Estamp.", 2: "2 - Eixo CNC", 3: "3 - Solda MIG"}[x],
            key="sim_fault_scenario",
        )

    avaliar_btn = st.button("Avaliar Resposta do CLP", type="primary", use_container_width=True, key="sim_btn_eval")

    if avaliar_btn:
        leitura_teste = {
            "id_celula": celula_alvo,
            "vibracao_triaxial_rms_mms": vib_injetada,
            "temperatura_fuso_c": temp_injetada,
            "torque_fuso_nm": 130.0,
            "vazao_refrigerante_lmin": 25.0,
            "pressao_hidraulica_bar": 160.0,
        }
        prob = 0.92 if falha_injetada > 0 else 0.05
        acao = avaliar_acao_clp(
            leitura_teste,
            tipo_falha_previsto=falha_injetada,
            probabilidade_falha=prob,
            score_anomalia=0.85 if falha_injetada > 0 else 0.10,
        )

        nivel = acao["nivel_seguranca"]
        cor_nivel = {
            4: "#EF4444",
            3: "#F59E0B",
            2: "#3B82F6",
            1: "#D97706",
            0: "#10B981",
        }.get(nivel, "#10B981")

        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 6px solid {cor_nivel}; padding: 14px 18px; margin-top: 10px;">
                <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">
                    Resposta do CLP de Segurança · Nível {nivel}
                </div>
                <div style="font-size:1.3rem; font-weight:800; color:{cor_nivel}; margin: 2px 0;">
                    {acao['comando_clp']} — {acao['status_operacional']}
                </div>
                <div style="font-size:0.80rem; color:#334E68; margin-bottom:8px;">
                    {acao['mensagem']}
                </div>
                <div style="font-size:0.75rem; color:#64748B;">
                    Avanço Spindle: <b>{acao['ajuste_velocidade_feed_pct']}%</b> · Inspeção Visual: <b>{'Sim' if acao['solicitar_inspecao_visao'] else 'Não'}</b> · OS PCM: <b>{'Sim' if acao['abertura_os_pcm'] else 'Não'}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Simulador Industrial")
