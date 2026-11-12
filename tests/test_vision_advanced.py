"""Testes para os módulos avançados de visão computacional (Filtros OpenCV/AeroMotion, Porosidade e HSV/HAZ)."""

from pathlib import Path
import cv2
import numpy as np
import pytest

from src.vision.thermal_analysis import analisar_termografia_solda
from src.vision.weld_inspection import inspecionar_solda
from vision.geometry import analyze_geometry, classify_geometry_against_references

RAIZ = Path(__file__).resolve().parents[1]
IMG_DIR = RAIZ / "data" / "raw" / "imagens"


def test_inspecao_solda_geometrica_aprovada_path_e_memoria():
    caminho = IMG_DIR / "solda_aprovada.png"
    assert caminho.is_file()
    img_bgr = cv2.imread(str(caminho), cv2.IMREAD_COLOR)

    # Testa passando matriz em memória (sem nome de arquivo) e com todos os artefatos de filtros
    resultado = inspecionar_solda(img_bgr, incluir_artefatos_filtros=True)
    assert resultado["status"] == "APROVADO"
    assert resultado["aprovado"] is True
    assert resultado["contagem_poros"] == 0
    assert resultado["porosidade_percentual"] == 0.0
    assert resultado["coerencia_escamas"] >= 0.70
    assert resultado["variacao_largura_percentual"] < 5.0
    assert resultado["descontinuidades_detectadas"] == 0
    assert "imagem_anotada_base64" in resultado
    assert len(resultado["imagem_anotada_base64"]) > 100
    assert {
        "cinza",
        "clahe",
        "sobel_mag",
        "bordas_canny",
        "mascara_cordao",
        "coerencia_color",
        "blackhat",
        "mascara_poros",
        "silhueta_normalizada",
        "contornos_aero_bgr",
        "anotada_bgr",
    }.issubset(resultado["artefatos"])


def test_inspecao_solda_geometrica_reprovada_path_e_memoria():
    caminho = IMG_DIR / "solda_reprovada.png"
    assert caminho.is_file()
    img_bgr = cv2.imread(str(caminho), cv2.IMREAD_COLOR)

    # Testa passando matriz BGR em memória (garantindo que a reprovação vem 100% dos filtros OpenCV)
    resultado = inspecionar_solda(img_bgr, incluir_artefatos_filtros=True)
    assert resultado["status"] == "REPROVADO"
    assert resultado["aprovado"] is False
    assert resultado["contagem_poros"] > 50
    assert resultado["porosidade_percentual"] >= 3.0
    assert resultado["coerencia_escamas"] < 0.45
    assert resultado["variacao_largura_percentual"] >= 10.0
    assert resultado["descontinuidades_detectadas"] >= 10
    assert len(resultado["motivos"]) >= 3


def test_comparacao_referencias_aeromotion_iou_e_morfologia():
    ref_ok = cv2.imread(str(IMG_DIR / "solda_aprovada.png"), cv2.IMREAD_COLOR)
    ref_bad = cv2.imread(str(IMG_DIR / "solda_reprovada.png"), cv2.IMREAD_COLOR)

    res_ok = classify_geometry_against_references(ref_ok, ref_ok, ref_bad)
    assert res_ok["status"] == "APROVADA"
    assert res_ok["classification"] == "DENTRO DOS CONFORMES"
    assert res_ok["metrics"]["normal_reference_iou"] > res_ok["metrics"]["defective_reference_iou"]

    res_bad = classify_geometry_against_references(ref_bad, ref_ok, ref_bad)
    assert res_bad["status"] == "REPROVADA"
    assert res_bad["classification"] == "REPROVADA"
    assert res_bad["metrics"]["defective_reference_iou"] > res_bad["metrics"]["normal_reference_iou"]


def test_analise_termografia_aprovada():
    caminho = IMG_DIR / "termica_solda_aprovada.png"
    assert caminho.is_file()
    resultado = analisar_termografia_solda(caminho)
    assert resultado["status"] == "APROVADO"
    assert resultado["aprovado"] is True
    assert resultado["pixels_hotspot"] > 25000
    assert resultado["percentual_haz"] > 0
    assert "imagem_anotada_base64" in resultado


def test_analise_termografia_reprovada():
    caminho = IMG_DIR / "termica_solda_reprovada.png"
    assert caminho.is_file()
    resultado = analisar_termografia_solda(caminho)
    assert resultado["status"] == "REPROVADO"
    assert resultado["aprovado"] is False
    assert "FALTA DE FUSAO" in resultado["diagnostico"] or "SUBAQUECIMENTO" in resultado["diagnostico"]
