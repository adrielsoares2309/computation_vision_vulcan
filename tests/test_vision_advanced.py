"""Testes para os módulos avançados de visão computacional (Canny/Porosidade e HSV/HAZ)."""

from pathlib import Path
import numpy as np
import pytest

from src.vision.thermal_analysis import analisar_termografia_solda
from src.vision.weld_inspection import inspecionar_solda

RAIZ = Path(__file__).resolve().parents[1]
IMG_DIR = RAIZ / "data" / "raw" / "imagens"


def test_inspecao_solda_geometrica_aprovada():
    caminho = IMG_DIR / "solda_aprovada.png"
    assert caminho.is_file()
    resultado = inspecionar_solda(caminho)
    assert resultado["status"] == "APROVADO"
    assert resultado["aprovado"] is True
    assert resultado["porosidade_percentual"] < 3.0
    assert "imagem_anotada_base64" in resultado
    assert len(resultado["imagem_anotada_base64"]) > 100


def test_inspecao_solda_geometrica_reprovada():
    caminho = IMG_DIR / "solda_reprovada.png"
    assert caminho.is_file()
    resultado = inspecionar_solda(caminho)
    assert resultado["status"] == "REPROVADO"
    assert resultado["aprovado"] is False
    assert len(resultado["motivos"]) > 0


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

