"""Testes unitários e de integração para o pipeline de dados e engenharia de atributos."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data.feature_engineering import (
    adicionar_rolling_features,
    calcular_iem,
    calcular_zscore_condicional,
    enriquecer_features_industriais,
    normalizar_por_liga,
)
from src.data.pipeline import sanitizar_dataframe_bruto

RAIZ = Path(__file__).resolve().parents[1]
RAW_CSV = RAIZ / "data" / "raw" / "dados_sensores_vulcantech.csv"
FEATURES_PARQUET = RAIZ / "data" / "processed" / "dados_sensores_vulcantech_features.parquet"


def test_calculo_iem():
    df = pd.DataFrame({
        "torque_fuso_nm": [100.0, 150.0],
        "vibracao_triaxial_rms_mms": [2.0, 4.0],
        "vazao_refrigerante_lmin": [19.0, 29.0],
    })
    resultado = calcular_iem(df)
    assert isinstance(resultado, pd.Series)
    # (100 * 2) / (19 + 1) = 200 / 20 = 10.0
    assert pytest.approx(resultado.iloc[0], 0.01) == 10.0
    # (150 * 4) / (29 + 1) = 600 / 30 = 20.0
    assert pytest.approx(resultado.iloc[1], 0.01) == 20.0


def test_pipeline_sanitizacao_remove_sentinelas():
    df_raw = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=5, freq="5min"),
        "id_celula": ["CEL-201"] * 5,
        "liga_metalica": ["Aco_Carbono_316L"] * 5,
        "temperatura_fuso_c": [50.0, 999.9, 52.0, 53.0, 51.0],  # 999.9 é sentinela
        "vibracao_triaxial_rms_mms": [1.5, 1.6, -99.0, 1.8, 1.7],  # -99.0 é sentinela
        "torque_fuso_nm": [100.0, 105.0, 102.0, 104.0, 103.0],
        "vazao_refrigerante_lmin": [25.0, 26.0, 25.5, 27.0, 26.0],
        "corrente_estator_amp": [28.0, 29.0, 28.5, 28.8, 29.2],
        "pressao_hidraulica_bar": [160.0, 162.0, 159.0, -1.0, 161.0],  # -1.0 é sentinela
        "nivel_ruido_db": [55.0, 56.0, 55.5, 57.0, 56.5],
        "tipo_falha": [0, 0, 0, 0, 0],
    })
    df_clean, total_sentinelas = sanitizar_dataframe_bruto(df_raw)
    assert 999.9 not in df_clean["temperatura_fuso_c"].dropna().values
    assert -99.0 not in df_clean["vibracao_triaxial_rms_mms"].dropna().values
    assert -1.0 not in df_clean["pressao_hidraulica_bar"].dropna().values
    assert total_sentinelas == 3


def test_parquet_features_persistido():
    assert FEATURES_PARQUET.is_file(), "Arquivo de features tratadas não foi encontrado."
    df = pd.read_parquet(FEATURES_PARQUET)
    assert len(df) == 10_000
    assert "indice_esforco_mecanico" in df.columns
    assert "temperatura_fuso_c_rolling_mean_30m" in df.columns
    assert "vibracao_triaxial_rms_mms_rolling_mean_2h" in df.columns
    assert "torque_fuso_nm_zscore_liga" in df.columns
    assert df.isna().sum().sum() == 0, "O dataset processado não deve conter valores NaN."
