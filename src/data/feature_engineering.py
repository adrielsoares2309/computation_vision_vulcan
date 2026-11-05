"""Módulo de Engenharia de Features Dinâmicas Industriais por Lote e Liga Metálica.

Atende rigorosamente aos requisitos da Etapa 1 do Projeto Integrador:
- Índice de Esforço Mecânico (IEM)
- Janelas móveis de 30 min (6 amostras) e 2 horas (24 amostras) por equipamento
- Normalização condicional dividida pela média histórica da respectiva liga metálica
- Z-Score condicional por liga metálica para prevenção de falsos alarmes
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .validator import SENSOR_SPECS

SENSORES_NUMERICOS = list(SENSOR_SPECS.keys())


def calcular_iem(df: pd.DataFrame) -> pd.Series:
    """Calcula o Índice de Esforço Mecânico (IEM).

    Fórmula oficial:
    IEM = (Torque_Fuso_Nm * Vibracao_Triaxial_RMS_mms) / (Vazao_Refrigerante_lmin + 1)
    """
    torque = pd.to_numeric(df["torque_fuso_nm"], errors="coerce").fillna(0.0)
    vibracao = pd.to_numeric(df["vibracao_triaxial_rms_mms"], errors="coerce").fillna(0.0)
    vazao = pd.to_numeric(df["vazao_refrigerante_lmin"], errors="coerce").fillna(0.0)
    vazao_segura = np.maximum(vazao, 0.0)
    iem = (torque * vibracao) / (vazao_segura + 1.0)
    return iem.round(4)


def adicionar_rolling_features(
    df: pd.DataFrame,
    colunas: list[str] | None = None,
    janelas: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Calcula médias e desvios móveis (Rolling Mean e Rolling Std) por equipamento (id_celula).

    Intervalo de amostragem: 5 minutos.
    - Janela de 30 min: 6 períodos.
    - Janela de 2 horas: 24 períodos.
    """
    df_out = df.copy()
    if colunas is None:
        colunas = ["temperatura_fuso_c", "vibracao_triaxial_rms_mms", "torque_fuso_nm", "corrente_estator_amp"]
    if janelas is None:
        janelas = {"30m": 6, "2h": 24}

    # Assegura ordenação cronológica por equipamento
    if "timestamp" in df_out.columns:
        df_out = df_out.sort_values(["id_celula", "timestamp"]).reset_index(drop=True)

    for nome_janela, window_size in janelas.items():
        for col in colunas:
            if col in df_out.columns:
                grouped = df_out.groupby("id_celula")[col]
                # Rolling Mean com min_periods=1 para não introduzir NaNs no início
                df_out[f"{col}_rolling_mean_{nome_janela}"] = (
                    grouped.rolling(window=window_size, min_periods=1)
                    .mean()
                    .reset_index(level=0, drop=True)
                    .round(4)
                )
                # Rolling Std com min_periods=1 (preenchendo primeiro ponto com 0.0)
                df_out[f"{col}_rolling_std_{nome_janela}"] = (
                    grouped.rolling(window=window_size, min_periods=1)
                    .std()
                    .reset_index(level=0, drop=True)
                    .fillna(0.0)
                    .round(4)
                )
    return df_out


def normalizar_por_liga(df: pd.DataFrame, colunas: list[str] | None = None) -> pd.DataFrame:
    """Normaliza as variáveis de processo dividindo-as pela média histórica da respectiva liga_metalica.

    Elimina falsos alarmes em materiais de alta dureza (ex: Liga de Titânio Ti6Al4V vs Alumínio 7075).
    """
    df_out = df.copy()
    if colunas is None:
        colunas = ["torque_fuso_nm", "corrente_estator_amp", "temperatura_fuso_c", "vibracao_triaxial_rms_mms"]

    for col in colunas:
        if col in df_out.columns and "liga_metalica" in df_out.columns:
            medias_liga = df_out.groupby("liga_metalica")[col].transform("mean")
            medias_liga = np.where(medias_liga == 0, 1.0, medias_liga)
            df_out[f"{col}_norm_liga"] = (df_out[col] / medias_liga).round(4)

    return df_out


def calcular_zscore_condicional(df: pd.DataFrame, colunas: list[str] | None = None) -> pd.DataFrame:
    """Calcula Z-Score condicional por liga metálica: (X - mu_liga) / sigma_liga."""
    df_out = df.copy()
    if colunas is None:
        colunas = ["torque_fuso_nm", "corrente_estator_amp", "temperatura_fuso_c", "vibracao_triaxial_rms_mms"]

    for col in colunas:
        if col in df_out.columns and "liga_metalica" in df_out.columns:
            mean = df_out.groupby("liga_metalica")[col].transform("mean")
            std = df_out.groupby("liga_metalica")[col].transform("std").replace(0, 1.0).fillna(1.0)
            df_out[f"{col}_zscore_liga"] = ((df_out[col] - mean) / std).round(4)

    return df_out


def enriquecer_features_industriais(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica o pipeline completo de Feature Engineering Industrial."""
    df_res = df.copy()
    df_res["indice_esforco_mecanico"] = calcular_iem(df_res)
    df_res = adicionar_rolling_features(df_res)
    df_res = normalizar_por_liga(df_res)
    df_res = calcular_zscore_condicional(df_res)
    return df_res

