"""Módulo de Visão Computacional — Inspeção Geométrica, Porosidade (Filtros AeroMotion/OpenCV) e Termografia (HSV/HAZ)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.services.vision_service import get_vision_history
from frontend.styles import DESIGN_TOKENS
from src.vision.thermal_analysis import analisar_termografia_solda
from src.vision.weld_inspection import carregar_imagem, inspecionar_solda
from vision.geometry import classify_geometry_against_references
from vision.pipeline import diagnose_image_dataset

RAIZ = Path(__file__).resolve().parents[2]
RAW_IMG_DIR = RAIZ / "data" / "raw" / "imagens"


def _bgr_to_rgb(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    st.markdown(
        """
        <div style="margin-bottom:1.0rem;">
            <h1 style="margin:0; font-size:1.55rem; color:#102A43; font-weight:800;">
                VISÃO COMPUTACIONAL — INSPEÇÃO GEOMÉTRICA, POROSIDADE E TERMOGRAFIA
            </h1>
            <div style="font-size:0.84rem; color:#334E68; font-weight:500;">
                Pipeline multi-estágio de filtros OpenCV (CLAHE, Gaussiano, Sobel, Tensor de Estrutura, Black-Hat, Canny, Silhueta IoU) e termografia HSV (ZAC/HAZ)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Diagnóstico do Dataset de Imagens (Padrão AeroMotion Dynamics)", expanded=False):
        try:
            diag = diagnose_image_dataset(RAW_IMG_DIR)
            st.write(
                f"Arquivos encontrados: **{diag['total_files']}** · "
                f"Imagens suportadas: **{diag['supported_images']}** · "
                f"Dimensões: `{diag['dimensions']}`"
            )
            df_diag = pd.DataFrame(
                [
                    {
                        "Modalidade": mod,
                        "Imagens": cnt,
                        "Classes Detectadas": ", ".join(
                            f"{lbl} ({amt})"
                            for lbl, amt in diag["class_counts"].get(mod, {}).items()
                        )
                        or "Rótulo por inspeção",
                    }
                    for mod, cnt in diag["modality_counts"].items()
                ]
            )
            st.dataframe(df_diag, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.caption(f"Diagnóstico resumido indisponível: {exc}")

    aba_geom, aba_term, aba_hist = st.tabs(
        [
            "1. Inspeção Geométrica & Porosidade (Filtros OpenCV)",
            "2. Análise Termográfica ZAC/HAZ (HSV)",
            "3. Histórico de Inspeções",
        ]
    )

    # -------------------------------------------------------------------------
    # ABA 1: Inspeção Geométrica & Porosidade (Pipeline Completo de Filtros)
    # -------------------------------------------------------------------------
    with aba_geom:
        st.markdown(
            "<h3 style='font-size:1.05rem; font-weight:700; color:#102A43;'>"
            "Pipeline de Filtros para Identificação de Soldas Aprovadas vs. Reprovadas (ISO 5817)"
            "</h3>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Sequência de filtros aplicados: (1) Escala de Cinza & CLAHE → (2) Suavização Gaussiana & Unsharp Mask → "
            "(3) Energia de Gradiente Direcional de Sobel (Gx, Gy) + Otsu para Segmentação do Cordão → "
            "(4) Tensor de Estrutura (Coerência Direcional das Escamas vs. Isotropia Globular) → "
            "(5) Morfologia Black-Hat + Circularidade (4πA/P²) para Isolamento de Poros e Crateras → "
            "(6) Detector de Bordas de Canny & Contornos → (7) Perfil Transversal de Largura (80 seções) e Silhueta Normalizada (IoU)."
        )

        # Carrega referências visuais padrão (aprovada vs reprovada)
        ref_aprov_path = RAW_IMG_DIR / "solda_aprovada.png"
        ref_reprov_path = RAW_IMG_DIR / "solda_reprovada.png"
        ref_aprov_img = carregar_imagem(ref_aprov_path) if ref_aprov_path.is_file() else None
        ref_reprov_img = carregar_imagem(ref_reprov_path) if ref_reprov_path.is_file() else None

        with st.expander("Referências Visuais de Comparação (Padrão Normal vs. Padrão Reprovado)", expanded=False):
            rcol1, rcol2 = st.columns(2)
            with rcol1:
                if ref_aprov_img is not None:
                    st.image(
                        _bgr_to_rgb(ref_aprov_img),
                        caption="Referência Normal (Aprovada) · solda_aprovada.png — Escamas regulares e bordas paralelas",
                        use_container_width=True,
                    )
            with rcol2:
                if ref_reprov_img is not None:
                    st.image(
                        _bgr_to_rgb(ref_reprov_img),
                        caption="Referência Defeituosa (Reprovada) · solda_reprovada.png — Porosidade, crateras e mordeduras",
                        use_container_width=True,
                    )

        gcol_left, gcol_right = st.columns([1.0, 1.45])

        with gcol_left:
            origem_geom = st.radio(
                "Selecione a Imagem de Solda para Inspeção:",
                ["solda_aprovada.png", "solda_reprovada.png", "Upload Próprio"],
                horizontal=True,
                key="vt_geom_source_radio",
            )

            img_bgr_selecionada: np.ndarray | None = None
            nome_imagem = origem_geom

            if origem_geom == "Upload Próprio":
                arq_up = st.file_uploader(
                    "Enviar imagem de junta soldada",
                    type=["png", "jpg", "jpeg", "tif"],
                    key="up_geom",
                )
                if arq_up is not None:
                    nparr = np.frombuffer(arq_up.getvalue(), np.uint8)
                    img_bgr_selecionada = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    nome_imagem = arq_up.name
            else:
                caminho_teste = RAW_IMG_DIR / origem_geom
                if caminho_teste.is_file():
                    img_bgr_selecionada = carregar_imagem(caminho_teste)

            st.markdown("**Parâmetros dos Filtros OpenCV & Critérios ISO 5817**")
            pcol1, pcol2 = st.columns(2)
            with pcol1:
                gaussian_k = st.selectbox(
                    "Kernel Gaussiano (px)",
                    options=[3, 5, 7, 9],
                    index=1,
                    key="vt_geom_gauss_k",
                )
                limiar_poro = st.slider(
                    "Limiar de Rejeição por Porosidade (%)",
                    0.5,
                    5.0,
                    3.0,
                    0.25,
                    key="vt_geom_poro_lim",
                )
                min_circ = st.slider(
                    "Circularidade Mínima de Poro (4πA/P²)",
                    0.15,
                    0.75,
                    0.28,
                    0.02,
                    key="vt_geom_circ_min",
                )
            with pcol2:
                canny_range = st.slider(
                    "Limiares Canny (Baixo / Alto)",
                    0,
                    255,
                    (50, 150),
                    key="vt_geom_canny_range",
                )
                min_area_contour = st.number_input(
                    "Área Mínima Contorno Canny (px)",
                    min_value=5,
                    max_value=5000,
                    value=20,
                    step=5,
                    key="vt_geom_min_area",
                )
                limiar_var_larg = st.slider(
                    "Limiar Variação de Largura (%)",
                    5.0,
                    25.0,
                    10.0,
                    0.5,
                    key="vt_geom_var_larg",
                )

            executar_btn = st.button(
                "Executar Inspeção Geométrica & Porosidade",
                type="primary",
                use_container_width=True,
                key="btn_exec_geom",
            )

            assinatura_atual = (
                nome_imagem,
                int(gaussian_k),
                int(canny_range[0]),
                int(canny_range[1]),
                int(min_area_contour),
                float(limiar_poro),
                float(min_circ),
                float(limiar_var_larg),
            )

            if img_bgr_selecionada is not None and (
                executar_btn
                or st.session_state.get("vt_geom_last_sig") != assinatura_atual
                or "res_geom" not in st.session_state
            ):
                with st.spinner("Aplicando filtros OpenCV (CLAHE, Sobel, Tensor de Estrutura, Black-Hat, Canny e Perfil)..."):
                    res_geom = inspecionar_solda(
                        img_bgr_selecionada,
                        limiar_porosidade_reprovacao=limiar_poro,
                        limiar_variacao_largura_reprovacao=limiar_var_larg,
                        gaussian_kernel=int(gaussian_k),
                        canny_low=int(canny_range[0]),
                        canny_high=max(int(canny_range[1]), int(canny_range[0]) + 1),
                        min_contour_area=float(min_area_contour),
                        min_circularidade_poro=float(min_circ),
                        incluir_artefatos_filtros=True,
                    )
                    comp_ref = classify_geometry_against_references(
                        img_bgr_selecionada,
                        normal_reference=ref_aprov_img,
                        defective_reference=ref_reprov_img,
                    )
                    st.session_state["res_geom"] = res_geom
                    st.session_state["comp_ref_geom"] = comp_ref
                    st.session_state["vt_geom_last_sig"] = assinatura_atual

            if img_bgr_selecionada is not None:
                st.image(
                    _bgr_to_rgb(img_bgr_selecionada),
                    caption=f"Imagem Original Selecionada: {nome_imagem} ({img_bgr_selecionada.shape[1]} × {img_bgr_selecionada.shape[0]} px)",
                    use_container_width=True,
                )

        with gcol_right:
            res_geom = st.session_state.get("res_geom")
            comp_ref = st.session_state.get("comp_ref_geom")
            if res_geom:
                status_inspecao = res_geom["status"]
                cor_status = {
                    "APROVADO": "#10B981",
                    "ALERTA": "#F59E0B",
                    "REPROVADO": "#EF4444",
                }.get(status_inspecao, "#10B981")
                rotulo_veredito = (
                    "APROVADO — DENTRO DOS CONFORMES"
                    if status_inspecao == "APROVADO"
                    else f"{status_inspecao} — DEFEITO GEOMÉTRICO / POROSIDADE DETECTADO"
                )

                st.markdown(
                    f"""
                    <div class="vt-card" style="border-left: 6px solid {cor_status}; padding: 14px; margin-bottom: 12px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#475569;">PARECER DA INSPEÇÃO GEOMÉTRICA & POROSIDADE</div>
                        <div style="font-size:1.45rem; font-weight:800; color:{cor_status};">{rotulo_veredito}</div>
                        <div style="font-size:0.84rem; color:#1E293B; margin-top:6px;">
                            {'<br>• '.join(['• ' + m for m in res_geom.get('motivos', [])]).replace('• • ', '• ', 1)}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Linha 1 de KPIs
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Porosidade (%)", f"{res_geom['porosidade_percentual']:.2f}%")
                m2.metric("Poros / Crateras", f"{res_geom['contagem_poros']}")
                m3.metric("Coerência das Escamas", f"{res_geom.get('coerencia_escamas', 0.0):.1%}")
                m4.metric("Largura Média Cordão", f"{res_geom['largura_media_px']:.1f} px")

                # Linha 2 de KPIs
                m5, m6, m7, m8 = st.columns(4)
                m5.metric("Variação de Largura", f"{res_geom['variacao_largura_percentual']:.1f}%")
                m6.metric("Rugosidade Margem", f"{res_geom.get('rugosidade_margem_px', 0.0):.1f} px")
                m7.metric("Descontinuidades", f"{res_geom['descontinuidades_detectadas']}")
                m8.metric("Contornos Canny", f"{res_geom.get('contagem_contornos_canny', 0)}")

                if comp_ref and "metrics" in comp_ref:
                    cm = comp_ref["metrics"]
                    st.caption(
                        f"**Comparação com Referências (AeroMotion IoU + Morfologia):** "
                        f"Similaridade Normal (`solda_aprovada`): **{cm['normal_reference_iou']:.3f}** · "
                        f"Similaridade Reprovada (`solda_reprovada`): **{cm['defective_reference_iou']:.3f}** · "
                        f"Margem de Decisão: **{cm['match_margin']:.3f}**"
                    )

                if "imagem_anotada_base64" in res_geom:
                    img_data = base64.b64decode(res_geom["imagem_anotada_base64"])
                    st.image(
                        img_data,
                        caption="Resultado Final Anotado: Contorno do Cordão, Seções Transversais de Largura e Poros/Crateras Destacados",
                        use_container_width=True,
                    )

        # Galeria Completa de Todas as Etapas de Filtragem OpenCV
        res_geom = st.session_state.get("res_geom")
        if res_geom and "artefatos" in res_geom:
            art = res_geom["artefatos"]
            st.markdown("---")
            st.markdown(
                "<h3 style='font-size:1.05rem; font-weight:700; color:#102A43;'>"
                "Etapas de Filtragem Aplicadas (Inspeção Passo a Passo — Base Projeto_Aero)"
                "</h3>",
                unsafe_allow_html=True,
            )

            f_row1_c1, f_row1_c2, f_row1_c3, f_row1_c4 = st.columns(4)
            with f_row1_c1:
                st.image(
                    art["clahe"],
                    caption="1. Escala de Cinza + Equalização CLAHE",
                    use_container_width=True,
                )
            with f_row1_c2:
                st.image(
                    art["sobel_mag"],
                    caption="2. Magnitude do Gradiente de Sobel (Gx, Gy)",
                    use_container_width=True,
                )
            with f_row1_c3:
                st.image(
                    art["bordas_canny"],
                    caption="3. Detector de Bordas de Canny",
                    use_container_width=True,
                )
            with f_row1_c4:
                st.image(
                    art["mascara_cordao"],
                    caption="4. Segmentação Morfológica do Cordão (Otsu + Close/Open)",
                    use_container_width=True,
                )

            f_row2_c1, f_row2_c2, f_row2_c3, f_row2_c4 = st.columns(4)
            with f_row2_c1:
                st.image(
                    _bgr_to_rgb(art["coerencia_color"]),
                    caption="5. Tensor de Estrutura (Coerência Direcional das Escamas)",
                    use_container_width=True,
                )
            with f_row2_c2:
                st.image(
                    art["blackhat"],
                    caption="6. Filtro Morfológico Black-Hat (Realce de Cavidades Escuras)",
                    use_container_width=True,
                )
            with f_row2_c3:
                st.image(
                    art["mascara_poros"],
                    caption="7. Máscara Binária de Poros e Crateras (Isotropia + Circularidade)",
                    use_container_width=True,
                )
            with f_row2_c4:
                st.image(
                    _bgr_to_rgb(art["contornos_aero_bgr"]),
                    caption="8. Contornos Canny e Caixas Delimitadoras (Padrão AeroMotion)",
                    use_container_width=True,
                )

            # Gráfico do Perfil Transversal de Largura e Tabela de Poros/Contornos
            p_col_chart, p_col_table = st.columns([1.15, 1.0])
            with p_col_chart:
                pts = res_geom.get("perfil_largura", [])
                if pts:
                    df_prof = pd.DataFrame(pts)
                    fig_prof = go.Figure()
                    fig_prof.add_trace(
                        go.Scatter(
                            x=df_prof["position_px"],
                            y=df_prof["width_px"],
                            mode="lines+markers",
                            name="Largura Local (px)",
                            line=dict(color="#1565C0", width=2.5),
                            marker=dict(size=4),
                        )
                    )
                    larg_m = res_geom["largura_media_px"]
                    fig_prof.add_hline(
                        y=larg_m,
                        line_dash="dash",
                        line_color="#10B981",
                        annotation_text=f"Média: {larg_m:.1f} px",
                    )
                    fig_prof.add_hline(
                        y=larg_m * 1.16,
                        line_dash="dot",
                        line_color="#EF4444",
                        annotation_text="Limite Superior (+16%)",
                    )
                    fig_prof.add_hline(
                        y=larg_m * 0.84,
                        line_dash="dot",
                        line_color="#EF4444",
                        annotation_text="Limite Inferior (-16%)",
                    )
                    fig_prof.update_layout(
                        title="Perfil Transversal de Largura do Cordão de Solda (80 Cortes)",
                        xaxis_title="Posição Longitudinal X (px)",
                        yaxis_title="Largura Transversal do Cordão (px)",
                        height=300,
                        margin=dict(l=20, r=20, t=40, b=20),
                        template="plotly_white",
                    )
                    st.plotly_chart(fig_prof, use_container_width=True, config={"displayModeBar": False})

            with p_col_table:
                st.markdown("**Tabela de Poros/Cavidades e Contornos Detectados**")
                poros_list = res_geom.get("lista_poros", [])
                if poros_list:
                    df_poros = pd.DataFrame(
                        [
                            {
                                "ID Poro": p.get("index", idx),
                                "Centro (x, y)": f"({p['centro'][0]}, {p['centro'][1]})",
                                "Raio (px)": p["raio"],
                                "Área (px²)": p["area"],
                                "Circularidade (4πA/P²)": p["circularidade"],
                            }
                            for idx, p in enumerate(poros_list[:25])
                        ]
                    )
                    st.dataframe(df_poros, use_container_width=True, hide_index=True, height=250)
                else:
                    cnts_list = res_geom.get("contornos_canny", [])
                    if cnts_list:
                        df_cnts = pd.DataFrame(
                            [
                                {
                                    "Índice": c["index"],
                                    "Área (px²)": round(c["area"], 1),
                                    "Perímetro (px)": round(c["perimeter"], 1),
                                    "Circularidade": round(c["circularity"], 3) if c["circularity"] else 0.0,
                                    "Razão Aspecto": round(c["aspect_ratio"], 2) if c["aspect_ratio"] else 0.0,
                                    "BBox": f"{c['bbox']['width']}×{c['bbox']['height']} em ({c['bbox']['x']},{c['bbox']['y']})",
                                }
                                for c in cnts_list[:20]
                            ]
                        )
                        st.dataframe(df_cnts, use_container_width=True, hide_index=True, height=250)
                    else:
                        st.success("Nenhum poro ou cavidade crítica detectado no cordão inspecionado.")

    # -------------------------------------------------------------------------
    # ABA 2: Análise Termográfica ZAC / HAZ (HSV)
    # -------------------------------------------------------------------------
    with aba_term:
        st.markdown(
            "<h3 style='font-size:1.05rem; font-weight:700; color:#102A43;'>"
            "Análise Termográfica e Zona Afetada pelo Calor (ZAC/HAZ — Segmentação HSV)"
            "</h3>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Segmentação no espaço de cor HSV: isolamento de hotspots na poça de fusão, "
            "delimitação da Zona Afetada pelo Calor (HAZ), cálculo da razão ZAC/Fusão e diagnóstico de falta de fusão ou superaquecimento."
        )

        tcol_left, tcol_right = st.columns([1.0, 1.35])

        with tcol_left:
            origem_term = st.radio(
                "Selecione a Imagem Térmica:",
                ["termica_solda_aprovada.png", "termica_solda_reprovada.png", "Upload Próprio"],
                horizontal=True,
                key="vt_term_source_radio",
            )

            term_bytes = None
            caminho_term_teste = None

            if origem_term == "Upload Próprio":
                arq_up_t = st.file_uploader(
                    "Enviar termografia falsa-cor",
                    type=["png", "jpg", "jpeg", "tif"],
                    key="up_term",
                )
                if arq_up_t is not None:
                    term_bytes = arq_up_t.read()
            else:
                caminho_term_teste = RAW_IMG_DIR / origem_term
                if caminho_term_teste.is_file():
                    term_bytes = caminho_term_teste.read_bytes()

            exec_term_btn = st.button(
                "Executar Análise Térmica",
                type="primary",
                use_container_width=True,
                key="btn_exec_term",
            )

            if term_bytes is not None and (
                exec_term_btn
                or st.session_state.get("vt_term_last_src") != origem_term
                or "res_term" not in st.session_state
            ):
                nparr_t = np.frombuffer(term_bytes, np.uint8)
                img_t_bgr = cv2.imdecode(nparr_t, cv2.IMREAD_COLOR)
                with st.spinner("Processando espaço de cor HSV e isolinhas térmicas..."):
                    res_term = analisar_termografia_solda(
                        caminho_term_teste if caminho_term_teste else img_t_bgr
                    )
                st.session_state["res_term"] = res_term
                st.session_state["vt_term_last_src"] = origem_term

            if term_bytes is not None:
                st.image(term_bytes, caption=f"Termograma Original: {origem_term}", use_container_width=True)

        with tcol_right:
            res_term = st.session_state.get("res_term")
            if res_term:
                status_term = res_term["status"]
                cor_term = {
                    "APROVADO": "#10B981",
                    "ALERTA": "#F59E0B",
                    "REPROVADO": "#EF4444",
                }.get(status_term, "#10B981")

                st.markdown(
                    f"""
                    <div class="vt-card" style="border-left: 6px solid {cor_term}; padding: 14px; margin-bottom: 12px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#475569;">DIAGNÓSTICO TERMOGRÁFICO ZAC/HAZ</div>
                        <div style="font-size:1.45rem; font-weight:800; color:{cor_term};">{status_term} — {res_term['diagnostico']}</div>
                        <div style="font-size:0.85rem; color:#334155; margin-top:4px;">
                            {' | '.join(res_term.get('motivos', []))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                tm1, tm2, tm3, tm4 = st.columns(4)
                tm1.metric("Pico Térmico Est.", f"~{res_term['temperatura_max_estimada_c']:.0f} °C")
                tm2.metric("Área ZAC/HAZ", f"{res_term['percentual_haz']:.1f}%")
                tm3.metric("Poça de Fusão", f"{res_term['percentual_hotspot']:.1f}%")
                tm4.metric("Razão ZAC/Fusão", f"{res_term['razao_haz_hotspot']:.2f}")

                if "imagem_anotada_base64" in res_term:
                    img_data_t = base64.b64decode(res_term["imagem_anotada_base64"])
                    st.image(
                        img_data_t,
                        caption="Heatmap com Isolinhas de Fusão e ZAC (HSV Segmentado)",
                        use_container_width=True,
                    )

    # -------------------------------------------------------------------------
    # ABA 3: Histórico de Inspeções
    # -------------------------------------------------------------------------
    with aba_hist:
        st.markdown(
            "<h3 style='font-size:1.05rem; font-weight:700; color:#102A43;'>Histórico de Inspeções no Banco SQLite</h3>",
            unsafe_allow_html=True,
        )
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


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Visão Computacional")
