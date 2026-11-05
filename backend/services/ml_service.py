"""Serviço de Manutenção Preditiva e Classificação Tabular."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend.config import Settings, get_settings
from database.repositories import MaintenanceRepository
from src.data.cleaner import dataframe_from_readings
from src.data.validator import FAULT_CLASSES, INDUSTRIAL_ACTIONS, SENSOR_SPECS, VALID_CELLS
from src.ml.predict import prever


class MLService:
    """Gerencia o modelo tabular persistido, metadados e inferências de sensores."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._lock = threading.Lock()
        self._model: Any | None = None
        self._model_mtime: int | None = None
        self._metadata: dict[str, Any] | None = None
        self._metadata_mtime: int | None = None
        self._dataset_cache: pd.DataFrame | None = None
        self._dataset_mtime: int | None = None
        self._dataset_path: Path | None = None
        self.repo = MaintenanceRepository(self.settings.database_url)

    @property
    def model_path(self) -> Path:
        return self.settings.model_dir / "tabular" / "best_model.joblib"

    @property
    def metadata_path(self) -> Path:
        return self.settings.model_dir / "tabular" / "model_metadata.json"

    @property
    def parquet_path(self) -> Path:
        return self.settings.data_dir / "processed" / "dados_sensores_vulcantech_tratados.parquet"

    @property
    def csv_path(self) -> Path:
        return self.settings.data_dir / "processed" / "dados_sensores_vulcantech_tratados.csv"

    def check_availability(self) -> dict[str, Any]:
        """Verifica disponibilidade do modelo tabular e metadados sem forçar retreinamento."""
        model_exists = self.model_path.is_file()
        meta_exists = self.metadata_path.is_file()
        dataset_exists = self.parquet_path.is_file() or self.csv_path.is_file()
        error = None
        model_name = None
        if meta_exists:
            try:
                meta = self.get_metadata()
                model_name = meta.get("model_name")
            except Exception as exc:
                error = str(exc)
        elif not model_exists:
            error = f"Modelo tabular ausente em {self.model_path.name}."
        return {
            "available": bool(model_exists and meta_exists and error is None),
            "model_file": self.model_path.name if model_exists else None,
            "metadata_file": self.metadata_path.name if meta_exists else None,
            "dataset_available": dataset_exists,
            "model_name": model_name,
            "task_type": "contemporaneous_multiclass_classification",
            "predicts_future_rul": False,
            "error": error,
        }

    def get_model(self) -> Any:
        """Carrega o pipeline tabular uma única vez por processo (ou quando atualizado em disco)."""
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Modelo tabular não encontrado ({self.model_path.name}). Execute 'python -m src.ml.train'."
            )
        mtime = self.model_path.stat().st_mtime_ns
        with self._lock:
            if self._model is None or self._model_mtime != mtime:
                self._model = joblib.load(self.model_path)
                self._model_mtime = mtime
            return self._model

    def get_metadata(self) -> dict[str, Any]:
        """Retorna os metadados reais do treinamento tabular."""
        if not self.metadata_path.is_file():
            raise FileNotFoundError(f"Metadados do modelo tabular não encontrados ({self.metadata_path.name}).")
        mtime = self.metadata_path.stat().st_mtime_ns
        with self._lock:
            if self._metadata is None or self._metadata_mtime != mtime:
                self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                self._metadata_mtime = mtime
            return dict(self._metadata)

    def load_historical_dataset(self) -> tuple[pd.DataFrame, Path]:
        """Carrega o dataset tratado de sensores (somente leitura, com cache por mtime)."""
        target = self.parquet_path if self.parquet_path.is_file() else self.csv_path
        if not target.is_file():
            raise FileNotFoundError("Dataset tratado não encontrado em data/processed.")
        mtime = target.stat().st_mtime_ns
        with self._lock:
            if self._dataset_cache is None or self._dataset_mtime != mtime or self._dataset_path != target:
                df = (
                    pd.read_parquet(target)
                    if target.suffix.lower() == ".parquet"
                    else pd.read_csv(target, parse_dates=["timestamp"])
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                self._dataset_cache = df
                self._dataset_mtime = mtime
                self._dataset_path = target
            return self._dataset_cache.copy(), target

    def predict_single(
        self,
        payload: dict[str, Any],
        persist: bool = True,
        reading_id: int | None = None,
    ) -> dict[str, Any]:
        """Executa inferência para uma única leitura de sensores."""
        results = self.predict_batch([payload], persist=persist, reading_ids=[reading_id] if reading_id else None)
        return results[0]

    def predict_batch(
        self,
        payloads: list[dict[str, Any]],
        persist: bool = False,
        reading_ids: list[int | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Executa inferência sobre uma lista de leituras reutilizando src.ml.predict.prever."""
        model = self.get_model()
        metadata = self.get_metadata()
        class_map = {int(c["label"]): str(c["name"]) for c in metadata.get("classes", [])} or FAULT_CLASSES

        df_input, warnings_per_row = dataframe_from_readings(payloads)
        predictions_df = prever(df_input, modelo=model)

        outputs: list[dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        for idx, raw_row in enumerate(payloads):
            pred_row = predictions_df.iloc[idx]
            code = int(pred_row["tipo_falha_previsto"])
            class_name = class_map.get(code, FAULT_CLASSES.get(code, str(code)))
            action = INDUSTRIAL_ACTIONS.get(code, "MANTER_OPERACAO")
            if code == 0:
                op_state = "NORMAL"
            elif code == 1:
                op_state = "ALERTA_MANUTENCAO"
            else:
                op_state = "PARADA_RECOMENDADA"

            scores: dict[str, float] = {}
            for col in predictions_df.columns:
                if col.startswith("probabilidade_classe_"):
                    cls_idx = int(col.replace("probabilidade_classe_", ""))
                    cls_label = class_map.get(cls_idx, str(cls_idx))
                    scores[cls_label] = round(float(pred_row[col]), 6)

            ts_val = raw_row.get("timestamp") or now_iso
            if isinstance(ts_val, pd.Timestamp):
                ts_val = ts_val.isoformat()
            else:
                ts_val = str(ts_val)

            source = str(raw_row.get("data_source") or "api")
            row_warnings = list(warnings_per_row[idx])

            record = {
                "reading_id": reading_ids[idx] if reading_ids and idx < len(reading_ids) else None,
                "equipment_id": str(raw_row["id_celula"]),
                "id_celula": str(raw_row["id_celula"]),
                "liga_metalica": str(raw_row["liga_metalica"]),
                "timestamp": ts_val,
                "predicted_class_code": code,
                "predicted_class_name": class_name,
                "operational_state": op_state,
                "recommended_action": action,
                "scores": scores,
                "calibrated_probabilities": False,
                "model_name": str(metadata.get("model_name", "LogisticRegression")),
                "model_trained_at_utc": metadata.get("trained_at_utc"),
                "data_source": source,
                "inference_status": "completed",
                "interpretation": (
                    "Classificação contemporânea da condição associada à leitura atual; "
                    "não estima tempo futuro até falha (RUL)."
                ),
                "warnings": row_warnings,
            }

            if persist:
                pred_id = self.repo.insert_prediction(record)
                record["prediction_id"] = pred_id
            else:
                record["prediction_id"] = None

            outputs.append(record)

        return outputs

    def get_latest_predictions(self, equipment_id: str | None = None, data_source: str | None = None) -> dict[str, Any]:
        """Retorna as previsões mais recentes persistidas ou classifica a última leitura histórica por célula."""
        persisted = self.repo.list_predictions(equipment_id=equipment_id, data_source=data_source, limit=25)
        if persisted:
            return {
                "available": True,
                "source": "database_predictions",
                "count": len(persisted),
                "items": persisted,
            }

        if data_source in {"simulated", "api"}:
            return {
                "available": False,
                "source": data_source,
                "count": 0,
                "items": [],
                "reason": f"Nenhuma previsão registrada com origem '{data_source}' no banco operacional.",
            }

        df, _ = self.load_historical_dataset()
        if equipment_id and equipment_id != "Todas":
            df = df[df["id_celula"].astype(str) == equipment_id]
        if df.empty:
            return {"available": False, "source": "historical", "count": 0, "items": []}

        latest_per_cell = df.sort_values("timestamp").groupby("id_celula", as_index=False).last()
        payloads = []
        for _, row in latest_per_cell.iterrows():
            item = row.to_dict()
            item["timestamp"] = row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None
            item["data_source"] = "historical"
            payloads.append(item)
        computed = self.predict_batch(payloads, persist=False)
        return {
            "available": True,
            "source": "historical_latest_snapshot",
            "count": len(computed),
            "items": computed,
        }

    def get_prediction_history(
        self,
        equipment_id: str | None = None,
        data_source: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Consulta o histórico real de previsões persistidas no banco SQLite."""
        items = self.repo.list_predictions(equipment_id=equipment_id, data_source=data_source, limit=limit)
        return {
            "count": len(items),
            "data_source_filter": data_source or "all",
            "items": items,
        }

    def get_alerts(
        self,
        equipment_id: str | None = None,
        data_source: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Retorna alertas operacionais registrados a partir de classificações de falha."""
        alerts = self.repo.list_alerts(equipment_id=equipment_id, data_source=data_source, limit=limit)
        return {
            "count": len(alerts),
            "items": alerts,
            "note": "Alertas refletem classificações contemporâneas de falhas (classes 1, 2 e 3) registradas no banco operacional.",
        }

    def get_equipment_overview(self, data_source: str = "all") -> dict[str, Any]:
        """Consolida o estado operacional e estatísticas por célula (CEL-201 a CEL-204)."""
        df, path = self.load_historical_dataset()
        persisted_preds = self.repo.list_predictions(
            data_source=None if data_source == "all" else data_source,
            limit=200,
        )
        latest_pred_by_cell: dict[str, dict[str, Any]] = {}
        for pred in persisted_preds:
            cell = pred["id_celula"]
            if cell not in latest_pred_by_cell:
                latest_pred_by_cell[cell] = pred

        cells_summary = []
        for cell in sorted(VALID_CELLS):
            cell_df = df[df["id_celula"].astype(str) == cell]
            fault_counts = (
                {FAULT_CLASSES.get(int(k), str(k)): int(v) for k, v in cell_df["tipo_falha"].value_counts().items()}
                if not cell_df.empty and "tipo_falha" in cell_df.columns
                else {}
            )
            last_row = cell_df.sort_values("timestamp").iloc[-1] if not cell_df.empty else None
            latest_pred = latest_pred_by_cell.get(cell)
            cells_summary.append(
                {
                    "equipment_id": cell,
                    "historical_readings": int(len(cell_df)),
                    "historical_last_timestamp": (
                        last_row["timestamp"].isoformat() if last_row is not None and pd.notna(last_row["timestamp"]) else None
                    ),
                    "historical_fault_distribution": fault_counts,
                    "latest_persisted_prediction": latest_pred,
                }
            )
        return {
            "dataset_source": path.name,
            "equipment": cells_summary,
        }

    def get_maintenance_sensors_summary(
        self,
        equipment_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sensor: str = "temperatura_fuso_c",
        data_source: str = "historical",
        limit: int = 500,
    ) -> dict[str, Any]:
        """Retorna estatísticas, distribuição de classes e série temporal para a página de Manutenção Preditiva."""
        hist_df, path = self.load_historical_dataset()
        min_date = hist_df["timestamp"].min().date().isoformat()
        max_date = hist_df["timestamp"].max().date().isoformat()
        cells = sorted(hist_df["id_celula"].dropna().astype(str).unique().tolist())

        if data_source in {"simulated", "api"}:
            from database.repositories import SensorRepository

            sensor_repo = SensorRepository(self.settings.database_url)
            db_rows = sensor_repo.list_readings(
                equipment_id=equipment_id,
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                limit=max(limit, 500),
            )
            preds = self.repo.list_predictions(
                equipment_id=equipment_id,
                data_source=data_source,
                limit=max(limit, 500),
            )
            pred_by_reading = {p["reading_id"]: p["predicted_class_code"] for p in preds if p.get("reading_id")}
            if db_rows:
                df = pd.DataFrame(db_rows)
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_localize(None)
                df["tipo_falha"] = df["id"].map(pred_by_reading)
            else:
                df = pd.DataFrame(columns=[*hist_df.columns, "data_source"])
        elif data_source == "all":
            from database.repositories import SensorRepository

            sensor_repo = SensorRepository(self.settings.database_url)
            db_rows = sensor_repo.list_readings(
                equipment_id=equipment_id,
                start_date=start_date,
                end_date=end_date,
                limit=500,
            )
            preds = self.repo.list_predictions(equipment_id=equipment_id, limit=500)
            pred_by_reading = {p["reading_id"]: p["predicted_class_code"] for p in preds if p.get("reading_id")}
            h_copy = hist_df.copy()
            h_copy["data_source"] = "historical"
            if db_rows:
                db_df = pd.DataFrame(db_rows)
                db_df["timestamp"] = pd.to_datetime(db_df["timestamp"], errors="coerce", utc=True).dt.tz_localize(None)
                db_df["tipo_falha"] = db_df["id"].map(pred_by_reading)
                df = pd.concat([h_copy, db_df], ignore_index=True)
            else:
                df = h_copy
        else:
            df = hist_df.copy()
            df["data_source"] = "historical"

        if not df.empty and pd.notna(df["timestamp"].max()):
            max_d_actual = df["timestamp"].max().date().isoformat()
            if max_d_actual > max_date:
                max_date = max_d_actual

        filtered = df
        if not filtered.empty:
            if equipment_id and equipment_id != "Todas":
                filtered = filtered[filtered["id_celula"].astype(str) == equipment_id]
            if start_date:
                filtered = filtered[filtered["timestamp"].dt.date >= pd.to_datetime(start_date).date()]
            if end_date:
                filtered = filtered[filtered["timestamp"].dt.date <= pd.to_datetime(end_date).date()]

        total_readings = int(len(filtered))
        cells_in_slice = int(filtered["id_celula"].nunique()) if not filtered.empty else 0
        labeled_count = int(filtered["tipo_falha"].notna().sum()) if "tipo_falha" in filtered.columns and not filtered.empty else 0

        class_dist = []
        if "tipo_falha" in filtered.columns and not filtered.empty:
            vc = filtered["tipo_falha"].value_counts(dropna=True).sort_index()
            for code, qty in vc.items():
                class_dist.append(
                    {
                        "class_code": int(code),
                        "class_name": FAULT_CLASSES.get(int(code), str(code)),
                        "count": int(qty),
                    }
                )

        if sensor not in SENSOR_SPECS:
            sensor = "temperatura_fuso_c"
        spec = SENSOR_SPECS[sensor]

        sorted_slice = filtered.sort_values("timestamp") if not filtered.empty else filtered
        if len(sorted_slice) > limit:
            step = max(1, len(sorted_slice) // limit)
            sampled = sorted_slice.iloc[::step].head(limit)
        else:
            sampled = sorted_slice

        series = []
        for idx, row in sampled.iterrows():
            val = row.get(sensor)
            series.append(
                {
                    "row_index": int(idx),
                    "timestamp": row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None,
                    "id_celula": str(row["id_celula"]),
                    "liga_metalica": str(row["liga_metalica"]),
                    "value": None if pd.isna(val) else round(float(val), 3),
                    "tipo_falha": int(row["tipo_falha"]) if pd.notna(row.get("tipo_falha")) else None,
                    "data_source": str(row.get("data_source") or data_source),
                }
            )

        sample_rows = []
        for idx, row in sorted_slice.tail(60).iterrows():
            sample_rows.append(
                {
                    "row_index": int(idx),
                    "timestamp": row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None,
                    "id_celula": str(row["id_celula"]),
                    "liga_metalica": str(row["liga_metalica"]),
                    "temperatura_fuso_c": None if pd.isna(row["temperatura_fuso_c"]) else float(row["temperatura_fuso_c"]),
                    "vibracao_triaxial_rms_mms": None if pd.isna(row["vibracao_triaxial_rms_mms"]) else float(row["vibracao_triaxial_rms_mms"]),
                    "torque_fuso_nm": None if pd.isna(row["torque_fuso_nm"]) else float(row["torque_fuso_nm"]),
                    "vazao_refrigerante_lmin": None if pd.isna(row["vazao_refrigerante_lmin"]) else float(row["vazao_refrigerante_lmin"]),
                    "corrente_estator_amp": None if pd.isna(row["corrente_estator_amp"]) else float(row["corrente_estator_amp"]),
                    "pressao_hidraulica_bar": None if pd.isna(row["pressao_hidraulica_bar"]) else float(row["pressao_hidraulica_bar"]),
                    "nivel_ruido_db": None if pd.isna(row["nivel_ruido_db"]) else float(row["nivel_ruido_db"]),
                    "tipo_falha": int(row["tipo_falha"]) if pd.notna(row.get("tipo_falha")) else None,
                    "data_source": str(row.get("data_source") or data_source),
                }
            )

        return {
            "dataset_file": f"data/processed/{path.name}" if data_source in {"historical", "all"} else "database/vulcantech.db",
            "data_source": data_source,
            "available_cells": cells,
            "date_range": {"min": min_date, "max": max_date},
            "last_timestamp": (
                filtered["timestamp"].max().isoformat() if not filtered.empty and pd.notna(filtered["timestamp"].max()) else None
            ),
            "kpis": {
                "readings_in_period": total_readings,
                "cells_count": cells_in_slice,
                "labeled_readings": labeled_count,
                "future_failures_predicted": None,
            },
            "sensor_spec": {"column": sensor, **spec},
            "all_sensor_specs": SENSOR_SPECS,
            "class_distribution": class_dist,
            "series": series,
            "selectable_records": sample_rows,
        }

