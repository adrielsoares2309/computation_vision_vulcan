"""Serviço do frontend para consumo dos endpoints de OEE e Simulação via API FastAPI."""

from __future__ import annotations

from typing import Any

from frontend.services.api_client import get_api_client


def get_oee_snapshot(
    equipment_id: str | None = None,
    shift: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    data_source: str = "historical",
) -> dict[str, Any]:
    """Consulta o resumo de indicadores OEE na API."""
    client = get_api_client()
    return client.get(
        "/oee/summary",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "shift": None if shift in (None, "Todos") else shift,
            "start_date": start_date,
            "end_date": end_date,
            "data_source": data_source,
        },
    )


def get_oee_history(
    equipment_id: str | None = None,
    shift: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    data_source: str = "historical",
    limit: int = 200,
) -> dict[str, Any]:
    """Consulta a série temporal de lotes OEE na API."""
    client = get_api_client()
    return client.get(
        "/oee/history",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "shift": None if shift in (None, "Todos") else shift,
            "start_date": start_date,
            "end_date": end_date,
            "data_source": data_source,
            "limit": limit,
        },
    )


def get_oee_by_equipment(
    shift: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    data_source: str = "historical",
) -> dict[str, Any]:
    """Consulta os indicadores OEE agrupados por equipamento na API."""
    client = get_api_client()
    return client.get(
        "/oee/equipment",
        params={
            "shift": None if shift in (None, "Todos") else shift,
            "start_date": start_date,
            "end_date": end_date,
            "data_source": data_source,
        },
    )


def get_oee_downtime(
    equipment_id: str | None = None,
    shift: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    data_source: str = "historical",
) -> dict[str, Any]:
    """Consulta paradas e eventos operacionais na API."""
    client = get_api_client()
    return client.get(
        "/oee/downtime",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "shift": None if shift in (None, "Todos") else shift,
            "start_date": start_date,
            "end_date": end_date,
            "data_source": data_source,
        },
    )


def get_oee_events(
    equipment_id: str | None = None,
    shift: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    data_source: str = "all",
    limit: int = 100,
) -> dict[str, Any]:
    """Lista os registros de produção e paradas na API."""
    client = get_api_client()
    return client.get(
        "/oee/events",
        params={
            "equipment_id": None if equipment_id in (None, "Todas") else equipment_id,
            "shift": None if shift in (None, "Todos") else shift,
            "start_date": start_date,
            "end_date": end_date,
            "data_source": data_source,
            "limit": limit,
        },
    )


def get_simulation_status() -> dict[str, Any]:
    return get_api_client().get("/simulation/status")


def start_simulation(mode: str = "MISTO", interval_seconds: float = 5.0, generate_initial_batch: int = 4) -> dict[str, Any]:
    return get_api_client().post(
        "/simulation/start",
        json_body={
            "mode": mode,
            "interval_seconds": interval_seconds,
            "generate_initial_batch": generate_initial_batch,
        },
    )


def stop_simulation() -> dict[str, Any]:
    return get_api_client().post("/simulation/stop")


def set_simulation_mode(mode: str) -> dict[str, Any]:
    return get_api_client().post("/simulation/mode", json_body={"mode": mode})


def step_simulation(mode: str | None = None, equipment_id: str | None = None, count: int = 4) -> dict[str, Any]:
    return get_api_client().post(
        "/simulation/step",
        json_body={"mode": mode, "equipment_id": equipment_id, "count": count},
    )
