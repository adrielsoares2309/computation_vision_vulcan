"""Módulo de Detecção de Anomalias Não Supervisionada para Sensores Industriais.

Utiliza Isolation Forest para identificar comportamentos atípicos e desvios operacionais,
complementando a classificação supervisionada multiclasse sem substituí-la.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data.validator import SENSOR_SPECS

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "tabular" / "anomaly_detector.joblib"
SENSORES = list(SENSOR_SPECS.keys())


def criar_pipeline_detector(contamination: float = 0.05, random_state: int = 42) -> Pipeline:
    """Cria pipeline de detecção de anomalias com imputação, padronização e Isolation Forest."""
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                IsolationForest(
                    n_estimators=150,
                    contamination=contamination,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def treinar_detector(
    df_treino: pd.DataFrame | str | Path,
    caminho_salvar: Path | None = None,
) -> dict[str, Any]:
    """Treina o Isolation Forest sobre os dados de sensores de treino e persiste o artefato."""
    if isinstance(df_treino, (str, Path)):
        caminho = Path(df_treino)
        df_treino = pd.read_parquet(caminho) if caminho.suffix == ".parquet" else pd.read_csv(caminho)

    colunas_validas = [c for c in SENSORES if c in df_treino.columns]
    X = df_treino[colunas_validas].copy()

    # Treina preferencialmente em operação normal (tipo_falha == 0) para modelar baseline
    if "tipo_falha" in df_treino.columns:
        mask_normal = df_treino["tipo_falha"] == 0
        if mask_normal.sum() > 100:
            X = df_treino.loc[mask_normal, colunas_validas].copy()

    pipeline = criar_pipeline_detector()
    pipeline.fit(X)

    destino = caminho_salvar or MODEL_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, destino)

    # Avaliação rápida no próprio conjunto
    is_anomaly, score_norm = detectar_anomalias(df_treino, pipeline)

    return {
        "status": "success",
        "pipeline": pipeline,
        "caminho_modelo": str(destino),
        "colunas_treino": colunas_validas,
        "amostras_treinadas": len(X),
        "taxa_anomalias_detectada": float(is_anomaly.mean()),
        "limiar_normal": 0.5,
    }


def carregar_detector(caminho: Path | None = None) -> Pipeline:
    """Carrega o detector de anomalias treinado."""
    destino = caminho or MODEL_PATH
    if not destino.is_file():
        raise FileNotFoundError(f"Detector de anomalias não encontrado em {destino}.")
    return joblib.load(destino)


def detectar_anomalias(
    df: pd.DataFrame,
    pipeline: Pipeline | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Executa detecção de anomalias sobre um lote de leituras de sensores.

    Retorna:
    - is_anomaly: array booleano (True se anomalia detectada)
    - anomaly_score: escore normalizado de 0.0 (normal) a 1.0 (anomalia severa)
    """
    model_pipe = pipeline or carregar_detector()
    colunas_validas = [c for c in SENSORES if c in df.columns]
    X = df[colunas_validas].copy()

    # predict retorna 1 para normal e -1 para anomalia
    preds = model_pipe.predict(X)
    is_anomaly = preds == -1

    # decision_function retorna valores negativos para anomalias
    dec_func = model_pipe.decision_function(X)
    # Normalização min-max invertida para escala 0.0 (normal) a 1.0 (anomalia)
    score_norm = 1.0 / (1.0 + np.exp(dec_func * 8.0))
    score_norm = np.clip(score_norm, 0.0, 1.0).round(4)

    return is_anomaly, score_norm
