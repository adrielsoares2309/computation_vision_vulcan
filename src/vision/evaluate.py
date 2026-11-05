"""Avaliação separada por modalidade e recusa segura para amostras insuficientes."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score


def evaluate_predictions(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    """Calcula métricas quando existe uma partição independente válida."""
    labels = [0, 1]
    return {
        "sample_count": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "recall_reprovada": float(recall_score(y_true, y_pred, labels=[1], average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "classification_report": classification_report(y_true, y_pred, labels=labels,
                                                        target_names=["APROVADA", "REPROVADA"],
                                                        output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def insufficient_evaluation(reasons: list[str], per_modality: dict[str, Any]) -> dict[str, Any]:
    """Expressa a ausência de avaliação independente sem fabricar métricas."""
    return {"status": "insufficient_independent_data", "metrics": None,
            "confusion_matrix": None, "reasons": reasons, "per_modality": per_modality}

