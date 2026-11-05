"""Rotas REST para cálculo e consulta de OEE (Overall Equipment Effectiveness)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.dependencies import get_oee_service
from backend.schemas.oee import (
    OEEDowntimeResponse,
    OEEEquipmentResponse,
    OEEHistoryResponse,
    OEESummaryResponse,
    ProductionEventCreate,
)
from backend.services.oee_service import OEEService

router = APIRouter(prefix="/oee", tags=["OEE — Eficiência Operacional"])

SourceQuery = Literal["historical", "simulated", "api", "all"]


@router.get("/summary", response_model=OEESummaryResponse, summary="Consulta os indicadores consolidados de OEE")
def get_oee_summary(
    equipment_id: str | None = Query(default=None, description="Célula (CEL-201 a CEL-204 ou Todas)."),
    shift: str | None = Query(default=None, description="Turno (MANHA, TARDE, NOITE ou Todos)."),
    start_date: str | None = Query(default=None, description="Data inicial YYYY-MM-DD."),
    end_date: str | None = Query(default=None, description="Data final YYYY-MM-DD."),
    data_source: SourceQuery = Query(
        default="historical",
        description="Origem dos dados: 'historical' (N/D para produção), 'simulated', 'api' ou 'all'.",
    ),
    service: OEEService = Depends(get_oee_service),
) -> OEESummaryResponse:
    try:
        result = service.get_summary(
            equipment_id=equipment_id,
            shift=shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
        )
        return OEESummaryResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/history", response_model=OEEHistoryResponse, summary="Consulta série histórica de lotes OEE")
def get_oee_history(
    equipment_id: str | None = Query(default=None),
    shift: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    data_source: SourceQuery = Query(default="historical"),
    limit: int = Query(default=200, ge=1, le=1000),
    service: OEEService = Depends(get_oee_service),
) -> OEEHistoryResponse:
    result = service.get_history(
        equipment_id=equipment_id,
        shift=shift,
        start_date=start_date,
        end_date=end_date,
        data_source=data_source,
        limit=limit,
    )
    return OEEHistoryResponse(**result)


@router.get("/equipment", response_model=OEEEquipmentResponse, summary="Consulta indicadores OEE por equipamento")
def get_oee_by_equipment(
    shift: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    data_source: SourceQuery = Query(default="historical"),
    service: OEEService = Depends(get_oee_service),
) -> OEEEquipmentResponse:
    result = service.get_by_equipment(
        shift=shift,
        start_date=start_date,
        end_date=end_date,
        data_source=data_source,
    )
    return OEEEquipmentResponse(**result)


@router.get("/downtime", response_model=OEEDowntimeResponse, summary="Consulta análise de paradas por motivo e célula")
def get_oee_downtime(
    equipment_id: str | None = Query(default=None),
    shift: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    data_source: SourceQuery = Query(default="historical"),
    service: OEEService = Depends(get_oee_service),
) -> OEEDowntimeResponse:
    result = service.get_downtime_analysis(
        equipment_id=equipment_id,
        shift=shift,
        start_date=start_date,
        end_date=end_date,
        data_source=data_source,
    )
    return OEEDowntimeResponse(**result)


@router.get("/events", summary="Lista eventos de produção e paradas registrados")
def get_oee_events(
    equipment_id: str | None = Query(default=None),
    shift: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    data_source: SourceQuery = Query(default="all"),
    limit: int = Query(default=100, ge=1, le=500),
    service: OEEService = Depends(get_oee_service),
) -> dict[str, Any]:
    return service.get_events(
        equipment_id=equipment_id,
        shift=shift,
        start_date=start_date,
        end_date=end_date,
        data_source=data_source,
        limit=limit,
    )


@router.post("/events", status_code=status.HTTP_201_CREATED, summary="Registra um lote de produção/parada e calcula seu OEE")
def create_oee_event(
    payload: ProductionEventCreate,
    service: OEEService = Depends(get_oee_service),
) -> dict[str, Any]:
    try:
        return service.record_production_event(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/current", summary="Consulta o OEE atual consolidado de fábrica")
def get_current_oee(service: OEEService = Depends(get_oee_service)) -> dict[str, Any]:
    res = service.get_summary(data_source="all")
    if not res.get("available"):
        from src.oee.calculator import calculate_oee_from_counts
        res = calculate_oee_from_counts(480.0, 32.0, 1.8, 240, good_count=230)
    return res


@router.post("/calculate", summary="Calcula OEE sob demanda a partir de parâmetros de produção")
def calculate_oee_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    from src.oee.calculator import calculate_oee_from_counts
    try:
        planned_time = float(payload.get("planned_time_min", 480.0))
        downtime = float(payload.get("downtime_min", 0.0))
        cycle_time = float(payload.get("ideal_cycle_time_min", 1.0))
        total_count = int(payload.get("total_count", 0))
        good_count = payload.get("good_count")
        rejected_count = payload.get("rejected_count")

        return calculate_oee_from_counts(
            planned_time_min=planned_time,
            downtime_min=downtime,
            ideal_cycle_time_min=cycle_time,
            total_count=total_count,
            good_count=int(good_count) if good_count is not None else None,
            rejected_count=int(rejected_count) if rejected_count is not None else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/impact", summary="Calcula o impacto preditivo no OEE e perdas financeiras")
def calculate_oee_impact_endpoint(
    payload: dict[str, Any],
    service: OEEService = Depends(get_oee_service),
) -> dict[str, Any]:
    from src.oee.calculator import calculate_oee_from_counts
    from src.oee.predictive_impact import calcular_impacto_preditivo_oee
    try:
        oee_base = payload.get("oee_base")
        if not oee_base:
            summary = service.get_summary(data_source="all")
            if summary.get("available") and "metrics" in summary:
                oee_base = {"available": True, **summary["metrics"]}
            else:
                oee_base = calculate_oee_from_counts(480.0, 30.0, 1.5, 280, good_count=265)
        elif "metrics" in oee_base:
            oee_base = {"available": True, **oee_base["metrics"]}

        tipo_falha = int(payload.get("tipo_falha_previsto", 1))
        probabilidade = float(payload.get("probabilidade_falha", 0.85))
        anomalia = float(payload.get("score_anomalia", 0.70))

        return calcular_impacto_preditivo_oee(
            oee_atual=oee_base,
            tipo_falha_previsto=tipo_falha,
            probabilidade_falha=probabilidade,
            score_anomalia=anomalia,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

