"""Rotas REST para ingestão e consulta de leituras de Sensores e Telemetria."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from backend.dependencies import get_sensor_service
from backend.schemas.sensors import SensorReadingCreate, SensorReadingResponse
from backend.services.sensor_service import SensorService

router = APIRouter(prefix="/sensors", tags=["Sensores e Telemetria"])

SourceQuery = Literal["historical", "simulated", "api", "all"]


@router.post(
    "/readings",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recebe, valida e persiste uma leitura de sensores (com inferência opcional)",
)
def create_sensor_reading(
    payload: SensorReadingCreate,
    service: SensorService = Depends(get_sensor_service),
) -> SensorReadingResponse:
    try:
        data = payload.model_dump()
        run_pred = bool(data.pop("run_prediction", True))
        result = service.ingest_reading(data, run_prediction=run_pred)
        return SensorReadingResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/latest", summary="Consulta a última leitura de cada equipamento")
def get_latest_sensor_readings(
    data_source: SourceQuery = Query(default="all"),
    service: SensorService = Depends(get_sensor_service),
) -> dict[str, Any]:
    try:
        return service.get_latest_readings(data_source=data_source)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/history", summary="Consulta histórico de leituras de sensores por célula e período")
def get_sensor_history(
    equipment_id: str | None = Query(default=None),
    data_source: SourceQuery = Query(default="historical"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    service: SensorService = Depends(get_sensor_service),
) -> dict[str, Any]:
    try:
        return service.get_history(
            equipment_id=equipment_id,
            data_source=data_source,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/equipment/{equipment_id}", summary="Consulta telemetria resumida de uma célula específica")
def get_equipment_telemetry(
    equipment_id: str = Path(..., description="Identificador da célula (CEL-201 a CEL-204)."),
    data_source: SourceQuery = Query(default="historical"),
    service: SensorService = Depends(get_sensor_service),
) -> dict[str, Any]:
    try:
        return service.get_equipment_telemetry(equipment_id=equipment_id, data_source=data_source)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

