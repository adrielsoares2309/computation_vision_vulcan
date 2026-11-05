"""Módulo de Visão Computacional — Inspeção Geométrica (Canny/Porosidade) e Termográfica (HSV/HAZ)."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.components.charts import apply_chart_theme
from frontend.components.header import render_header
from frontend.components.kpi_card import render_kpi
from frontend.services.api_client import APIConnectionError, APIResponseError
from frontend.services.vision_service import (
    get_vision_history,
    get_vision_metadata,
    get_vision_summary,
    list_sample_images,
    load_sample_preview,
    validate_image,
)
from frontend.styles import DESIGN_TOKENS, render_status_badge
from src.vision.thermal_analysis import analisar_termografia_solda
from src.vision.weld_inspection import inspecionar_solda

RAIZ = Path(__file__).resolve().parents[2]
RAW_IMG_DIR = RAIZ / "data" / "raw" / "imagens"


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    st.markdown(
        """
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                VISÃO COMPUTACIONAL & INSPEÇÃO DE SOLDAS
            </h1>
            <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                Inspeção dimensional por Canny/contornos, estimativa de porosidade e análise termográfica da ZAC/HAZ em HSV
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    aba_geom, aba_term, aba_hist = st.tabs([
        "1. Inspeção Geométrica & Porosidade (OpenCV)",
        "2. Análise Termográfica ZAC/HAZ (HSV)",
        "3. Histórico & Classificador Espectral",
    ])

    # -------------------------------------------------------------
    # ABA 1: Inspeção Geométrica do Cordão de Solda (Canny + Contornos + Porosidade)
    # -------------------------------------------------------------
    with aba_geom:
        st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Inspeção Dimensional de Cordão de Solda</h3>", unsafe_allow_html=True)
        st.markdown(
            """
            Processamento em tempo real: conversão em escala de cinza, filtro unsharp mask de nitidez,
            detector de bordas de Canny, extração morfológica de contornos, medição de perfil de largura,
            detecção de descontinuidades geométricas e estimativa percentual de porosidade (ISO 5817).
            """
        )

        gcol_left, gcol_right = st.columns([1, 1.3])

        with gcol_left:
            origem_geom = st.radio("Selecione a Imagem Visual:", ["solda_aprovada.png", "solda_reprovada.png", "Upload Próprio"], horizontal=True)

            img_bytes = None
            caminho_teste = None

            if origem_geom == "Upload Próprio":
                arq_up = st.file_uploader("Enviar imagem de junta soldada", type=["png", "jpg", "jpeg", "tif"], key="up_geom")
                if arq_up is not None:
                    img_bytes = arq_up.read()
            else:
                caminho_teste = RAW_IMG_DIR / origem_geom
                if caminho_teste.is_file():
                    img_bytes = caminho_teste.read_bytes()

            limiar_poro = st.slider("Limiar de Rejeição por Porosidade (%)", 1.0, 5.0, 3.0, 0.5)

            if img_bytes is not None and st.button("Executar Inspeção Geométrica", type="primary", use_container_width=True):
                nparr = np.frombuffer(img_bytes, np.uint8)
                img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                with st.spinner("Processando filtros Canny e contornos..."):
                    res_geom = inspecionar_solda(
                        caminho_teste if caminho_teste else img_bgr,
                        limiar_porosidade_reprovacao=limiar_poro,
                    )
                st.session_state["res_geom"] = res_geom

        with gcol_right:
            res_geom = st.session_state.get("res_geom")
            if res_geom:
                status_inspecao = res_geom["status"]
                cor_status = {"APROVADO": "#10B981", "ALERTA": "#F59E0B", "REPROVADO": "#EF4444"}.get(status_inspecao, "#10B981")

                st.markdown(
                    f"""
                    <div class="vt-card" style="border-left: 6px solid {cor_status}; padding: 14px; margin-bottom: 12px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#475569;">PARECER DA INSPEÇÃO GEOMÉTRICA</div>
                        <div style="font-size:1.6rem; font-weight:800; color:{cor_status};">{status_inspecao}</div>
                        <div style="font-size:0.85rem; color:#334155; margin-top:4px;">
                            {' | '.join(res_geom.get('motivos', []))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Métricas em colunas
                m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                with m_c1:
                    st.metric("Porosidade", f"{res_geom['porosidade_percentual']:.2f}%")
                with m_c2:
                    st.metric("Poros Detectados", f"{res_geom['contagem_poros']}")
                with m_c3:
                    st.metric("Largura Média", f"{res_geom['largura_media_px']:.1f} px")
                with m_c4:
                    st.metric("Variação Largura", f"{res_geom['variacao_largura_percentual']:.1f}%")

                # Exibição da imagem anotada
                if "imagem_anotada_base64" in res_geom:
                    img_data = base64.b64decode(res_geom["imagem_anotada_base64"])
                    st.image(img_data, caption="Imagem Anotada com HUD Industrial e Contornos de Defeito", use_container_width=True)
            else:
                st.info("Selecione uma imagem à esquerda e clique em 'Executar Inspeção Geométrica'.")

    # -------------------------------------------------------------
    # ABA 2: Análise Termográfica ZAC / HAZ (HSV)
    # -------------------------------------------------------------
    with aba_term:
        st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Análise Termográfica e Zona Afetada pelo Calor (ZAC/HAZ)</h3>", unsafe_allow_html=True)
        st.markdown(
            """
            Avaliação termográfica via espaço de cor HSV: segmentação de hotspots na poça de fusão,
            isolamento da Zona Afetada pelo Calor (HAZ), cálculo de proporção ZAC/Fusão e estimativa
            de perfil térmico contra riscos de trincas a frio e superaquecimento crítico.
            """
        )

        tcol_left, tcol_right = st.columns([1, 1.3])

        with tcol_left:
            origem_term = st.radio("Selecione a Imagem Térmica:", ["termica_solda_aprovada.png", "termica_solda_reprovada.png", "Upload Próprio"], horizontal=True)

            term_bytes = None
            caminho_term_teste = None

            if origem_term == "Upload Próprio":
                arq_up_t = st.file_uploader("Enviar termografia falsa-cor", type=["png", "jpg", "jpeg", "tif"], key="up_term")
                if arq_up_t is not None:
                    term_bytes = arq_up_t.read()
            else:
                caminho_term_teste = RAW_IMG_DIR / origem_term
                if caminho_term_teste.is_file():
                    term_bytes = caminho_term_teste.read_bytes()

            if term_bytes is not None and st.button("Executar Análise Térmica", type="primary", use_container_width=True):
                nparr_t = np.frombuffer(term_bytes, np.uint8)
                img_t_bgr = cv2.imdecode(nparr_t, cv2.IMREAD_COLOR)
                with st.spinner("Processando espaço de cor HSV e isolinhas térmicas..."):
                    res_term = analisar_termografia_solda(caminho_term_teste if caminho_term_teste else img_t_bgr)
                st.session_state["res_term"] = res_term

        with tcol_right:
            res_term = st.session_state.get("res_term")
            if res_term:
                status_term = res_term["status"]
                cor_term = {"APROVADO": "#10B981", "ALERTA": "#F59E0B", "REPROVADO": "#EF4444"}.get(status_term, "#10B981")

                st.markdown(
                    f"""
                    <div class="vt-card" style="border-left: 6px solid {cor_term}; padding: 14px; margin-bottom: 12px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#475569;">DIAGNÓSTICO TERMOGRÁFICO ZAC/HAZ</div>
                        <div style="font-size:1.6rem; font-weight:800; color:{cor_term};">{status_term} — {res_term['diagnostico']}</div>
                        <div style="font-size:0.85rem; color:#334155; margin-top:4px;">
                            {' | '.join(res_term.get('motivos', []))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                tm1, tm2, tm3, tm4 = st.columns(4)
                with tm1:
                    st.metric("Pico Térmico Est.", f"~{res_term['temperatura_max_estimada_c']:.0f} °C")
                with tm2:
                    st.metric("Área ZAC/HAZ", f"{res_term['percentual_haz']:.1f}%")
                with tm3:
                    st.metric("Poça de Fusão", f"{res_term['percentual_hotspot']:.1f}%")
                with tm4:
                    st.metric("Razão ZAC/Fusão", f"{res_term['razao_haz_hotspot']:.2f}")

                if "imagem_anotada_base64" in res_term:
                    img_data_t = base64.b64decode(res_term["imagem_anotada_base64"])
                    st.image(img_data_t, caption="Heatmap com Isolinhas de Fusão e ZAC (HSV Segmentado)", use_container_width=True)
            else:
                st.info("Selecione uma imagem térmica à esquerda e clique em 'Executar Análise Térmica'.")

    # -------------------------------------------------------------
    # ABA 3: Histórico e Classificador Espectral (HOG/KNN)
    # -------------------------------------------------------------
    with aba_hist:
        st.markdown("<h3 style='font-size:1.1rem; font-weight:700; color:#0F172A;'>Histórico de Inspeções no Banco SQLite</h3>", unsafe_allow_html=True)
        try:
            history_resp = get_vision_history(limit=50)
            items = history_resp.get("items", [])
            if items:
                df_h = pd.DataFrame(items)
                st.dataframe(df_h, use_container_width=True)
            else:
                st.info("Nenhuma inspeção gravada no banco de dados ainda.")
        except Exception as exc:
            st.warning(f"Banco de dados ou histórico indisponível no momento: {exc}")


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Visão Computacional')
