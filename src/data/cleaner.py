"""Saneamento de leituras individuais ou lotes para inferência online."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .validator import SENSOR_SPECS


def sanitize_sensor_reading(reading: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Converte sentinelas documentados (999.9, -99.0, -1.0) em None/NaN e registra avisos."""
    cleaned = dict(reading)
    warnings: list[str] = []

    if "id_celula" in cleaned and cleaned["id_celula"] is not None:
        cleaned["id_celula"] = str(cleaned["id_celula"]).strip()
    if "liga_metalica" in cleaned and cleaned["liga_metalica"] is not None:
        cleaned["liga_metalica"] = str(cleaned["liga_metalica"]).strip()

    for col, spec in SENSOR_SPECS.items():
        val = cleaned.get(col)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            warnings.append(f"Valor ausente em '{col}'; será imputado pelo pipeline do modelo.")
            cleaned[col] = None
            continue
        fval = float(val)
        if any(abs(fval - s) < 1e-6 for s in spec["sentinels"]):
            warnings.append(
                f"Sentinela de ruído documentado ({fval}) detectado em '{col}'; convertido em ausente para imputação segura."
            )
            cleaned[col] = None
            continue
        if fval < spec["normal_min"] or fval > spec["normal_max"]:
            warnings.append(
                f"Leitura de '{col}' ({fval} {spec['unit']}) fora da faixa normal documentada "
                f"({spec['normal_min']} a {spec['normal_max']} {spec['unit']})."
            )
        cleaned[col] = fval

    return cleaned, warnings


def dataframe_from_readings(readings: list[dict[str, Any]]) -> tuple[pd.DataFrame, list[list[str]]]:
    """Prepara um DataFrame compatível com src.ml.predict.prever a partir de uma lista de leituras."""
    cleaned_rows = []
    all_warnings = []
    for row in readings:
        c_row, row_warnings = sanitize_sensor_reading(row)
        cleaned_rows.append(c_row)
        all_warnings.append(row_warnings)
    df = pd.DataFrame(cleaned_rows)
    for col in SENSOR_SPECS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df, all_warnings

