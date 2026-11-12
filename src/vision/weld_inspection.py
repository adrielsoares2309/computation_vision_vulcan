"""Inspeção geométrica e de porosidade de cordão de solda por visão computacional (OpenCV).

Baseado nos filtros do repositório AeroMotion Dynamics (Projeto_Aero) combinados com
filtros industriais para soldas MIG/MAG (ISO 5817 / AWS D1.1):
1. Conversão para Escala de Cinza (Grayscale)
2. Equalização Adaptativa de Histograma (CLAHE)
3. Suavização Gaussiana (GaussianBlur) & Realce Laplaciano (Unsharp Mask)
4. Gradientes Direcionais de Sobel (Gx, Gy) & Segmentação por Energia de Textura + Otsu + Morfologia
5. Tensor de Estrutura (Jxx, Jyy, Jxy) para Coerência Direcional das Escamas e Isotropia
6. Detector de Bordas de Canny & Extração de Atributos de Contornos (Área, Perímetro, Circularidade, Solidez, BBox)
7. Filtro Morfológico Black-Hat ponderado por Isotropia + Circularidade (4πA/P²) para Porosidade e Crateras
8. Perfil Transversal de Largura (80 cortes), Rugosidade de Margem (Mordeduras) e Comparação por Silhueta (IoU)
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from vision.geometry import (
    GeometryConfig,
    _normalized_silhouette,
    analyze_bead_profile,
    classify_geometry_against_references,
    contour_features,
    detect_porosity_and_coherence,
    segment_weld_bead,
)


def carregar_imagem(origem: str | Path | np.ndarray) -> np.ndarray:
    """Carrega uma imagem como array BGR uint8."""
    if isinstance(origem, np.ndarray):
        if origem.dtype != np.uint8:
            origem = np.clip(origem, 0, 255).astype(np.uint8)
        if origem.ndim == 2:
            return cv2.cvtColor(origem, cv2.COLOR_GRAY2BGR)
        if origem.ndim == 3 and origem.shape[2] == 4:
            return cv2.cvtColor(origem, cv2.COLOR_BGRA2BGR)
        return origem.copy()

    caminho = Path(origem)
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo de imagem não encontrado: {caminho}")
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Não foi possível decodificar a imagem: {caminho}")
    return img


def aplicar_filtro_realce(cinza: np.ndarray, gaussian_kernel: int = 5) -> np.ndarray:
    """Aplica suavização gaussiana e filtro de nitidez (unsharp mask)."""
    k = max(3, int(gaussian_kernel) | 1)
    suavizada = cv2.GaussianBlur(cinza, (k, k), sigmaX=1.0)
    kernel_sharpen = np.array(
        [[0, -1, 0], [-1, 5, -1], [0, -1, 0]],
        dtype=np.float32,
    )
    return cv2.filter2D(suavizada, -1, kernel_sharpen)


def detectar_bordas_canny(
    imagem_realcada: np.ndarray,
    limiar_baixo: int = 50,
    limiar_alto: int = 150,
) -> np.ndarray:
    """Aplica o algoritmo de detecção de bordas de Canny com limiares configuráveis."""
    return cv2.Canny(imagem_realcada, int(limiar_baixo), int(limiar_alto))


def estimar_porosidade(
    cinza: np.ndarray,
    mascara_cordao: np.ndarray,
    min_area: int = 12,
    max_area: int = 4000,
    min_circularidade: float = 0.28,
    blackhat_kernel: int = 19,
) -> tuple[int, float, list[dict[str, Any]], np.ndarray]:
    """Detecta cavidades/poros reais no cordão via Black-Hat morfológico, Tensor de Estrutura (Isotropia) e Circularidade.

    Elimina falsos positivos provenientes das sombras alongadas entre escamas de solda regulares.
    Retorna: (contagem_poros, area_total_poros, lista_poros, mascara_poros).
    """
    info = detect_porosity_and_coherence(
        cinza,
        mascara_cordao,
        blackhat_kernel=blackhat_kernel,
        min_circularity=min_circularidade,
    )
    poros_filtrados = [
        p for p in info["pores"] if min_area <= p["area"] <= max_area
    ]
    area_total = float(sum(p["area"] for p in poros_filtrados))
    return len(poros_filtrados), area_total, poros_filtrados, info["porosity_mask"]


def analisar_descontinuidade_cordao(
    contorno_cordao: np.ndarray,
    altura_img: int,
    largura_img: int,
    mascara_cordao: np.ndarray | None = None,
) -> tuple[float, float, float, float, int, list[dict[str, Any]]]:
    """Analisa a uniformidade transversal da largura do cordão, rugosidade de margem e descontinuidades."""
    if mascara_cordao is None:
        mascara_cordao = np.zeros((altura_img, largura_img), dtype=np.uint8)
        cv2.drawContours(mascara_cordao, [contorno_cordao], -1, 255, thickness=cv2.FILLED)

    prof = analyze_bead_profile(mascara_cordao, contorno_cordao)
    return (
        float(prof["mean_width_px"]),
        float(prof["min_width_px"]),
        float(prof["max_width_px"]),
        float(prof["width_variation_pct"]),
        int(prof["discontinuities_count"]),
        prof["discontinuities"],
    )


def _encode_png_base64(img: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf).decode("ascii")


def inspecionar_solda(
    origem_imagem: str | Path | np.ndarray,
    limiar_porosidade_reprovacao: float = 3.0,
    limiar_porosidade_alerta: float = 1.0,
    limiar_variacao_largura_reprovacao: float = 10.0,
    gaussian_kernel: int = 5,
    canny_low: int = 50,
    canny_high: int = 150,
    min_contour_area: float = 20.0,
    min_circularidade_poro: float = 0.28,
    incluir_artefatos_filtros: bool = False,
    salvar_anotada_em: str | Path | None = None,
) -> dict[str, Any]:
    """Executa a inspeção geométrica e de porosidade completa do cordão de solda via OpenCV.

    Aplica todos os filtros do Projeto_Aero + filtros metalúrgicos de porosidade e coerência:
    1. Escala de Cinza (Grayscale) & Equalização Adaptativa CLAHE
    2. Suavização Gaussiana (GaussianBlur) & Filtro de Nitidez (Unsharp Mask)
    3. Gradientes Direcionais de Sobel (Gx, Gy) & Energia Morfológica para Isolar o Cordão
    4. Detector de Bordas de Canny & Extração de Contornos (Área, Perímetro, Circularidade, Solidez, BBox)
    5. Tensor de Estrutura (Jxx, Jyy, Jxy) para Coerência Direcional das Escamas vs. Morfologia Globular
    6. Filtro Black-Hat + Isotropia + Circularidade (4πA/P²) para Isolamento de Poros e Crateras
    7. Medição do Perfil Transversal de Largura (80 seções), Rugosidade de Margem (Mordeduras) e Silhueta Normalizada
    8. Classificação Industrial Determinística (APROVADO / ALERTA / REPROVADO) e Renderização HUD
    """
    img_bgr = carregar_imagem(origem_imagem)
    altura, largura = img_bgr.shape[:2]

    # Filtro 1: Escala de Cinza e Equalização Adaptativa CLAHE
    cinza = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cinza)

    # Filtro 2: Suavização Gaussiana e Realce Unsharp Mask
    k_gauss = max(3, int(gaussian_kernel) | 1)
    suavizada = cv2.GaussianBlur(cinza, (k_gauss, k_gauss), 0)
    realcada = aplicar_filtro_realce(cinza, gaussian_kernel=k_gauss)

    # Filtro 3: Segmentação Morfológica do Cordão via Energia de Sobel + Otsu
    mascara_cordao, contorno_cordao, sobel_mag = segment_weld_bead(cinza, gaussian_kernel=k_gauss)
    area_cordao = max(float(np.count_nonzero(mascara_cordao)), 1.0)

    # Filtro 4: Detector de Bordas de Canny e Contornos (Padrão Projeto_Aero)
    c_low = min(max(0, int(canny_low)), 254)
    c_high = max(int(canny_high), c_low + 1)
    bordas = detectar_bordas_canny(suavizada, limiar_baixo=c_low, limiar_alto=c_high)
    contornos_canny_raw, _ = cv2.findContours(bordas.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos_relevantes = [c for c in contornos_canny_raw if cv2.contourArea(c) >= float(min_contour_area)]
    atributos_contornos = [contour_features(c, i) for i, c in enumerate(contornos_relevantes)]

    # Filtro 5 & 6: Coerência Direcional (Tensor de Estrutura) + Porosidade (Black-Hat + Circularidade)
    info_poros = detect_porosity_and_coherence(
        cinza,
        mascara_cordao,
        blackhat_kernel=19,
        min_circularity=float(min_circularidade_poro),
    )
    num_poros = int(info_poros["pores_count"])
    area_poros = float(info_poros["total_pore_area_px"])
    lista_poros = info_poros["pores"]
    mascara_poros = info_poros["porosity_mask"]
    coerencia_escamas = float(info_poros["mean_coherence"])
    isotropia_media = float(info_poros["mean_isotropy"])
    razao_gx_gy = float(info_poros["gx_gy_ratio"])
    porosidade_pct = (area_poros / area_cordao) * 100.0

    # Filtro 7: Perfil de Largura, Rugosidade de Margem (Mordeduras) e Descontinuidades
    perfil = analyze_bead_profile(mascara_cordao, contorno_cordao)
    larg_media = float(perfil["mean_width_px"])
    larg_min = float(perfil["min_width_px"])
    larg_max = float(perfil["max_width_px"])
    var_larg_pct = float(perfil["width_variation_pct"])
    rugosidade_margem = float(perfil["toe_roughness_px"])
    num_desc = int(perfil["discontinuities_count"])
    desc_detalhes = perfil["discontinuities"]

    # Filtro 8: Regras de Decisão Industrial Multimétrica (Independente do nome do arquivo)
    motivos_criticos: list[str] = []
    motivos_alerta: list[str] = []

    if porosidade_pct >= limiar_porosidade_reprovacao or num_poros >= 20:
        motivos_criticos.append(
            f"Porosidade excessiva no cordão ({porosidade_pct:.2f}% / {num_poros} poros detectados; limite: {limiar_porosidade_reprovacao:.1f}%)"
        )
    elif porosidade_pct >= limiar_porosidade_alerta or num_poros >= 3:
        motivos_alerta.append(f"Porosidade moderada ({porosidade_pct:.2f}%, {num_poros} poros)")

    if coerencia_escamas < 0.52:
        motivos_criticos.append(
            f"Baixa coerência direcional das escamas ({coerencia_escamas:.1%} < 52%) — solidificação globular irregular e crateras"
        )
    elif coerencia_escamas < 0.62:
        motivos_alerta.append(f"Coerência direcional das escamas moderada ({coerencia_escamas:.1%})")

    if var_larg_pct >= limiar_variacao_largura_reprovacao or rugosidade_margem >= 8.0:
        motivos_criticos.append(
            f"Irregularidade geométrica crítica nas margens (variação de largura: {var_larg_pct:.1f}%, rugosidade: {rugosidade_margem:.1f}px)"
        )
    elif var_larg_pct >= 6.0 or rugosidade_margem >= 5.0:
        motivos_alerta.append(
            f"Variação moderada de largura ({var_larg_pct:.1f}%) e margem ({rugosidade_margem:.1f}px)"
        )

    if num_desc >= 5:
        motivos_criticos.append(f"{num_desc} descontinuidades dimensionais (mordeduras/estreitamentos) ao longo do cordão")
    elif num_desc >= 2:
        motivos_alerta.append(f"{num_desc} descontinuidades pontuais de margem")

    bx, by, bw, bh_rect = cv2.boundingRect(contorno_cordao)

    if motivos_criticos:
        status = "REPROVADO"
        aprovado = False
        motivos = motivos_criticos + motivos_alerta
        cor_status = (0, 0, 220)  # Vermelho industrial
    elif motivos_alerta:
        status = "ALERTA"
        aprovado = True
        motivos = motivos_alerta
        cor_status = (0, 190, 240)  # Âmbar industrial
    else:
        status = "APROVADO"
        aprovado = True
        motivos = [
            f"Cordão aprovado: escamas uniformes (coerência {coerencia_escamas:.1%}), "
            f"ausência de porosidade crítica ({porosidade_pct:.2f}%) e largura estável ({larg_media:.1f}px, var {var_larg_pct:.1f}%)."
        ]
        cor_status = (0, 180, 0)  # Verde industrial

    # Imagem de contornos Canny no padrão Projeto_Aero
    img_contornos_aero = img_bgr.copy()
    cv2.drawContours(img_contornos_aero, contornos_relevantes, -1, (0, 255, 0), 2)
    for f in atributos_contornos[:150]:
        b = f["bbox"]
        cv2.rectangle(
            img_contornos_aero,
            (b["x"], b["y"]),
            (b["x"] + b["width"], b["y"] + b["height"]),
            (0, 0, 255) if f.get("is_porosity") else (255, 140, 0),
            1,
        )

    # Renderização da Imagem Final Anotada com HUD Industrial
    anotada = img_bgr.copy()
    cv2.rectangle(anotada, (bx, by), (bx + bw, by + bh_rect), cor_status, 2)
    cv2.drawContours(anotada, [contorno_cordao], -1, (255, 180, 0), 2)

    # Desenha linhas de perfil transversal onde há descontinuidades
    for pt in perfil["profile_points"][::2]:
        pos_x = int(pt["position_px"])
        y1 = int(pt["upper_edge_px"])
        y2 = int(pt["lower_edge_px"])
        cor_corte = (0, 140, 255) if pt["edge_deviation_px"] > larg_media * 0.08 else (180, 220, 0)
        cv2.line(anotada, (pos_x, y1), (pos_x, y2), cor_corte, 1)

    # Destacar poros e crateras detectados com círculos vermelhos e cruzetas
    for p in lista_poros:
        cx, cy = p["centro"]
        r = p["raio"]
        cv2.circle(anotada, (cx, cy), r + 3, (0, 0, 255), 2)
        cv2.drawMarker(anotada, (cx, cy), (0, 255, 255), cv2.MARKER_CROSS, max(6, r * 2), 1)

    # Painel HUD superior industrial
    overlay_hud = anotada.copy()
    cv2.rectangle(overlay_hud, (0, 0), (largura, 70), (18, 24, 32), -1)
    cv2.addWeighted(overlay_hud, 0.86, anotada, 0.14, 0, anotada)

    cv2.putText(
        anotada,
        f"INSPECAO GEOMETRICA & POROSIDADE | STATUS: {status}",
        (15, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        cor_status,
        2,
        cv2.LINE_AA,
    )
    metricas_str = (
        f"Porosidade: {porosidade_pct:.2f}% ({num_poros} poros) | "
        f"Coerencia Escamas: {coerencia_escamas:.1%} | "
        f"Largura: {larg_media:.1f}px (var: {var_larg_pct:.1f}%) | "
        f"Descontinuidades: {num_desc}"
    )
    cv2.putText(
        anotada,
        metricas_str,
        (15, 54),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (230, 235, 240),
        1,
        cv2.LINE_AA,
    )

    if salvar_anotada_em is not None:
        caminho_saida = Path(salvar_anotada_em)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(caminho_saida), anotada)

    _, buffer = cv2.imencode(".jpg", anotada, [cv2.IMWRITE_JPEG_QUALITY, 92])
    base64_str = base64.b64encode(buffer).decode("ascii")

    resultado: dict[str, Any] = {
        "status": status,
        "aprovado": aprovado,
        "porosidade_percentual": round(porosidade_pct, 3),
        "contagem_poros": num_poros,
        "area_poros_px": round(area_poros, 1),
        "area_cordao_px": round(area_cordao, 1),
        "largura_media_px": round(larg_media, 1),
        "largura_min_px": round(larg_min, 1),
        "largura_max_px": round(larg_max, 1),
        "variacao_largura_percentual": round(var_larg_pct, 2),
        "rugosidade_margem_px": round(rugosidade_margem, 2),
        "coerencia_escamas": round(coerencia_escamas, 4),
        "isotropia_morfologica": round(isotropia_media, 4),
        "razao_gradiente_xy": round(razao_gx_gy, 4),
        "contagem_contornos_canny": len(atributos_contornos),
        "descontinuidades_detectadas": num_desc,
        "descontinuidades_detalhes": desc_detalhes[:30],
        "perfil_largura": perfil["profile_points"],
        "contornos_canny": atributos_contornos[:50],
        "motivos": motivos,
        "lista_poros": lista_poros[:60],
        "parametros_filtros": {
            "gaussian_kernel": k_gauss,
            "canny_low": c_low,
            "canny_high": c_high,
            "min_contour_area": float(min_contour_area),
            "min_circularidade_poro": float(min_circularidade_poro),
            "limiar_porosidade_reprovacao": float(limiar_porosidade_reprovacao),
            "limiar_variacao_largura_reprovacao": float(limiar_variacao_largura_reprovacao),
        },
        "imagem_anotada_base64": base64_str,
        "dimensoes_imagem": {"largura": largura, "altura": altura},
    }

    if incluir_artefatos_filtros:
        try:
            silhueta = _normalized_silhouette(img_bgr)
        except ValueError:
            silhueta = np.zeros((256, 512), dtype=np.uint8)
        resultado["artefatos"] = {
            "original_bgr": img_bgr,
            "cinza": cinza,
            "clahe": clahe,
            "realcada": realcada,
            "sobel_mag": sobel_mag,
            "bordas_canny": bordas,
            "mascara_cordao": mascara_cordao,
            "coerencia_color": info_poros["coherence_color"],
            "blackhat": info_poros["blackhat"],
            "mascara_poros": mascara_poros,
            "silhueta_normalizada": silhueta,
            "contornos_aero_bgr": img_contornos_aero,
            "anotada_bgr": anotada,
        }

    return resultado
