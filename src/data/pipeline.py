"""Pipeline End-to-End de Engenharia e Saneamento de Dados Industriais.

Executa:
1. Inspeção estrutural e quantificação de NaNs por célula e liga metálica.
2. Tratamento de ruído eletromagnético e sensores defeituosos (999.9 °C, -99.0 mm/s, -1.0 bar).
3. Interpolação temporal condicional por equipamento (id_celula).
4. Feature Engineering Industrial (IEM, Rolling Mean/Std 30m e 2h, Normalização e Z-Score condicional por liga).
5. Persistência dos dados tratados com rastreabilidade completa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cleaner import sanitize_sensor_reading
from .feature_engineering import enriquecer_features_industriais
from .validator import SENSOR_SPECS, VALID_ALLOYS, VALID_CELLS

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "dados_sensores_vulcantech.csv"
PROCESSED_PARQUET = ROOT / "data" / "processed" / "dados_sensores_vulcantech_features.parquet"
PROCESSED_CSV = ROOT / "data" / "processed" / "dados_sensores_vulcantech_features.csv"
METRICS_PATH = ROOT / "reports" / "ml" / "data_sanitization_report.json"


def inspecionar_taxas_ausencia(df: pd.DataFrame) -> dict[str, Any]:
    """Quantifica taxas de ausência de dados agrupadas por célula e por liga metálica."""
    total_linhas = len(df)
    nans_totais = df.isna().sum().to_dict()

    nans_por_celula: dict[str, dict[str, int]] = {}
    for celula, group in df.groupby("id_celula"):
        nans_por_celula[str(celula)] = group.isna().sum().to_dict()

    nans_por_liga: dict[str, dict[str, int]] = {}
    for liga, group in df.groupby("liga_metalica"):
        nans_por_liga[str(liga)] = group.isna().sum().to_dict()

    return {
        "total_registros": total_linhas,
        "nans_totais": {k: int(v) for k, v in nans_totais.items()},
        "nans_por_celula": nans_por_celula,
        "nans_por_liga": nans_por_liga,
    }


def sanitizar_dataframe_bruto(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Converte sentinelas de ruído (-99.0, 999.9, -1.0) em NaN para posterior interpolação."""
    df = df_raw.copy()
    sentinelas_tratados = 0

    for col, spec in SENSOR_SPECS.items():
        if col in df.columns:
            for s in spec["sentinels"]:
                mask = np.isclose(df[col].astype(float), s, atol=1e-3)
                cnt = int(mask.sum())
                if cnt > 0:
                    sentinelas_tratados += cnt
                    df.loc[mask, col] = np.nan

    return df, sentinelas_tratados


def interpolar_temporalmente_por_celula(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica interpolação temporal condicional por equipamento (id_celula).

    Garante que os registros estejam ordenados cronologicamente e que a interpolação
    não misture dados de células diferentes nem interpole variáveis categóricas ou a variável-alvo.
    """
    df_sorted = df.sort_values(["id_celula", "timestamp"]).copy()
    sensores = list(SENSOR_SPECS.keys())

    partes = []
    for celula, group in df_sorted.groupby("id_celula", sort=False):
        g = group.copy()
        # Interpolação linear temporal com limite de 6 passos (30 min)
        g[sensores] = g[sensores].interpolate(method="linear", limit=6, limit_direction="both")
        # Se restarem valores nas bordas, preenche com a mediana da respectiva célula
        for col in sensores:
            if g[col].isna().any():
                med = g[col].median()
                g[col] = g[col].fillna(med if pd.notna(med) else SENSOR_SPECS[col]["normal_min"])
        partes.append(g)

    df_interpolado = pd.concat(partes, ignore_index=True)
    return df_interpolado.sort_values("timestamp").reset_index(drop=True)


def executar_pipeline_completo(caminho_csv: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Executa todas as etapas da Engenharia de Dados Industriais."""
    caminho = caminho_csv or RAW_PATH
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo de dados brutos não encontrado: {caminho}")

    df_raw = pd.read_csv(caminho, parse_dates=["timestamp"])
    relatorio_ausencias = inspecionar_taxas_ausencia(df_raw)

    # 1. Limpeza de ruídos eletromagnéticos e sentinelas
    df_clean, sentinelas_qtd = sanitizar_dataframe_bruto(df_raw)

    # 2. Interpolação temporal condicional por equipamento
    df_interp = interpolar_temporalmente_por_celula(df_clean)

    # 3. Engenharia de Features Dinâmicas (IEM, Rolling Mean/Std, Normalização e Z-Score por liga)
    df_features = enriquecer_features_industriais(df_interp)

    # 4. Relatório consolidado
    relatorio_execucao = {
        "status": "sucesso",
        "total_amostras": len(df_features),
        "total_colunas": len(df_features.columns),
        "colunas_geradas": df_features.columns.tolist(),
        "sentinelas_removidos": sentinelas_qtd,
        "ausencias_iniciais": relatorio_ausencias,
        "nans_finais": {k: int(v) for k, v in df_features.isna().sum().items()},
    }

    # 5. Persistência
    PROCESSED_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df_features.to_parquet(PROCESSED_PARQUET, index=False)
    df_features.to_csv(PROCESSED_CSV, index=False)

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(relatorio_execucao, indent=2, ensure_ascii=False), encoding="utf-8")

    return df_features, relatorio_execucao


if __name__ == "__main__":
    df_out, rel = executar_pipeline_completo()
    print(f"Pipeline executado com sucesso! Shape: {df_out.shape}. Colunas: {len(df_out.columns)}.")
