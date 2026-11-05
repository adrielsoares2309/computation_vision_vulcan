"""Serviço de inferência de falhas com buffer temporal e engenharia dinâmica de atributos."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

import joblib
import numpy as np

from api.history import PredictionHistory
from src.ml.predict import predict_single

ROOT_DIR = Path(__file__).resolve().parents[1]

CLASS_NAMES = {
    0: "Normal",
    1: "Desgaste_Ferramenta",
    2: "Falha_Refrigeracao",
    3: "Desalinhamento_Trinca",
}


class ModelService:
    """Carrega classificadores treinados e executa predições enriquecidas em tempo real."""

    def __init__(self, root_dir: Path | None = None, history: PredictionHistory | None = None) -> None:
        self.root_dir = root_dir or ROOT_DIR
        self.history = history or PredictionHistory()
        self.classifier_path = self.root_dir / "models" / "tabular" / "best_model.joblib"
        self.anomaly_path = self.root_dir / "models" / "tabular" / "anomaly_detector.joblib"

        if not self.classifier_path.exists():
            raise FileNotFoundError(f"Classificador não encontrado em: {self.classifier_path}")

        self.classifier_bundle = joblib.load(self.classifier_path)
        self.classifier = (
            self.classifier_bundle["model"]
            if isinstance(self.classifier_bundle, dict) and "model" in self.classifier_bundle
            else self.classifier_bundle
        )
        self.anomaly_model = joblib.load(self.anomaly_path) if self.anomaly_path.exists() else None
        self.buffers: dict[str, deque[dict[str, Any]]] = defaultdict(deque)

    def predict(self, reading: dict[str, Any]) -> dict[str, Any]:
        """Calcula a predição multiclasse com probabilidades e detecção de anomalias."""
        started = perf_counter()
        cell_id = reading.get("id_celula") or reading.get("id_equipamento") or "CEL-201"
        alloy = reading.get("liga_metalica") or "Aco_Carbono_316L"

        res = predict_single(reading)
        duration_ms = (perf_counter() - started) * 1000.0

        output = {
            "timestamp": reading.get("timestamp") or datetime.now().isoformat(),
            "id_celula": cell_id,
            "id_equipamento": cell_id,
            "liga_metalica": alloy,
            "classe_prevista": res["classe_predita"],
            "rotulo_classe": res["descricao_falha"],
            "probabilidades": res["probabilidades"],
            "anomalia": res.get("anomalia", 0),
            "score_anomalia": res.get("score_anomalia", 0.0),
            "tempo_inferencia_ms": round(duration_ms, 2),
            "iem": res.get("indice_esforco_mecanico", 0.0),
            "regime_operacional": reading.get("regime_operacional") or reading.get("modo_operacao") or "Producao_Normal",
            "origem_leitura": reading.get("origem_leitura", "simulada"),
            "status_operacional": "ALERTA" if res["classe_predita"] > 0 else "NORMAL",
        }

        if self.history:
            self.history.add(reading, output)

        return output

