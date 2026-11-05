"""Leitura, validação e extração de descritores visuais HOG e cor."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


IMAGE_SIZE = (128, 128)
FEATURE_VERSION = "hog_rgb_hist_v1"


def load_rgb_image(image_path: str | Path, image_size: tuple[int, int] = IMAGE_SIZE) -> np.ndarray:
    """Abre a imagem e devolve RGB uint8 redimensionado sem sobrescrever a origem."""
    caminho = Path(image_path)
    if not caminho.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {caminho}")
    imagem = cv2.imread(str(caminho), cv2.IMREAD_UNCHANGED)
    if imagem is None or imagem.size == 0:
        raise ValueError(f"Imagem inválida ou ilegível: {caminho}")
    if imagem.dtype != np.uint8:
        raise ValueError(f"Formato de pixel não suportado em {caminho}: {imagem.dtype}; esperado uint8.")
    if imagem.ndim == 2:
        rgb = cv2.cvtColor(imagem, cv2.COLOR_GRAY2RGB)
    elif imagem.ndim == 3 and imagem.shape[2] == 3:
        rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
    elif imagem.ndim == 3 and imagem.shape[2] == 4:
        rgb = cv2.cvtColor(imagem, cv2.COLOR_BGRA2RGB)
    else:
        raise ValueError(f"Número de canais incompatível em {caminho}: shape={imagem.shape}.")
    if rgb.shape[0] < 1 or rgb.shape[1] < 1 or not np.isfinite(rgb).all():
        raise ValueError(f"Dimensões ou valores de pixel inválidos em {caminho}.")
    largura, altura = image_size
    if largura <= 0 or altura <= 0:
        raise ValueError("O tamanho de entrada deve ter dimensões positivas.")
    interpolacao = cv2.INTER_AREA if rgb.shape[1] > largura or rgb.shape[0] > altura else cv2.INTER_LINEAR
    return cv2.resize(rgb, (largura, altura), interpolation=interpolacao)


def extract_features(image_path: str | Path, image_size: tuple[int, int] = IMAGE_SIZE) -> np.ndarray:
    """Extrai HOG, histogramas RGB e médias espaciais em um vetor determinístico."""
    rgb = load_rgb_image(image_path, image_size)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # HOG explícito: histograma de orientação por célula 8x8, blocos 2x2
    # normalizados. Implementação própria evita dependência de APIs HOG opcionais.
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude, angulo = cv2.cartToPolar(grad_x, grad_y, angleInDegrees=True)
    angulo = np.mod(angulo, 180.0)
    altura, largura = gray.shape
    celula = 8
    bins = 9
    grade_y, grade_x = altura // celula, largura // celula
    hist_celulas = np.zeros((grade_y, grade_x, bins), dtype=np.float32)
    for linha in range(grade_y):
        for coluna in range(grade_x):
            y0, x0 = linha * celula, coluna * celula
            magnitudes = magnitude[y0:y0+celula, x0:x0+celula].reshape(-1)
            angulos = angulo[y0:y0+celula, x0:x0+celula].reshape(-1)
            hist_celulas[linha, coluna], _ = np.histogram(angulos, bins=bins, range=(0, 180), weights=magnitudes)
    blocos = []
    for linha in range(grade_y - 1):
        for coluna in range(grade_x - 1):
            bloco = hist_celulas[linha:linha+2, coluna:coluna+2].reshape(-1)
            blocos.append(bloco / np.sqrt(float(np.dot(bloco, bloco)) + 1e-6))
    hog = np.concatenate(blocos)
    histogramas = []
    for canal in range(3):
        hist = cv2.calcHist([rgb], [canal], None, [16], [0, 256]).reshape(-1)
        hist = hist / max(float(hist.sum()), 1.0)
        histogramas.append(hist)
    # Médias em uma grade 4x4 preservam informação grosseira de posição.
    medias_espaciais = cv2.resize(rgb.astype(np.float32), (4, 4), interpolation=cv2.INTER_AREA).reshape(-1) / 255.0
    descritores = np.concatenate([hog.astype(np.float32), *histogramas, medias_espaciais]).astype(np.float32)
    if not np.isfinite(descritores).all():
        raise ValueError(f"Descritores inválidos calculados para {image_path}.")
    return descritores


def augment_image(image: np.ndarray, angle_degrees: float = 3.0, brightness_delta: float = 0.04) -> np.ndarray:
    """Gera uma variação moderada para uso futuro, sem ser usada no dataset inicial."""
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("Aumento espera imagem RGB uint8 com três canais.")
    if abs(angle_degrees) > 5 or not 0 <= brightness_delta <= 0.08:
        raise ValueError("Aumento limitado a rotação de até 5° e brilho até 0,08.")
    altura, largura = image.shape[:2]
    centro = (largura / 2, altura / 2)
    matriz = cv2.getRotationMatrix2D(centro, float(angle_degrees), 1.0)
    rodada = cv2.warpAffine(image, matriz, (largura, altura), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    return np.clip(rodada.astype(np.float32) * (1.0 + brightness_delta), 0, 255).astype(np.uint8)

