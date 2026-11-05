"""Repositórios de persistência e consulta operacional em SQLite."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from .db import db_session


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SensorRepository:
    """Persistência e leitura de registros de sensores recebidos via API ou simulador."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    def insert_reading(self, reading: dict[str, Any], warnings: list[str] | None = None) -> int:
        now = _utc_now()
        with db_session(self.database_url) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sensor_readings (
                    timestamp, id_celula, liga_metalica,
                    temperatura_fuso_c, vibracao_triaxial_rms_mms, torque_fuso_nm,
                    vazao_refrigerante_lmin, corrente_estator_amp, pressao_hidraulica_bar,
                    nivel_ruido_db, warnings_json, data_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(reading["timestamp"]),
                    str(reading["id_celula"]),
                    str(reading["liga_metalica"]),
                    reading.get("temperatura_fuso_c"),
                    reading.get("vibracao_triaxial_rms_mms"),
                    reading.get("torque_fuso_nm"),
                    reading.get("vazao_refrigerante_lmin"),
                    reading.get("corrente_estator_amp"),
                    reading.get("pressao_hidraulica_bar"),
                    reading.get("nivel_ruido_db"),
                    json.dumps(warnings or [], ensure_ascii=False),
                    str(reading.get("data_source") or "api"),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_readings(
        self,
        equipment_id: str | None = None,
        data_source: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if equipment_id and equipment_id != "Todas":
            clauses.append("id_celula = ?")
            params.append(equipment_id)
        if data_source and data_source not in {"all", "todas"}:
            clauses.append("data_source = ?")
            params.append(data_source)
        if start_date:
            clauses.append("substr(timestamp, 1, 10) >= ?")
            params.append(start_date[:10])
        if end_date:
            clauses.append("substr(timestamp, 1, 10) <= ?")
            params.append(end_date[:10])
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        with db_session(self.database_url) as conn:
            rows = conn.execute(
                f"SELECT * FROM sensor_readings {where_sql} ORDER BY timestamp DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["warnings"] = json.loads(item.pop("warnings_json", "[]") or "[]")
            result.append(item)
        return result


class MaintenanceRepository:
    """Persistência de previsões de manutenção e alertas operacionais."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    def insert_prediction(self, record: dict[str, Any]) -> int:
        now = _utc_now()
        with db_session(self.database_url) as conn:
            cursor = conn.execute(
                """
                INSERT INTO maintenance_predictions (
                    reading_id, timestamp, id_celula, liga_metalica,
                    predicted_class_code, predicted_class_name, recommended_action,
                    scores_json, warnings_json, model_name, data_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("reading_id"),
                    str(record["timestamp"]),
                    str(record["id_celula"]),
                    str(record["liga_metalica"]),
                    int(record["predicted_class_code"]),
                    str(record["predicted_class_name"]),
                    str(record["recommended_action"]),
                    json.dumps(record["scores"], ensure_ascii=False),
                    json.dumps(record.get("warnings") or [], ensure_ascii=False),
                    str(record["model_name"]),
                    str(record.get("data_source") or "api"),
                    now,
                ),
            )
            pred_id = int(cursor.lastrowid)
            fault_code = int(record["predicted_class_code"])
            if fault_code != 0:
                severity = "CRITICA" if fault_code in (2, 3) else "ALTA"
                conn.execute(
                    """
                    INSERT INTO maintenance_alerts (
                        prediction_id, timestamp, id_celula, fault_code, fault_name,
                        severity, recommended_action, message, data_source, acknowledged, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        pred_id,
                        str(record["timestamp"]),
                        str(record["id_celula"]),
                        fault_code,
                        str(record["predicted_class_name"]),
                        severity,
                        str(record["recommended_action"]),
                        f"Classificação contemporânea detectou '{record['predicted_class_name']}' na célula {record['id_celula']}.",
                        str(record.get("data_source") or "api"),
                        now,
                    ),
                )
            return pred_id

    def list_predictions(
        self,
        equipment_id: str | None = None,
        data_source: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if equipment_id and equipment_id != "Todas":
            clauses.append("id_celula = ?")
            params.append(equipment_id)
        if data_source and data_source not in {"all", "todas"}:
            clauses.append("data_source = ?")
            params.append(data_source)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        with db_session(self.database_url) as conn:
            rows = conn.execute(
                f"SELECT * FROM maintenance_predictions {where_sql} ORDER BY timestamp DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        results = []
        for r in rows:
            item = dict(r)
            item["scores"] = json.loads(item.pop("scores_json", "{}") or "{}")
            item["warnings"] = json.loads(item.pop("warnings_json", "[]") or "[]")
            results.append(item)
        return results

    def list_alerts(
        self,
        equipment_id: str | None = None,
        data_source: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if equipment_id and equipment_id != "Todas":
            clauses.append("id_celula = ?")
            params.append(equipment_id)
        if data_source and data_source not in {"all", "todas"}:
            clauses.append("data_source = ?")
            params.append(data_source)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        with db_session(self.database_url) as conn:
            rows = conn.execute(
                f"SELECT * FROM maintenance_alerts {where_sql} ORDER BY timestamp DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(r) for r in rows]


class VisionRepository:
    """Persistência e consulta de inspeções visuais e térmicas."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    def insert_inspection(self, record: dict[str, Any]) -> int:
        now = _utc_now()
        with db_session(self.database_url) as conn:
            cursor = conn.execute(
                """
                INSERT INTO vision_inspections (
                    inspection_uid, timestamp, piece_id, filename, modality,
                    predicted_class, scores_json, score_type, model_status,
                    experimental, validated_for_industrial_use, warnings_json,
                    data_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record["inspection_id"]),
                    str(record["timestamp"]),
                    str(record["piece_id"]),
                    str(record["filename"]),
                    str(record["modality"]),
                    str(record["predicted_class"]),
                    json.dumps(record["class_scores"], ensure_ascii=False),
                    str(record["score_type"]),
                    str(record["model_status"]),
                    1 if record.get("experimental", True) else 0,
                    1 if record.get("validated_for_industrial_use", False) else 0,
                    json.dumps(record.get("warnings") or [], ensure_ascii=False),
                    str(record.get("data_source") or "api"),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_inspections(self, modality: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if modality and modality not in {"all", "todas"}:
            clauses.append("modality = ?")
            params.append(modality.lower())
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        with db_session(self.database_url) as conn:
            rows = conn.execute(
                f"SELECT * FROM vision_inspections {where_sql} ORDER BY timestamp DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        results = []
        for r in rows:
            item = dict(r)
            item["inspection_id"] = item.pop("inspection_uid")
            item["class_scores"] = json.loads(item.pop("scores_json", "{}") or "{}")
            item["warnings"] = json.loads(item.pop("warnings_json", "[]") or "[]")
            item["experimental"] = bool(item["experimental"])
            item["validated_for_industrial_use"] = bool(item["validated_for_industrial_use"])
            results.append(item)
        return results


class OEERepository:
    """Persistência e consulta de eventos operacionais e lotes de produção."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    def insert_production_event(self, event: dict[str, Any]) -> int:
        now = _utc_now()
        with db_session(self.database_url) as conn:
            cursor = conn.execute(
                """
                INSERT INTO production_events (
                    timestamp, id_celula, liga_metalica, shift,
                    planned_time_min, downtime_min, ideal_cycle_time_min,
                    total_count, good_count, rejected_count,
                    downtime_reason, associated_fault_class, data_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event["timestamp"]),
                    str(event["id_celula"]),
                    str(event["liga_metalica"]),
                    str(event["shift"]),
                    float(event["planned_time_min"]),
                    float(event["downtime_min"]),
                    float(event["ideal_cycle_time_min"]),
                    int(event["total_count"]),
                    int(event["good_count"]),
                    int(event["rejected_count"]),
                    event.get("downtime_reason"),
                    int(event.get("associated_fault_class") or 0),
                    str(event.get("data_source") or "simulated"),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_production_events(
        self,
        equipment_id: str | None = None,
        shift: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_source: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if equipment_id and equipment_id != "Todas":
            clauses.append("id_celula = ?")
            params.append(equipment_id)
        if shift and shift not in {"Todos", "all"}:
            clauses.append("shift = ?")
            params.append(shift.upper())
        if data_source and data_source not in {"all", "todas"}:
            clauses.append("data_source = ?")
            params.append(data_source)
        if start_date:
            clauses.append("substr(timestamp, 1, 10) >= ?")
            params.append(start_date[:10])
        if end_date:
            clauses.append("substr(timestamp, 1, 10) <= ?")
            params.append(end_date[:10])
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        with db_session(self.database_url) as conn:
            rows = conn.execute(
                f"SELECT * FROM production_events {where_sql} ORDER BY timestamp DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

