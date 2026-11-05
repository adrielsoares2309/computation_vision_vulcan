"""Serviço de Sensores e Telemetria Industrial."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from backend.config import Settings, get_settings
from backend.services.ml_service import MLService
from database.repositories import SensorRepository
from src.data.cleaner import sanitize_sensor_reading
from src.data.validator import SENSOR_SPECS, VALID_CELLS


class SensorService:
    """Coordena a ingestão e consulta de leituras de sensores (históricas, simuladas e via API)."""

    def __init__(self, settings: Settings | None = None, ml_service: MLService | None = None) -> None:
        self.settings = settings or get_settings()
        self.ml_service = ml_service or MLService(self.settings)
        self.repo = SensorRepository(self.settings.database_url)

    def ingest_reading(self, payload: dict[str, Any], run_prediction: bool = True) -> dict[str, Any]:
        """Valida, higieniza sentinelas, persiste no SQLite e opcionalmente executa a inferência."""
        raw = dict(payload)
        if not raw.get("timestamp"):
            raw["timestamp"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        cleaned, warnings = sanitize_sensor_reading(raw)
        reading_id = self.repo.insert_reading(cleaned, warnings=warnings)

        prediction = None
        if run_prediction:
            prediction = self.ml_service.predict_single(cleaned, persist=True, reading_id=reading_id)

        return {
            "reading_id": reading_id,
            "reading": cleaned,
            "warnings": warnings,
            "prediction": prediction,
        }

    def get_latest_readings(self, data_source: str = "all") -> dict[str, Any]:
        """Retorna a última leitura de cada célula identificando claramente a origem."""
        if data_source in {"api", "simulated"}:
            rows = self.repo.list_readings(data_source=data_source, limit=100)
            latest_by_cell: dict[str, dict[str, Any]] = {}
            for r in rows:
                cell = r["id_celula"]
                if cell not in latest_by_cell:
                    latest_by_cell[cell] = r
            return {
                "data_source": data_source,
                "count": len(latest_by_cell),
                "items": list(latest_by_cell.values()),
            }

        df, _ = self.ml_service.load_historical_dataset()
        hist_latest = df.sort_values("timestamp").groupby("id_celula", as_index=False).last()
        latest_map: dict[str, dict[str, Any]] = {}
        for _, row in hist_latest.iterrows():
            item = {
                "id": None,
                "timestamp": row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None,
                "id_celula": str(row["id_celula"]),
                "liga_metalica": str(row["liga_metalica"]),
                "data_source": "historical",
            }
            for col in SENSOR_SPECS:
                val = row.get(col)
                item[col] = None if pd.isna(val) else round(float(val), 3)
            latest_map[str(row["id_celula"])] = item

        if data_source == "all":
            db_rows = self.repo.list_readings(limit=50)
            for r in reversed(db_rows):
                latest_map[r["id_celula"]] = r

        items = [latest_map[c] for c in sorted(latest_map)]
        return {
            "data_source": data_source,
            "count": len(items),
            "items": items,
        }

    def get_history(
        self,
        equipment_id: str | None = None,
        data_source: str = "historical",
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Consulta leituras históricas do Parquet ou operacionais do SQLite sem misturar sem identificação."""
        if data_source in {"api", "simulated"}:
            items = self.repo.list_readings(
                equipment_id=equipment_id,
                data_source=data_source,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            return {
                "data_source": data_source,
                "count": len(items),
                "items": items,
            }

        df, path = self.ml_service.load_historical_dataset()
        if equipment_id and equipment_id != "Todas":
            df = df[df["id_celula"].astype(str) == equipment_id]
        if start_date:
            df = df[df["timestamp"].dt.date >= pd.to_datetime(start_date).date()]
        if end_date:
            df = df[df["timestamp"].dt.date <= pd.to_datetime(end_date).date()]

        df_sorted = df.sort_values("timestamp", ascending=False).head(limit)
        records = []
        for idx, row in df_sorted.iterrows():
            entry: dict[str, Any] = {
                "row_index": int(idx),
                "timestamp": row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None,
                "id_celula": str(row["id_celula"]),
                "liga_metalica": str(row["liga_metalica"]),
                "tipo_falha": int(row["tipo_falha"]) if "tipo_falha" in row and pd.notna(row["tipo_falha"]) else None,
                "data_source": "historical",
            }
            for col in SENSOR_SPECS:
                val = row.get(col)
                entry[col] = None if pd.isna(val) else round(float(val), 3)
            records.append(entry)

        if data_source == "all":
            db_items = self.repo.list_readings(
                equipment_id=equipment_id,
                start_date=start_date,
                end_date=end_date,
                limit=min(limit, 100),
            )
            records = (db_items + records)[:limit]

        return {
            "data_source": data_source,
            "source_file": path.name if data_source in {"historical", "all"} else None,
            "count": len(records),
            "items": records,
        }

    def get_equipment_telemetry(self, equipment_id: str, data_source: str = "historical") -> dict[str, Any]:
        """Retorna estatísticas resumidas de telemetria para uma célula específica."""
        cell = equipment_id.strip().upper()
        if cell not in VALID_CELLS:
            raise ValueError(f"Equipamento inválido ({equipment_id}). Células válidas: {sorted(VALID_CELLS)}.")

        if data_source in {"api", "simulated"}:
            rows = self.repo.list_readings(equipment_id=cell, data_source=data_source, limit=500)
            if not rows:
                return {
                    "equipment_id": cell,
                    "data_source": data_source,
                    "available": False,
                    "count": 0,
                    "sensors_summary": {},
                    "latest_reading": None,
                }
            df = pd.DataFrame(rows)
        else:
            df, _ = self.ml_service.load_historical_dataset()
            df = df[df["id_celula"].astype(str) == cell]

        sensors_summary: dict[str, Any] = {}
        for col, spec in SENSOR_SPECS.items():
            if col in df.columns:
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                out_of_range = int((~s.between(spec["normal_min"], spec["normal_max"])).sum()) if not s.empty else 0
                sensors_summary[col] = {
                    "label": spec["label"],
                    "unit": spec["unit"],
                    "count": int(len(s)),
                    "mean": round(float(s.mean()), 3) if not s.empty else None,
                    "min": round(float(s.min()), 3) if not s.empty else None,
                    "max": round(float(s.max()), 3) if not s.empty else None,
                    "out_of_normal_range": out_of_range,
                }

        latest_row = df.sort_values("timestamp").iloc[-1].to_dict() if not df.empty else None
        if latest_row and isinstance(latest_row.get("timestamp"), pd.Timestamp):
            latest_row["timestamp"] = latest_row["timestamp"].isoformat()

        return {
            "equipment_id": cell,
            "data_source": data_source,
            "available": not df.empty,
            "count": int(len(df)),
            "sensors_summary": sensors_summary,
            "latest_reading": latest_row,
        }

