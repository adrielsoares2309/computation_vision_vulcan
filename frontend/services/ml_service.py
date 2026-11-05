"""Serviço do frontend para Manutenção Preditiva e Telemetria consumindo a API FastAPI."""

from __future__ import annotations

from typing import Any

from frontend.services.api_client import get_api_client


def get_sensor_metadata() -> dict[str, Any]:
    """Consulta metadados do modelo tabular e disponibilidade na API."""
    return get_api_client().get("/maintenance/metadata")


def get_maintenance_sensors_view(
    equipment_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sensor: str = "temperatura_fuso_c",
    data_source: str = "historical",
    limit: int = 500,
) -> dict[str, Any]:
    """Consulta KPIs, distribuição de classes e série temporal para o dashboard de Manutenção Preditiva."""
    return get_api_client().get(
        "/maintenance/sensors",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "start_date": start_date,
            "end_date": end_date,
            "sensor": sensor,
            "data_source": data_source,
            "limit": limit,
        },
    )


def get_equipment_overview(data_source: str = "all") -> dict[str, Any]:
    """Consulta estado consolidado das células monitoradas na API."""
    return get_api_client().get(
        "/maintenance/equipment",
        params={"data_source": data_source},
    )


def get_latest_sensor_readings(data_source: str = "all") -> dict[str, Any]:
    """Consulta a última leitura dos sensores de cada equipamento na API."""
    return get_api_client().get(
        "/sensors/latest",
        params={"data_source": data_source},
    )


def predict_sensor_reading(reading_payload: dict[str, Any], persist: bool = True) -> dict[str, Any]:
    """Envia uma leitura de sensores para classificação no endpoint POST /api/v1/maintenance/predict."""
    body = {
        "timestamp": reading_payload.get("timestamp"),
        "id_celula": reading_payload["id_celula"],
        "liga_metalica": reading_payload["liga_metalica"],
        "temperatura_fuso_c": reading_payload.get("temperatura_fuso_c"),
        "vibracao_triaxial_rms_mms": reading_payload.get("vibracao_triaxial_rms_mms"),
        "torque_fuso_nm": reading_payload.get("torque_fuso_nm"),
        "vazao_refrigerante_lmin": reading_payload.get("vazao_refrigerante_lmin"),
        "corrente_estator_amp": reading_payload.get("corrente_estator_amp"),
        "pressao_hidraulica_bar": reading_payload.get("pressao_hidraulica_bar"),
        "nivel_ruido_db": reading_payload.get("nivel_ruido_db"),
        "data_source": reading_payload.get("data_source", "historical"),
        "persist": persist,
    }
    return get_api_client().post("/maintenance/predict", json_body=body)


def get_latest_predictions(equipment_id: str | None = None, data_source: str | None = None) -> dict[str, Any]:
    """Consulta as últimas previsões disponíveis na API."""
    return get_api_client().get(
        "/maintenance/latest",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "data_source": None if data_source in (None, "all") else data_source,
        },
    )


def get_prediction_history(
    equipment_id: str | None = None,
    data_source: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Consulta o histórico de previsões persistidas na API."""
    return get_api_client().get(
        "/maintenance/history",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "data_source": None if data_source in (None, "all") else data_source,
            "limit": limit,
        },
    )


def get_maintenance_alerts(
    equipment_id: str | None = None,
    data_source: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Consulta os alertas de manutenção registrados na API."""
    return get_api_client().get(
        "/maintenance/alerts",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "data_source": None if data_source in (None, "all") else data_source,
            "limit": limit,
        },
    )
