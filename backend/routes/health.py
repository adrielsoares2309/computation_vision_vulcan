"""Rotas de saúde, prontidão e diagnóstico do sistema."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status

from backend.dependencies import ServiceContainer, get_container
from backend.schemas.health import HealthResponse, ReadinessResponse, SystemStatusResponse
from database.db import check_db_health

router = APIRouter(tags=["Saúde e Diagnóstico"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@router.get("/health", response_model=HealthResponse, summary="Verifica se o processo da API está ativo")
def health_check(container: ServiceContainer = Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=container.settings.app_name,
        version=container.settings.app_version,
        timestamp_utc=_utc_now(),
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Verifica prontidão de banco, dados e modelos")
def readiness_check(
    response: Response,
    container: ServiceContainer = Depends(get_container),
) -> ReadinessResponse:
    db_info = check_db_health(container.settings.database_url)
    ml_info = container.ml_service.check_availability()
    vision_info = container.vision_service.check_availability()

    db_ready = bool(db_info.get("available"))
    dataset_ready = bool(ml_info.get("dataset_available"))
    tabular_ready = bool(ml_info.get("available"))
    vision_ready = bool(vision_info.get("available"))

    issues: list[str] = []
    if not db_ready:
        issues.append(f"Banco SQLite indisponível: {db_info.get('error')}")
    if not dataset_ready:
        issues.append("Dataset tratado (Parquet/CSV) indisponível em data/processed.")
    if not tabular_ready:
        issues.append(ml_info.get("error") or "Modelo tabular indisponível.")
    if not vision_ready:
        issues.append(vision_info.get("error") or "Modelos de visão computacional indisponíveis.")

    ready = db_ready and dataset_ready and tabular_ready and vision_ready
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        ready=ready,
        status="ready" if ready else "degraded",
        database_ready=db_ready,
        dataset_ready=dataset_ready,
        tabular_model_ready=tabular_ready,
        vision_models_ready=vision_ready,
        issues=issues,
        timestamp_utc=_utc_now(),
    )


@router.get("/system/status", response_model=SystemStatusResponse, summary="Diagnóstico detalhado dos módulos do sistema")
def system_status(container: ServiceContainer = Depends(get_container)) -> SystemStatusResponse:
    db_info = check_db_health(container.settings.database_url)
    ml_info = container.ml_service.check_availability()
    vision_info = container.vision_service.check_availability()
    sim_info = container.simulation_service.get_status()
    oee_info = container.oee_service.check_status()

    parquet_exists = container.ml_service.parquet_path.is_file()
    csv_exists = container.ml_service.csv_path.is_file()

    return SystemStatusResponse(
        api_status="online",
        version=container.settings.app_version,
        timestamp_utc=_utc_now(),
        database=db_info,
        datasets={
            "processed_parquet_available": parquet_exists,
            "processed_csv_available": csv_exists,
            "active_source_file": (
                container.ml_service.parquet_path.name
                if parquet_exists
                else (container.ml_service.csv_path.name if csv_exists else None)
            ),
        },
        models={
            "tabular": ml_info,
            "vision": vision_info,
        },
        simulation=sim_info,
        oee_service=oee_info,
        startup_errors=list(container.startup_errors),
    )

