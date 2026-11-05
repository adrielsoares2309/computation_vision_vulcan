"""Rotas REST para Manutenção Preditiva e Classificação Multiclasse de Sensores."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.dependencies import get_ml_service
from backend.schemas.predictive_maintenance import (
    BatchPredictionRequest,
    MaintenancePredictionOutput,
    SensorFeatureInput,
)
from backend.services.ml_service import MLService

router = APIRouter(prefix="/maintenance", tags=["Manutenção Preditiva"])


@router.get("/metadata", summary="Retorna metadados reais do modelo tabular, features, métricas e limitações")
def get_maintenance_metadata(service: MLService = Depends(get_ml_service)) -> dict[str, Any]:
    try:
        meta = service.get_metadata()
        availability = service.check_availability()
        return {**meta, "availability": availability}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post(
    "/predict",
    response_model=MaintenancePredictionOutput,
    summary="Executa inferência contemporânea sobre uma leitura de sensores",
)
def predict_maintenance(
    payload: SensorFeatureInput,
    service: MLService = Depends(get_ml_service),
) -> MaintenancePredictionOutput:
    try:
        data = payload.model_dump()
        persist = bool(data.pop("persist", True))
        result = service.predict_single(data, persist=persist)
        return MaintenancePredictionOutput(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/predict-batch",
    response_model=list[MaintenancePredictionOutput],
    summary="Executa inferência em lote para múltiplas leituras de sensores",
)
def predict_maintenance_batch(
    payload: BatchPredictionRequest,
    service: MLService = Depends(get_ml_service),
) -> list[MaintenancePredictionOutput]:
    try:
        rows = [item.model_dump() for item in payload.readings]
        results = service.predict_batch(rows, persist=payload.persist)
        return [MaintenancePredictionOutput(**r) for r in results]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/latest", summary="Consulta as últimas previsões disponíveis por equipamento")
def get_latest_maintenance(
    equipment_id: str | None = Query(default=None),
    data_source: str | None = Query(default=None),
    service: MLService = Depends(get_ml_service),
) -> dict[str, Any]:
    try:
        return service.get_latest_predictions(equipment_id=equipment_id, data_source=data_source)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/history", summary="Consulta histórico de previsões persistidas no banco SQLite")
def get_maintenance_history(
    equipment_id: str | None = Query(default=None),
    data_source: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: MLService = Depends(get_ml_service),
) -> dict[str, Any]:
    return service.get_prediction_history(equipment_id=equipment_id, data_source=data_source, limit=limit)


@router.get("/alerts", summary="Consulta alertas de manutenção gerados por classificações de falha")
def get_maintenance_alerts(
    equipment_id: str | None = Query(default=None),
    data_source: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: MLService = Depends(get_ml_service),
) -> dict[str, Any]:
    return service.get_alerts(equipment_id=equipment_id, data_source=data_source, limit=limit)


@router.get("/equipment", summary="Consulta estado consolidado das células de manufatura")
def get_maintenance_equipment(
    data_source: str = Query(default="all"),
    service: MLService = Depends(get_ml_service),
) -> dict[str, Any]:
    try:
        return service.get_equipment_overview(data_source=data_source)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/sensors", summary="Consulta KPIs, distribuição de falhas e séries temporais de sensores")
def get_maintenance_sensors(
    equipment_id: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    sensor: str = Query(default="temperatura_fuso_c"),
    data_source: str = Query(default="historical"),
    limit: int = Query(default=500, ge=20, le=2000),
    service: MLService = Depends(get_ml_service),
) -> dict[str, Any]:
    try:
        return service.get_maintenance_sensors_summary(
            equipment_id=equipment_id,
            start_date=start_date,
            end_date=end_date,
            sensor=sensor,
            data_source=data_source,
            limit=limit,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

