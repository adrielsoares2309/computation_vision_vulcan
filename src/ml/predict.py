"""Carregamento e inferência com o pipeline persistido."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd


RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_MODELO = RAIZ / "models" / "tabular" / "best_model.joblib"


def carregar_modelo(caminho: str | Path = CAMINHO_MODELO) -> Any:
    """Carrega o pipeline completo previamente treinado."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {caminho}. Execute python -m src.ml.train primeiro.")
    return joblib.load(caminho)


def enriquecer_se_necessario(registros: pd.DataFrame, esperadas: list[str]) -> pd.DataFrame:
    """Enriquece features calculadas caso o chamador forneça apenas leituras brutas."""
    dados = registros.copy()
    if "indice_esforco_mecanico" in esperadas and "indice_esforco_mecanico" not in dados.columns:
        if (
            "torque_fuso_nm" in dados.columns
            and "vibracao_triaxial_rms_mms" in dados.columns
            and "vazao_refrigerante_lmin" in dados.columns
        ):
            dados["indice_esforco_mecanico"] = (
                dados["torque_fuso_nm"] * dados["vibracao_triaxial_rms_mms"]
            ) / (dados["vazao_refrigerante_lmin"] + 1.0)

    for col in esperadas:
        if col not in dados.columns:
            if "_rolling_mean_" in col:
                base_col = col.split("_rolling_mean_")[0]
                dados[col] = dados[base_col] if base_col in dados.columns else 0.0
            elif "_rolling_std_" in col:
                dados[col] = 0.0
            elif "_norm_liga" in col:
                base_col = col.split("_norm_liga")[0]
                dados[col] = dados[base_col] if base_col in dados.columns else 0.0
            elif "_zscore_liga" in col:
                dados[col] = 0.0
    return dados


def prever(registros: pd.DataFrame, modelo: Any | None = None) -> pd.DataFrame:
    """Retorna rótulo previsto e probabilidades por classe para registros brutos compatíveis."""
    modelo = modelo or carregar_modelo()
    esperadas = list(modelo.feature_names_in_)
    registros_processados = enriquecer_se_necessario(registros, esperadas)
    faltantes = sorted(set(esperadas) - set(registros_processados.columns))
    extras = sorted(set(registros_processados.columns) - set(esperadas))
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {faltantes}")
    entrada = registros_processados.loc[:, esperadas]
    resultado = pd.DataFrame({"tipo_falha_previsto": modelo.predict(entrada)}, index=registros.index)
    if hasattr(modelo, "predict_proba"):
        probabilidades = modelo.predict_proba(entrada)
        for indice, classe in enumerate(modelo.classes_):
            resultado[f"probabilidade_classe_{classe}"] = probabilidades[:, indice]
    if extras:
        resultado.attrs["colunas_extras_ignoradas"] = extras
    return resultado


DESC_FALHAS = {
    0: "Operação Normal",
    1: "Desgaste de Ferramenta",
    2: "Falha de Refrigeração",
    3: "Desalinhamento / Trinca",
}


def predict_single(reading: dict[str, Any], modelo: Any | None = None) -> dict[str, Any]:
    """Realiza inferência para uma leitura individual fornecida como dicionário."""
    df_in = pd.DataFrame([reading])
    preds = prever(df_in, modelo=modelo)
    pred_class = int(preds["tipo_falha_previsto"].iloc[0])

    prob_cols = [c for c in preds.columns if c.startswith("probabilidade_classe_")]
    if prob_cols:
        probs = [float(preds[c].iloc[0]) for c in sorted(prob_cols)]
    else:
        probs = [1.0 if i == pred_class else 0.0 for i in range(4)]

    # Anomalia se classe > 0 ou IEM crítico
    iem = float(reading.get("indice_esforco_mecanico", 0.0))
    if not iem and "torque_fuso_nm" in reading and "vibracao_triaxial_rms_mms" in reading:
        flow = float(reading.get("vazao_refrigerante_lmin", 15.0))
        iem = (float(reading["torque_fuso_nm"]) * float(reading["vibracao_triaxial_rms_mms"])) / (flow + 1.0)

    is_anomaly = int(pred_class > 0 or iem > 32.0)

    return {
        "classe_predita": pred_class,
        "descricao_falha": DESC_FALHAS.get(pred_class, f"Falha Tipo {pred_class}"),
        "probabilidades": probs,
        "anomalia": is_anomaly,
        "score_anomalia": float(max(probs[1:]) if len(probs) > 1 else is_anomaly),
        "indice_esforco_mecanico": round(iem, 3),
    }

