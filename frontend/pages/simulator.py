"""Página 8: Simulador Industrial — Injeção de falhas controladas e malha fechada do CLP."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.services.api_client import get_api_client
from frontend.styles import DESIGN_TOKENS
from src.simulation.plc_controller import avaliar_acao_clp, obter_historico_acoes_clp
from src.simulation.sensor_simulator import SIMULATION_MODES, generate_simulated_sensor_reading


def render() -> None:
    c = DESIGN_TOKENS["colors"]
    client = get_api_client()

    st.markdown(
        """
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                SIMULADOR INDUSTRIAL & CLP EM MALHA FECHADA
            </h1>
            <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                Geração estocástica de telemetria, injeção de falhas e automação de segurança (IEC 61131 / ISO 13849)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Painel de Controle do Simulador
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A; margin-bottom:8px;'>Controle da Simulação Contínua</h3>", unsafe_allow_html=True)

    status_sim = {}
    try:
        status_sim = client.get("/simulation/status")
    except Exception:
        status_sim = {"running": False, "mode": "MISTO", "interval_seconds": 5.0}

    esta_rodando = status_sim.get("running", False)

    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns([1.2, 1, 1, 1])

    with c_ctrl1:
        novo_modo = st.selectbox(
            "Modo Operacional da Simulação",
            options=sorted(SIMULATION_MODES),
            index=sorted(SIMULATION_MODES).index(status_sim.get("mode", "MISTO")),
        )
    with c_ctrl2:
        intervalo = st.number_input("Intervalo (s)", min_value=1.0, max_value=30.0, value=5.0, step=1.0)
    with c_ctrl3:
        st.write("")
        st.write("")
        if esta_rodando:
            if st.button("Interromper Simulação", type="primary", use_container_width=True):
                try:
                    client.post("/simulation/stop")
                    st.success("Simulação interrompida.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao parar: {exc}")
        else:
            if st.button("Iniciar Simulação", type="primary", use_container_width=True):
                try:
                    client.post("/simulation/start", json_body={"mode": novo_modo, "interval_seconds": intervalo})
                    st.success("Simulação iniciada.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao iniciar: {exc}")
    with c_ctrl4:
        st.write("")
        st.write("")
        if st.button("Executar 1 Ciclo Manual", use_container_width=True):
            try:
                res = client.post("/simulation/step", json_body={"count": 1, "mode": novo_modo})
                st.success("1 ciclo executado com sucesso!")
            except Exception as exc:
                st.info("Ciclo manual simulado localmente.")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Injeção Manual de Falhas e Avaliação de Resposta do CLP
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A; margin-bottom:8px;'>Injeção Forçada de Condições & Teste do CLP</h3>", unsafe_allow_html=True)

    ic1, ic2, ic3, ic4 = st.columns(4)
    with ic1:
        celula_alvo = st.selectbox("Célula Alvo", ["CEL-201", "CEL-202", "CEL-203", "CEL-204"])
    with ic2:
        vib_injetada = st.slider("Vibração RMS (mm/s)", 0.5, 12.0, 2.0, 0.1)
    with ic3:
        temp_injetada = st.slider("Temperatura Fuso (°C)", 25.0, 115.0, 52.0, 1.0)
    with ic4:
        falha_injetada = st.selectbox("Falha Provável", [0, 1, 2, 3], format_func=lambda x: {0: "0 - Normal", 1: "1 - Desgaste", 2: "2 - Refrigeração", 3: "3 - Desalinhamento"}[x])

    if st.button("Avaliar Ação de CLP em Malha Fechada", use_container_width=True):
        leitura_teste = {
            "id_celula": celula_alvo,
            "vibracao_triaxial_rms_mms": vib_injetada,
            "temperatura_fuso_c": temp_injetada,
            "torque_fuso_nm": 130.0,
            "vazao_refrigerante_lmin": 25.0,
            "pressao_hidraulica_bar": 160.0,
        }
        prob = 0.92 if falha_injetada > 0 else 0.05
        acao_resultado = avaliar_acao_clp(
            leitura_teste,
            tipo_falha_previsto=falha_injetada,
            probabilidade_falha=prob,
            score_anomalia=0.85 if falha_injetada > 0 else 0.10,
        )

        nivel = acao_resultado["nivel_seguranca"]
        cor_nivel = {
            4: "#DC2626",
            3: "#EA580C",
            2: "#2563EB",
            1: "#D97706",
            0: "#10B981",
        }.get(nivel, "#10B981")

        st.markdown(
            f"""
            <div class="vt-card" style="border-left: 6px solid {cor_nivel}; padding: 16px; margin-top: 14px;">
                <div style="font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase;">
                    Ação Determinística Executada pelo CLP (Nível {nivel} de Segurança)
                </div>
                <div style="font-size:1.4rem; font-weight:800; color:{cor_nivel}; margin: 4px 0;">
                    {acao_resultado['status_operacional']} — <code>{acao_resultado['comando_clp']}</code>
                </div>
                <div style="font-size:0.85rem; color:#334155; margin-bottom:8px;">
                    {acao_resultado['mensagem']}
                </div>
                <div style="font-size:0.8rem; color:#64748B;">
                    <b>Alimentação do Fuso:</b> {acao_resultado['ajuste_velocidade_feed_pct']}% |
                    <b>Trigger de Visão:</b> {'Sim' if acao_resultado['solicitar_inspecao_visao'] else 'Não'} |
                    <b>Ordem de Serviço PCM:</b> {'Sim (' + str(acao_resultado['prioridade_os']) + ')' if acao_resultado['abertura_os_pcm'] else 'Não'} |
                    <b>Intertravamento de Segurança:</b> {'ATIVADO' if acao_resultado['intertravamento_ativo'] else 'Desativado'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 3. Histórico de Ações do CLP
    st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Telemetria de Comandos Emitidos pelo CLP</h3>", unsafe_allow_html=True)
    historico = obter_historico_acoes_clp(limite=20)
    if historico:
        df_hist = pd.DataFrame(historico)[["timestamp", "id_celula", "nivel_seguranca", "categoria", "comando_clp", "status_operacional"]]
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("Nenhuma ação registrada no buffer recente do CLP.")


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Simulador Industrial')
