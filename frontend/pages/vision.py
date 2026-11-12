"""Página 5: Visão Computacional — Estação Industrial de Inspeção de Cordão de Solda (Siemens/Cognex SCADA)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.services.vision_service import get_vision_history
from frontend.styles import DESIGN_TOKENS
from src.vision.thermal_analysis import analisar_termografia_solda
from src.vision.weld_inspection import carregar_imagem, inspecionar_solda
from vision.geometry import classify_geometry_against_references

RAIZ = Path(__file__).resolve().parents[2]
RAW_IMG_DIR = RAIZ / "data" / "raw" / "imagens"


def _bgr_to_rgb(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    render_header(
        title="Estação de Inspeção Óptica & Termográfica de Soldas",
        description="Sistema de visão computacional em linha: medição geométrica, porosidade ISO 5817 e termografia HSV.",
        icon="scan_eye",
        context_badge=("ISO 5817 NÍVEL B", "info"),
    )

    tab_inspecao, tab_gabarito, tab_historico = st.tabs(
        [
            "Estação de Inspeção em Linha",
            "Comparação com Gabarito (IoU)",
            "Histórico de Qualidade",
        ]
    )

    # Carrega referências
    ref_ok_path = RAW_IMG_DIR / "solda_aprovada.png"
    ref_bad_path = RAW_IMG_DIR / "solda_reprovada.png"
    ref_ok = carregar_imagem(ref_ok_path) if ref_ok_path.is_file() else None
    ref_bad = carregar_imagem(ref_bad_path) if ref_bad_path.is_file() else None

    # =========================================================================
    # ABA 1: Estação de Inspeção Principal (Áreas A, B e C)
    # =========================================================================
    with tab_inspecao:
        # 1. Barra de Ação Operacional Superior (Seleção rápida)
        top_c1, top_c2, top_c3 = st.columns([1.5, 2.0, 1.2], vertical_alignment="center")
        with top_c1:
            origem = st.selectbox(
                "Amostra de Solda para Inspeção",
                options=["solda_aprovada.png", "solda_reprovada.png", "termica_solda_aprovada.png", "termica_solda_reprovada.png", "Upload de Imagem"],
                index=0,
                key="vis_main_sample_select",
                label_visibility="collapsed",
            )
        with top_c2:
            limiar_poro = st.slider(
                "Tolerância Máxima de Porosidade (%)",
                min_value=1.0,
                max_value=5.0,
                value=3.0,
                step=0.5,
                key="vis_main_poro_thresh",
            )
        with top_c3:
            executar = st.button("Executar Inspeção", type="primary", use_container_width=True, key="vis_btn_inspect")

        # Obtenção da imagem
        img_bgr: np.ndarray | None = None
        nome_arquivo = origem

        if origem == "Upload de Imagem":
            up_file = st.file_uploader("Enviar imagem", type=["png", "jpg", "jpeg", "tif"], key="vis_file_up")
            if up_file:
                nparr = np.frombuffer(up_file.getvalue(), np.uint8)
                img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                nome_arquivo = up_file.name
        else:
            file_path = RAW_IMG_DIR / origem
            if file_path.is_file():
                img_bgr = carregar_imagem(file_path)

        if img_bgr is None:
            st.info("Selecione uma imagem de amostra para iniciar a inspeção visual.")
            return

        is_thermal = "termica" in nome_arquivo.lower()

        # Execução ou recuperação de cache
        sig = (nome_arquivo, float(limiar_poro), is_thermal)
        if executar or st.session_state.get("vis_cache_sig") != sig or "vis_result" not in st.session_state:
            with st.spinner("Processando filtros ópticos e geométricos..."):
                if is_thermal:
                    res = analisar_termografia_solda(img_bgr)
                else:
                    res = inspecionar_solda(
                        img_bgr,
                        limiar_porosidade_reprovacao=float(limiar_poro),
                        incluir_artefatos_filtros=True,
                    )
            st.session_state["vis_result"] = res
            st.session_state["vis_cache_sig"] = sig

        res = st.session_state.get("vis_result", {})
        status = res.get("status", "INCONCLUSIVA")

        # Layout Industrial: Área A (Imagem Dominante 62%) e Área B + C (Parecer, Indicadores e Defeitos 38%)
        col_img, col_info = st.columns([1.6, 1.0], gap="medium")

        # --- ÁREA A: IMAGEM DA INSPEÇÃO (DOMINANTE) ---
        with col_img:
            # Alternador de Camadas de Visualização
            if is_thermal:
                camada = st.radio(
                    "Camada de Exibição",
                    options=["Resultado Anotado (HUD)", "Termograma Original (Falsa-cor)"],
                    horizontal=True,
                    key="vis_layer_thermal",
                )
                if camada == "Resultado Anotado (HUD)" and "imagem_anotada_base64" in res:
                    st.image(base64.b64decode(res["imagem_anotada_base64"]), use_container_width=True)
                else:
                    st.image(_bgr_to_rgb(img_bgr), use_container_width=True)
            else:
                art = res.get("artefatos", {})
                camadas_disp = ["Inspeção Anotada (HUD)", "Original", "Bordas Canny", "Contornos", "Máscara de Poros", "Coerência (Tensor)"]
                camada = st.radio(
                    "Camada de Exibição",
                    options=camadas_disp,
                    horizontal=True,
                    key="vis_layer_optics",
                )
                if camada == "Inspeção Anotada (HUD)" and "imagem_anotada_base64" in res:
                    st.image(base64.b64decode(res["imagem_anotada_base64"]), use_container_width=True)
                elif camada == "Original":
                    st.image(_bgr_to_rgb(img_bgr), use_container_width=True)
                elif camada == "Bordas Canny" and "bordas_canny" in art:
                    st.image(art["bordas_canny"], use_container_width=True)
                elif camada == "Contornos" and "contornos_aero_bgr" in art:
                    st.image(_bgr_to_rgb(art["contornos_aero_bgr"]), use_container_width=True)
                elif camada == "Máscara de Poros" and "mascara_poros" in art:
                    st.image(art["mascara_poros"], use_container_width=True)
                elif camada == "Coerência (Tensor)" and "coerencia_color" in art:
                    st.image(_bgr_to_rgb(art["coerencia_color"]), use_container_width=True)
                else:
                    st.image(_bgr_to_rgb(img_bgr), use_container_width=True)

        # --- ÁREA B & C: RESULTADO DA INSPEÇÃO & DEFEITOS ENCONTRADOS ---
        with col_info:
            # Banner Semântico de Decisão
            if status == "APROVADO":
                banner_color = "#10B981"
                banner_bg = "#ECFDF5"
                banner_title = "SOLDA APROVADA"
                badge_type = "success"
            elif status == "ALERTA":
                banner_color = "#F59E0B"
                banner_bg = "#FFFBEB"
                banner_title = "ALERTA OPERACIONAL"
                badge_type = "warning"
            else:
                banner_color = "#EF4444"
                banner_bg = "#FEF2F2"
                banner_title = "SOLDA REPROVADA"
                badge_type = "danger"

            st.markdown(
                f"""
                <div style="background:{banner_bg}; border: 2px solid {banner_color}; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px;">
                    <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">Resultado da Inspeção</div>
                    <div style="font-size:1.6rem; font-weight:900; color:{banner_color}; margin: 2px 0;">{banner_title}</div>
                    <div style="font-size:0.80rem; color:#334E68;">
                        Amostra: <b>{nome_arquivo}</b> · Dimensões: {img_bgr.shape[1]}×{img_bgr.shape[0]} px
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Área B: Indicadores Relevantes (Sem invenção de dados)
            st.markdown(f'<div class="section-title">{svg_icon("gauge", c["text_heading"], 14)} Indicadores da Junta</div>', unsafe_allow_html=True)
            k_c1, k_c2 = st.columns(2)
            if is_thermal:
                with k_c1:
                    render_kpi("Pico Térmico", f"~{res.get('temperatura_max_estimada_c', 0):.0f} °C", "Estimativa radiométrica", "activity", "danger" if res.get("status") == "REPROVADO" else "primary")
                with k_c2:
                    render_kpi("Área ZAC/HAZ", f"{res.get('percentual_haz', 0):.1f}%", "Zona termicamente afetada", "layers", "warning" if res.get("percentual_haz", 0) > 40 else "success")
                k_c3, k_c4 = st.columns(2)
                with k_c3:
                    render_kpi("Poça Fusão", f"{res.get('percentual_hotspot', 0):.1f}%", "Hotspot de soldagem", "speed", "primary")
                with k_c4:
                    render_kpi("Razão ZAC/Fusão", f"{res.get('razao_haz_hotspot', 0):.2f}", "Meta nominal < 4.5", "verified", "primary")
            else:
                poro_p = res.get("porosidade_percentual", 0.0)
                n_poros = res.get("contagem_poros", 0)
                larg_m = res.get("largura_media_px", 0.0)
                n_desc = res.get("descontinuidades_detectadas", 0)

                with k_c1:
                    render_kpi("Porosidade", f"{poro_p:.2f}%", f"{n_poros} poros detectados", "scan_eye", "danger" if poro_p >= limiar_poro else "success")
                with k_c2:
                    render_kpi("Largura do Cordão", f"{larg_m:.1f} px", f"Variação: {res.get('variacao_largura_percentual', 0):.1f}%", "activity", "primary")
                k_c3, k_c4 = st.columns(2)
                with k_c3:
                    render_kpi("Descontinuidades", f"{n_desc}", "Mordeduras / Estreitamentos", "wrench", "danger" if n_desc >= 5 else "success")
                with k_c4:
                    render_kpi("Coerência Escamas", f"{res.get('coerencia_escamas', 0):.1%}", "Regularidade direcional", "layers", "success" if res.get('coerencia_escamas', 0) >= 0.52 else "danger")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # Área C: Defeitos Encontrados (Lista Compacta Operacional)
            st.markdown(f'<div class="section-title">{svg_icon("alert_triangle", c["text_heading"], 14)} Defeitos & Apontamentos</div>', unsafe_allow_html=True)
            motivos = res.get("motivos", [])
            if status == "APROVADO":
                st.success("Nenhum defeito impeditivo identificado. O cordão atende aos requisitos normativos.")
            else:
                for idx, m in enumerate(motivos[:4]):
                    st.markdown(
                        f"""
                        <div style="background:#FFFFFF; border-left: 4px solid #EF4444; border-radius: 4px; padding: 8px 12px; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-size:0.80rem; font-weight:700; color:#102A43;">Não Conformidade #{idx + 1}</div>
                            <div style="font-size:0.76rem; color:#475569;">{m}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # =========================================================================
    # ABA 2: Comparação com Gabarito (IoU - Padrão AeroMotion Dynamics)
    # =========================================================================
    with tab_gabarito:
        st.markdown(
            f'<div class="section-title">{svg_icon("file_check", c["text_heading"], 15)} Comparação Objetiva com Gabarito Técnico</div>',
            unsafe_allow_html=True,
        )
        if ref_ok is not None and ref_bad is not None and not is_thermal:
            comp = classify_geometry_against_references(img_bgr, ref_ok, ref_bad)
            cm = comp.get("metrics", {})

            gc1, gc2, gc3 = st.columns([1.0, 1.0, 1.2])
            with gc1:
                st.image(_bgr_to_rgb(ref_ok), caption="Gabarito Aprovado (Normal)", use_container_width=True)
            with gc2:
                st.image(_bgr_to_rgb(img_bgr), caption="Amostra Inspecionada", use_container_width=True)
            with gc3:
                st.markdown(
                    f"""
                    <div class="vt-card" style="padding: 16px;">
                        <div style="font-size:0.8rem; font-weight:700; color:#102A43; margin-bottom:10px;">Similaridade Geométrica (IoU)</div>
                        <div style="margin-bottom:8px;">
                            <div style="font-size:0.75rem; color:#475569;">Similaridade com Padrão Aprovado</div>
                            <div style="font-size:1.3rem; font-weight:800; color:#10B981;">{cm.get('normal_reference_iou', 0):.3f}</div>
                        </div>
                        <div style="margin-bottom:8px;">
                            <div style="font-size:0.75rem; color:#475569;">Similaridade com Padrão Reprovado</div>
                            <div style="font-size:1.3rem; font-weight:800; color:#EF4444;">{cm.get('defective_reference_iou', 0):.3f}</div>
                        </div>
                        <div style="font-size:0.75rem; color:#334E68; border-top: 1px solid #E2E8F0; padding-top:8px;">
                            Classificação: <b>{comp.get('classification', 'N/A')}</b> (Margem: {cm.get('match_margin', 0):.3f})
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Comparação de gabarito disponível para modalidades geométricas.")

    # =========================================================================
    # ABA 3: Histórico de Inspeções
    # =========================================================================
    with tab_historico:
        st.markdown(
            f'<div class="section-title">{svg_icon("clock", c["text_heading"], 15)} Registros de Inspeções no Banco de Dados</div>',
            unsafe_allow_html=True,
        )
        try:
            hist = get_vision_history(limit=50)
            items = hist.get("items", [])
            if items:
                df_h = pd.DataFrame(items)[["id", "image_name", "modality", "status", "created_at"]]
                df_h.columns = ["ID", "Amostra", "Modalidade", "Resultado", "Data/Hora"]
                st.dataframe(df_h, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma inspeção persistida no histórico SQLite até o momento.")
        except Exception as exc:
            st.caption(f"Histórico em banco SQLite não disponível: {exc}")


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Visão Computacional")
