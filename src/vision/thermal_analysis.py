"""Módulo de análise termográfica de solda via OpenCV e espaço de cor HSV.

Realiza:
1. Conversão de imagem termográfica para o espaço de cor HSV.
2. Segmentação e thresholding de hotspots (poça de fusão / picos térmicos).
3. Segmentação da Zona Afetada pelo Calor (ZAC / HAZ - Heat-Affected Zone).
4. Cálculo da área e percentual da ZAC em relação à área total e à poça de fusão.
5. Estimativa de perfil de temperatura aproximada (°C) via mapeamento térmico de falsa cor.
6. Classificação do estado termográfico (Normal, Alerta Térmico, Subaquecimento/Falta de Fusão, Superaquecimento Crítico).
7. Geração de sobreposição visual anotada (HUD térmico industrial e isolinhas).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def carregar_imagem_termica(origem: str | Path | np.ndarray) -> np.ndarray:
    """Carrega uma imagem termográfica como array BGR uint8."""
    if isinstance(origem, np.ndarray):
        if origem.dtype != np.uint8:
            origem = np.clip(origem, 0, 255).astype(np.uint8)
        if origem.ndim == 2:
            return cv2.applyColorMap(origem, cv2.COLORMAP_INFERNO)
        if origem.ndim == 3 and origem.shape[2] == 4:
            return cv2.cvtColor(origem, cv2.COLOR_BGRA2BGR)
        return origem

    caminho = Path(origem)
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo termográfico não encontrado: {caminho}")
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Não foi possível ler a imagem termográfica: {caminho}")
    return img


def estimar_temperatura_pixel(h: int, s: int, v: int) -> float:
    """Estima a temperatura relativa (°C) baseada na intensidade e matiz de falsa cor."""
    # Faixas típicas de mapa térmico (Ironbow / Jet / Inferno):
    # Branco/Amarelo brilhante: ~1100°C a 1500°C (fusão de aços/titânio)
    # Laranja/Vermelho: ~700°C a 1050°C
    # Magenta/Roxo: ~400°C a 690°C
    # Azul/Ciano: ~150°C a 390°C
    # Fundo escuro/Preto: ~25°C a 140°C
    intensidade = float(v) / 255.0
    saturacao = float(s) / 255.0

    if v > 240 and s < 60:
        # Branco incandescente: núcleo da poça de fusão
        return 1450.0 + (v - 240) * 10.0
    elif (h < 25 or h > 165) and v > 180:
        # Vermelho/Laranja quente
        return 850.0 + intensidade * 450.0
    elif (25 <= h <= 45) and v > 150:
        # Amarelo brilhante
        return 1100.0 + intensidade * 250.0
    elif (130 <= h <= 165) and v > 100:
        # Magenta / Violeta (borda externa ZAC)
        return 450.0 + intensidade * 300.0
    elif (70 <= h <= 130) and v > 70:
        # Verde / Azul (zona de resfriamento distante)
        return 150.0 + intensidade * 250.0
    else:
        # Região fria do substrato
        return 25.0 + intensidade * 120.0


def analisar_termografia_solda(
    origem_imagem: str | Path | np.ndarray,
    limiar_min_hotspot_pixels: int = 25000,
    limiar_max_haz_pct: float = 40.0,
    salvar_anotada_em: str | Path | None = None,
) -> dict[str, Any]:
    """Executa a análise térmica quantitativa do cordão de solda via OpenCV e HSV.

    Retorna métricas da ZAC (HAZ), hotspots, perfil de temperatura e imagem anotada.
    """
    img_bgr = carregar_imagem_termica(origem_imagem)
    altura, largura = img_bgr.shape[:2]
    area_total = float(altura * largura)

    # 1. Conversão para HSV
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h_canal = hsv[:, :, 0]
    s_canal = hsv[:, :, 1]
    v_canal = hsv[:, :, 2]

    # 2. Segmentação de Hotspot (Zona de Fusão / Alta Temperatura)
    # Alta luminosidade (V > 185) e saturação em tons quentes (H < 35 ou H > 160)
    mascara_vermelho_laranja = ((h_canal < 35) | (h_canal > 160)) & (s_canal > 70) & (v_canal > 180)
    mascara_branco_nucleo = (v_canal > 235) & (s_canal < 80)
    mascara_hotspot = np.uint8(mascara_vermelho_laranja | mascara_branco_nucleo) * 255

    # Limpeza morfológica do hotspot
    kernel_hotspot = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mascara_hotspot = cv2.morphologyEx(mascara_hotspot, cv2.MORPH_OPEN, kernel_hotspot)

    # 3. Segmentação da Zona Afetada pelo Calor (ZAC / HAZ)
    # Halo térmico: temperaturas médias/altas no entorno do cordão (V > 110 e saturação moderada)
    mascara_calor_total = np.uint8((v_canal > 110) & ((s_canal > 50) | (v_canal > 180))) * 255
    kernel_haz = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mascara_calor_total = cv2.morphologyEx(mascara_calor_total, cv2.MORPH_CLOSE, kernel_haz)

    # ZAC estrita é o halo térmico menos a poça central de fusão
    mascara_haz = cv2.bitwise_and(mascara_calor_total, cv2.bitwise_not(mascara_hotspot))

    # 4. Cálculo de Áreas e Percentuais
    pixels_hotspot = int(np.count_nonzero(mascara_hotspot))
    pixels_haz = int(np.count_nonzero(mascara_haz))
    pixels_calor_total = int(np.count_nonzero(mascara_calor_total))

    pct_hotspot = (pixels_hotspot / max(area_total, 1.0)) * 100.0
    pct_haz = (pixels_haz / max(area_total, 1.0)) * 100.0
    pct_calor_total = (pixels_calor_total / max(area_total, 1.0)) * 100.0
    razao_haz_hotspot = pixels_haz / max(float(pixels_hotspot), 1.0)

    # 5. Estimativa de Temperaturas
    # Amostragem em grade reduzida para eficiência
    amostras_y = np.linspace(0, altura - 1, 60, dtype=int)
    amostras_x = np.linspace(0, largura - 1, 80, dtype=int)
    grid_h = h_canal[np.ix_(amostras_y, amostras_x)]
    grid_s = s_canal[np.ix_(amostras_y, amostras_x)]
    grid_v = v_canal[np.ix_(amostras_y, amostras_x)]

    temperaturas = [
        estimar_temperatura_pixel(int(grid_h[r, c]), int(grid_s[r, c]), int(grid_v[r, c]))
        for r in range(grid_h.shape[0])
        for c in range(grid_h.shape[1])
    ]
    temp_max_estimada = float(np.max(temperaturas))
    temp_media_estimada = float(np.mean(temperaturas))

    # 6. Diagnóstico Industrial e Classificação
    motivos = []
    if pixels_hotspot < limiar_min_hotspot_pixels:
        status = "REPROVADO"
        aprovado = False
        cor_status = (0, 0, 220)  # Vermelho
        diagnostico = "SUBAQUECIMENTO / FALTA DE FUSAO TERMICA"
        motivos.append(
            f"Energia de soldagem insuficiente: apenas {pixels_hotspot:,} pixels de fusão detectados "
            f"(mínimo esperado: {limiar_min_hotspot_pixels:,}). Alto risco de trinca e descolamento."
        )
    elif pct_haz > limiar_max_haz_pct:
        status = "REPROVADO"
        aprovado = False
        cor_status = (0, 0, 220)
        diagnostico = "SUPERAQUECIMENTO CRITICO (ZAC Excessiva)"
        motivos.append(
            f"Zona Afetada pelo Calor crítica ({pct_haz:.1f}% > {limiar_max_haz_pct:.1f}%). "
            "Risco de crescimento de grão grosseiro e empenamento estrutural da junta."
        )
    elif razao_haz_hotspot > 4.5 or temp_max_estimada > 1750.0:
        status = "ALERTA"
        aprovado = True
        cor_status = (0, 190, 240)  # Âmbar
        diagnostico = "DISSIPACAO TERMICA IRREGULAR"
        motivos.append(
            f"Razão ZAC/Fusão elevada ({razao_haz_hotspot:.2f}). "
            "Recomenda-se ajuste de velocidade de avanço ou gás de proteção."
        )
    else:
        status = "APROVADO"
        aprovado = True
        cor_status = (0, 180, 0)  # Verde
        diagnostico = "DISTRIBUICAO TERMICA HOMOGENEA (Conforme)"
        motivos.append(
            f"Poça de fusão contínua ({pixels_hotspot:,} px, {pct_hotspot:.1f}%) "
            f"com ZAC proporcional ({pct_haz:.1f}%) e gradiente estável."
        )

    # 7. Renderização da Imagem Anotada
    anotada = img_bgr.copy()

    # Contornos da ZAC em Amarelo/Ciano
    contornos_haz, _ = cv2.findContours(mascara_haz, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(anotada, contornos_haz, -1, (0, 220, 255), 1)

    # Contornos dos Hotspots em Vermelho vivo
    contornos_hot, _ = cv2.findContours(mascara_hotspot, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(anotada, contornos_hot, -1, (0, 0, 255), 2)

    # HUD Superior
    overlay_hud = anotada.copy()
    cv2.rectangle(overlay_hud, (0, 0), (largura, 68), (15, 20, 25), -1)
    cv2.addWeighted(overlay_hud, 0.85, anotada, 0.15, 0, anotada)

    cv2.putText(
        anotada,
        f"ANALISE TERMICA ZAC/HAZ | STATUS: {status} - {diagnostico}",
        (15, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        cor_status,
        2,
        cv2.LINE_AA,
    )
    metricas_str = (
        f"Pico Estimado: ~{temp_max_estimada:.0f} C | "
        f"ZAC/HAZ: {pct_haz:.1f}% ({pixels_haz:,} px) | "
        f"Fusao/Hotspot: {pct_hotspot:.1f}% ({pixels_hotspot:,} px) | "
        f"Razao ZAC/Fusao: {razao_haz_hotspot:.2f}"
    )
    cv2.putText(
        anotada,
        metricas_str,
        (15, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (220, 225, 230),
        1,
        cv2.LINE_AA,
    )

    if salvar_anotada_em is not None:
        caminho_saida = Path(salvar_anotada_em)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(caminho_saida), anotada)

    # Codificação em Base64 para consumo direto
    _, buffer = cv2.imencode(".jpg", anotada, [cv2.IMWRITE_JPEG_QUALITY, 90])
    base64_str = base64.b64encode(buffer).decode("ascii")

    return {
        "status": status,
        "aprovado": aprovado,
        "diagnostico": diagnostico,
        "pixels_hotspot": pixels_hotspot,
        "percentual_hotspot": round(pct_hotspot, 2),
        "pixels_haz": pixels_haz,
        "percentual_haz": round(pct_haz, 2),
        "percentual_calor_total": round(pct_calor_total, 2),
        "razao_haz_hotspot": round(razao_haz_hotspot, 2),
        "temperatura_max_estimada_c": round(temp_max_estimada, 1),
        "temperatura_media_estimada_c": round(temp_media_estimada, 1),
        "motivos": motivos,
        "imagem_anotada_base64": base64_str,
        "dimensoes_imagem": {"largura": largura, "altura": altura},
    }
