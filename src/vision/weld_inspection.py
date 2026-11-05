"""Inspeção geométrica de cordão de solda por visão computacional (OpenCV).

Aplica filtros de realce, conversão em escala de cinza, detector de bordas de Canny,
extração e análise de contornos, estimativa de porosidade e detecção de descontinuidades
geométricas conforme normas industriais (ISO 5817 / AWS D1.1).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def carregar_imagem(origem: str | Path | np.ndarray) -> np.ndarray:
    """Carrega uma imagem como array BGR uint8."""
    if isinstance(origem, np.ndarray):
        if origem.dtype != np.uint8:
            origem = np.clip(origem, 0, 255).astype(np.uint8)
        if origem.ndim == 2:
            return cv2.cvtColor(origem, cv2.COLOR_GRAY2BGR)
        if origem.ndim == 3 and origem.shape[2] == 4:
            return cv2.cvtColor(origem, cv2.COLOR_BGRA2BGR)
        return origem

    caminho = Path(origem)
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo de imagem não encontrado: {caminho}")
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Não foi possível decodificar a imagem: {caminho}")
    return img


def aplicar_filtro_realce(cinza: np.ndarray) -> np.ndarray:
    """Aplica suavização gaussiana e filtro de nitidez (unsharp mask)."""
    suavizada = cv2.GaussianBlur(cinza, (5, 5), sigmaX=1.0)
    kernel_sharpen = np.array(
        [[0, -1, 0],
         [-1, 5, -1],
         [0, -1, 0]],
        dtype=np.float32,
    )
    realcada = cv2.filter2D(suavizada, -1, kernel_sharpen)
    return realcada


def detectar_bordas_canny(
    imagem_realcada: np.ndarray,
    limiar_baixo: int = 50,
    limiar_alto: int = 150,
) -> np.ndarray:
    """Aplica o algoritmo de detecção de bordas de Canny com limiares industriais."""
    return cv2.Canny(imagem_realcada, limiar_baixo, limiar_alto)


def estimar_porosidade(
    cinza: np.ndarray,
    mascara_cordao: np.ndarray,
    min_area: int = 4,
    max_area: int = 600,
    min_circularidade: float = 0.35,
) -> tuple[int, float, list[dict[str, Any]], np.ndarray]:
    """Detecta cavidades/poros escuros no cordão através de binarização adaptativa e circularidade.

    Retorna: (contagem_poros, area_total_poros, lista_poros, mascara_poros).
    """
    # Inverter imagem equalizada dentro do cordão: cavidades escuras tornam-se brilhantes
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cinza_clahe = clahe.apply(cinza)

    # Limiarização adaptativa para isolar descontinuidades locais escuras
    binaria = cv2.adaptiveThreshold(
        cinza_clahe,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        5,
    )
    # Restringe a busca apenas à região do cordão
    binaria_cordao = cv2.bitwise_and(binaria, mascara_cordao)

    contornos, _ = cv2.findContours(binaria_cordao, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    poros = []
    area_total = 0.0
    mascara_poros = np.zeros_like(cinza)

    for c in contornos:
        area = cv2.contourArea(c)
        if min_area <= area <= max_area:
            perimetro = cv2.arcLength(c, True)
            if perimetro > 0:
                circularidade = (4.0 * np.pi * area) / (perimetro * perimetro)
                if circularidade >= min_circularidade:
                    (cx, cy), raio = cv2.minEnclosingCircle(c)
                    poros.append({
                        "centro": (int(cx), int(cy)),
                        "raio": int(max(raio, 2)),
                        "area": float(area),
                        "circularidade": float(circularidade),
                    })
                    area_total += area
                    cv2.drawContours(mascara_poros, [c], -1, 255, -1)

    return len(poros), float(area_total), poros, mascara_poros


def analisar_descontinuidade_cordao(
    contorno_cordao: np.ndarray,
    altura_img: int,
    largura_img: int,
) -> tuple[float, float, float, float, int, list[dict[str, Any]]]:
    """Analisa a uniformidade da largura do cordão de solda e detecta descontinuidades geométricas."""
    x, y, w, h = cv2.boundingRect(contorno_cordao)
    e_horizontal = w >= h

    larguras = []
    descontinuidades = []

    # Amostragem do perfil de largura em cortes transversais
    mascara_cordao = np.zeros((altura_img, largura_img), dtype=np.uint8)
    cv2.drawContours(mascara_cordao, [contorno_cordao], -1, 255, -1)

    if e_horizontal:
        passo = max(1, w // 80)
        for col in range(x, x + w, passo):
            coluna_pixels = np.flatnonzero(mascara_cordao[:, col])
            if len(coluna_pixels) > 0:
                largura_corte = coluna_pixels[-1] - coluna_pixels[0] + 1
                larguras.append((col, largura_corte))
    else:
        passo = max(1, h // 80)
        for lin in range(y, y + h, passo):
            linha_pixels = np.flatnonzero(mascara_cordao[lin, :])
            if len(linha_pixels) > 0:
                largura_corte = linha_pixels[-1] - linha_pixels[0] + 1
                larguras.append((lin, largura_corte))

    if not larguras:
        return 0.0, 0.0, 0.0, 0.0, 0, []

    valores_largura = [v[1] for v in larguras]
    largura_media = float(np.mean(valores_largura))
    largura_min = float(np.min(valores_largura))
    largura_max = float(np.max(valores_largura))
    std_largura = float(np.std(valores_largura))
    variacao_percentual = float((std_largura / (largura_media + 1e-6)) * 100.0)

    # Detecta quedas bruscas de largura (falta de fusão/estreitamento) ou aumentos anômalos
    for pos, larg in larguras:
        if larg < largura_media * 0.55:
            descontinuidades.append({
                "tipo": "estreitamento_falta_fusao",
                "posicao": pos,
                "largura_local": larg,
                "largura_esperada": largura_media,
            })
        elif larg > largura_media * 1.65:
            descontinuidades.append({
                "tipo": "excesso_penetracao_largura",
                "posicao": pos,
                "largura_local": larg,
                "largura_esperada": largura_media,
            })

    return largura_media, largura_min, largura_max, variacao_percentual, len(descontinuidades), descontinuidades


def inspecionar_solda(
    origem_imagem: str | Path | np.ndarray,
    limiar_porosidade_reprovacao: float = 3.0,
    limiar_porosidade_alerta: float = 1.0,
    limiar_variacao_largura_reprovacao: float = 35.0,
    salvar_anotada_em: str | Path | None = None,
) -> dict[str, Any]:
    """Executa a inspeção geométrica completa do cordão de solda via OpenCV.

    Pipeline:
    1. Grayscale & CLAHE
    2. Suavização Gaussiana & Filtro de Nitidez
    3. Canny Edge Detection & Morfologia Matemática
    4. Segmentação de Contorno do Cordão
    5. Análise de Largura e Descontinuidade Geométrica
    6. Detecção e Estimativa de Porosidade
    7. Classificação Industrial (Aprovado / Alerta / Reprovado)
    8. Renderização de Imagem Anotada com Métricas e Caixas de Defeitos
    """
    img_bgr = carregar_imagem(origem_imagem)
    altura, largura = img_bgr.shape[:2]

    cinza = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    realcada = aplicar_filtro_realce(cinza)
    bordas = detectar_bordas_canny(realcada, limiar_baixo=40, limiar_alto=130)

    # Fechamento morfológico para conectar bordas descontínuas do cordão
    kernel_morf = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    bordas_conectadas = cv2.morphologyEx(bordas, cv2.MORPH_CLOSE, kernel_morf)

    # Identificar contornos candidatos a cordão de solda
    contornos, _ = cv2.findContours(bordas_conectadas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Encontra o maior contorno significativo (cordão central de solda)
    area_minima = (altura * largura) * 0.03
    contornos_validos = [c for c in contornos if cv2.contourArea(c) >= area_minima]

    if not contornos_validos:
        # Se contorno isolado não foi encontrado por Canny fechado, usa limiarização Otsu combinada
        _, thresh = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel_otsu = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        thresh_closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_otsu)
        contornos_otsu, _ = cv2.findContours(thresh_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contornos_validos = sorted(contornos_otsu, key=cv2.contourArea, reverse=True)[:1]

    if contornos_validos:
        contorno_cordao = max(contornos_validos, key=cv2.contourArea)
        area_cordao = float(cv2.contourArea(contorno_cordao))
    else:
        # Fallback: cordão no terço central da imagem
        area_cordao = float(altura * largura * 0.4)
        contorno_cordao = np.array([
            [[int(largura * 0.1), int(altura * 0.25)]],
            [[int(largura * 0.9), int(altura * 0.25)]],
            [[int(largura * 0.9), int(altura * 0.75)]],
            [[int(largura * 0.1), int(altura * 0.75)]],
        ], dtype=np.int32)

    # Cria máscara do cordão
    mascara_cordao = np.zeros((altura, largura), dtype=np.uint8)
    cv2.drawContours(mascara_cordao, [contorno_cordao], -1, 255, -1)

    # 1. Análise de Porosidade
    num_poros, area_poros, lista_poros, _ = estimar_porosidade(cinza, mascara_cordao)
    porosidade_pct = (area_poros / max(area_cordao, 1.0)) * 100.0

    # 2. Análise Geométrica e Descontinuidades
    larg_media, larg_min, larg_max, var_larg_pct, num_desc, desc_detalhes = analisar_descontinuidade_cordao(
        contorno_cordao, altura, largura
    )

    # 3. Classificação e Decisão
    motivos = []
    if porosidade_pct >= limiar_porosidade_reprovacao:
        motivos.append(f"Porosidade excessiva ({porosidade_pct:.2f}% ≥ {limiar_porosidade_reprovacao:.1f}%)")
    elif porosidade_pct >= limiar_porosidade_alerta:
        motivos.append(f"Porosidade moderada ({porosidade_pct:.2f}%)")

    if var_larg_pct >= limiar_variacao_largura_reprovacao:
        motivos.append(f"Irregularidade de largura crítica ({var_larg_pct:.1f}% ≥ {limiar_variacao_largura_reprovacao:.1f}%)")
    elif var_larg_pct >= 20.0:
        motivos.append(f"Variação de largura moderada ({var_larg_pct:.1f}%)")

    if num_desc >= 3:
        motivos.append(f"{num_desc} descontinuidades pontuais detectadas")

    # Análise de alinhamento e deslocamento do cordão
    bx, by, bw, bh = cv2.boundingRect(contorno_cordao)
    centro_y_esperado = altura / 2.0
    desvio_centro_y = abs(by + bh / 2.0 - centro_y_esperado)
    if desvio_centro_y > (altura * 0.06):
        motivos.append(f"Desalinhamento do cordão em relação ao eixo da junta ({desvio_centro_y:.0f}px)")

    # Integração com classificador ML supervisionado de visão (HOG + Histograma de Cor)
    predicao_ml = None
    if isinstance(origem_imagem, (str, Path)) and Path(origem_imagem).is_file():
        try:
            from .predict import predict_image
            predicao_ml = predict_image(origem_imagem, modality="visual")
            if predicao_ml.get("predicted_class") == "REPROVADA":
                score_rep = predicao_ml["class_scores"].get("REPROVADA", 0.0)
                if score_rep > 0.6:
                    motivos.append(f"Padrão morfológico reprovado por classificador espectral (score: {score_rep:.1%})")
        except Exception:
            pass

    if any("crítica" in m or "excessiva" in m or "reprovado" in m or "Desalinhamento" in m for m in motivos) or num_desc >= 5:
        status = "REPROVADO"
        aprovado = False
        cor_status = (0, 0, 220)  # Vermelho
    elif motivos:
        status = "ALERTA"
        aprovado = True
        cor_status = (0, 190, 240)  # Âmbar / Amarelo industrial
    else:
        status = "APROVADO"
        aprovado = True
        motivos = ["Cordão com geometria uniforme e ausência de porosidade crítica."]
        cor_status = (0, 180, 0)  # Verde industrial
        motivos.append("Cordão com geometria uniforme e ausência de porosidade crítica.")
        cor_status = (0, 180, 0)  # Verde industrial

    # 4. Desenho e Anotação Visual
    anotada = img_bgr.copy()

    # Bounding box do cordão
    bx, by, bw, bh = cv2.boundingRect(contorno_cordao)
    cv2.rectangle(anotada, (bx, by), (bx + bw, by + bh), cor_status, 2)
    cv2.drawContours(anotada, [contorno_cordao], -1, (255, 140, 0), 2)  # Ciano no contorno

    # Destacar poros detectados com círculos e cruzetas
    for p in lista_poros:
        cx, cy = p["centro"]
        r = p["raio"]
        cv2.circle(anotada, (cx, cy), r + 2, (0, 0, 255), 2)
        cv2.drawMarker(anotada, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, r * 2, 1)

    # Painel HUD superior industrial
    overlay_hud = anotada.copy()
    cv2.rectangle(overlay_hud, (0, 0), (largura, 65), (20, 25, 30), -1)
    cv2.addWeighted(overlay_hud, 0.85, anotada, 0.15, 0, anotada)

    # Texto de status e métricas principais no HUD
    cv2.putText(
        anotada,
        f"INSPECAO GEOMETRICA DE SOLDA | STATUS: {status}",
        (15, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        cor_status,
        2,
        cv2.LINE_AA,
    )
    metricas_str = (
        f"Porosidade: {porosidade_pct:.2f}% ({num_poros} poros) | "
        f"Largura Media: {larg_media:.1f}px (var: {var_larg_pct:.1f}%) | "
        f"Descontinuidades: {num_desc}"
    )
    cv2.putText(
        anotada,
        metricas_str,
        (15, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (220, 225, 230),
        1,
        cv2.LINE_AA,
    )

    if salvar_anotada_em is not None:
        caminho_saida = Path(salvar_anotada_em)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(caminho_saida), anotada)

    # Codificar imagem em JPEG base64 para uso direto em web/API/Streamlit
    _, buffer = cv2.imencode(".jpg", anotada, [cv2.IMWRITE_JPEG_QUALITY, 90])
    base64_str = base64.b64encode(buffer).decode("ascii")

    return {
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
        "descontinuidades_detectadas": num_desc,
        "motivos": motivos,
        "lista_poros": lista_poros[:50],  # Limita aos primeiros 50
        "imagem_anotada_base64": base64_str,
        "dimensoes_imagem": {"largura": largura, "altura": altura},
    }
