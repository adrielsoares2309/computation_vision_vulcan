"""Persistência SQLite de leituras industriais, anomalias e histórico de predições."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "runtime" / "predictions.sqlite3"


class PredictionHistory:
    """Gerenciador de histórico de predições e telemetria SQLite em WAL mode."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(database_path or DEFAULT_DB_PATH)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    equipment_id TEXT NOT NULL,
                    reading_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    predicted_class INTEGER NOT NULL,
                    anomaly INTEGER,
                    inference_ms REAL NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    regime_operacional TEXT,
                    origem_leitura TEXT NOT NULL DEFAULT 'simulada',
                    probabilities_json TEXT,
                    regime_previous TEXT,
                    regime_changed_at TEXT,
                    perfil_sintetico TEXT,
                    perfil_anomalia TEXT
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_equipment_time "
                "ON predictions(equipment_id, timestamp DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_regime "
                "ON predictions(regime_operacional)"
            )

    def add(self, reading: dict[str, Any], result: dict[str, Any]) -> None:
        probabilities = result.get("probabilidades") or result.get("probabilities")
        equip = (
            result.get("id_celula")
            or result.get("id_equipamento")
            or reading.get("id_celula")
            or reading.get("id_equipamento")
            or "CEL-201"
        )
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO predictions
                (timestamp, equipment_id, reading_json, result_json, predicted_class,
                 anomaly, inference_ms, regime_operacional, origem_leitura,
                 probabilities_json, regime_previous, regime_changed_at,
                 perfil_sintetico, perfil_anomalia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.get("timestamp") or datetime.now().isoformat(),
                    equip,
                    json.dumps(reading, ensure_ascii=False, default=str),
                    json.dumps(result, ensure_ascii=False, default=str),
                    result.get("classe_prevista", 0),
                    None if result.get("anomalia") is None else int(result["anomalia"]),
                    result.get("tempo_inferencia_ms", 1.0),
                    result.get("regime_operacional") or reading.get("modo_operacao") or "Producao_Normal",
                    result.get("origem_leitura") or reading.get("origem_leitura") or "simulada",
                    json.dumps(probabilities, ensure_ascii=False) if probabilities is not None else None,
                    result.get("regime_anterior"),
                    result.get("regime_alterado_em"),
                    result.get("perfil_sintetico") or reading.get("perfil_sintetico"),
                    result.get("perfil_anomalia") or reading.get("perfil_anomalia"),
                ),
            )

    def list(self, limit: int = 100, equipment_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT result_json FROM predictions"
        parameters: list[Any] = []
        if equipment_id:
            query += " WHERE equipment_id = ?"
            parameters.append(equipment_id)
        query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        parameters.append(limit)
        with self._connect() as connection:
            return [json.loads(row["result_json"]) for row in connection.execute(query, parameters)]

    def recent_readings(self, equipment_id: str, since: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT reading_json FROM predictions WHERE equipment_id = ? AND timestamp >= ? ORDER BY timestamp",
                (equipment_id, since),
            )
            return [json.loads(row["reading_json"]) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            equipments = connection.execute("SELECT COUNT(DISTINCT equipment_id) FROM predictions").fetchone()[0]
            last = connection.execute("SELECT MAX(timestamp) FROM predictions").fetchone()[0]
            anomalies = connection.execute("SELECT COUNT(*) FROM predictions WHERE anomaly = 1").fetchone()[0]
            mean_inference = connection.execute("SELECT AVG(inference_ms) FROM predictions").fetchone()[0] or 0.0

            return {
                "total_predicoes": total,
                "celulas_ativas": equipments,
                "ultima_predicao": last,
                "total_anomalias": anomalies,
                "tempo_medio_inferencia_ms": round(mean_inference, 2),
            }

