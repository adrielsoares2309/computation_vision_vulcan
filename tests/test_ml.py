"""Testes de contrato para os artefatos do pipeline de ML VulcanTech."""

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.ml.predict import CAMINHO_MODELO, prever
from src.ml.train import carregar_dataset, dividir_cronologicamente, identificar_alvo


RAIZ = Path(__file__).resolve().parents[1]


def test_dataset_tratado_e_alvo_documentado():
    dados, origem = carregar_dataset()
    assert origem.suffix == ".parquet"
    assert dados.shape[0] == 10_000
    assert dados.shape[1] >= 11
    assert identificar_alvo(dados) == "tipo_falha"
    assert set(dados.tipo_falha.unique()) == {0, 1, 2, 3}


def test_divisao_temporal_sem_intersecao():
    dados, _ = carregar_dataset()
    treino, validacao, teste, _ = dividir_cronologicamente(dados)
    assert len(treino) + len(validacao) + len(teste) == len(dados)
    assert set(treino).isdisjoint(validacao)
    assert set(treino).isdisjoint(teste)
    assert set(validacao).isdisjoint(teste)
    datas = dados.timestamp
    assert datas.iloc[treino].max() < datas.iloc[validacao].min()
    assert datas.iloc[validacao].max() < datas.iloc[teste].min()


def test_pipeline_persistido_nao_recebe_alvo_ou_timestamp():
    assert CAMINHO_MODELO.is_file()
    modelo = joblib.load(CAMINHO_MODELO)
    assert "tipo_falha" not in modelo.feature_names_in_
    assert "timestamp" not in modelo.feature_names_in_
    assert len(modelo.feature_names_in_) >= 9


def test_previsao_tem_tamanho_e_probabilidades_validas():
    dados, _ = carregar_dataset()
    modelo = joblib.load(CAMINHO_MODELO)
    entrada = dados.loc[:11, list(modelo.feature_names_in_)]
    resultado = prever(entrada, modelo=modelo)
    assert len(resultado) == len(entrada)
    assert "tipo_falha_previsto" in resultado
    colunas_prob = [c for c in resultado if c.startswith("probabilidade_classe_")]
    assert len(colunas_prob) == 4
    assert (resultado[colunas_prob].sum(axis=1).sub(1).abs() < 1e-8).all()


def test_previsao_rejeita_colunas_obrigatorias_ausentes():
    modelo = joblib.load(CAMINHO_MODELO)
    entrada = pd.DataFrame({"liga_metalica": ["Aco_Carbono_316L"]})
    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        prever(entrada, modelo=modelo)


def test_metadados_e_relatorios_foram_gerados():
    metadados = json.loads((RAIZ / "models/tabular/model_metadata.json").read_text(encoding="utf-8"))
    assert metadados["target"] == "tipo_falha"
    assert metadados["split_counts"] == {"train": 7000, "validation": 1500, "test": 1500}
    assert "recall_falhas_macro" in metadados["test_metrics"]
    assert (RAIZ / "reports/ml/model_comparison.csv").is_file()
    assert (RAIZ / "reports/ml/classification_report.json").is_file()
    assert (RAIZ / "reports/ml/confusion_matrix.csv").is_file()
    assert (RAIZ / "reports/ml/training_summary.md").is_file()
