"""Schemas de saúde, prontidão e diagnóstico do sistema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Estado do processo HTTP ('ok').")
    service: str = Field(..., description="Nome do serviço.")
    version: str = Field(..., description="Versão da API.")
    timestamp_utc: str = Field(..., description="Timestamp UTC da verificação.")


class ReadinessResponse(BaseModel):
    ready: bool = Field(..., description="Indica se os recursos essenciais estão disponíveis.")
    status: str = Field(..., description="'ready' ou 'degraded'.")
    database_ready: bool
    dataset_ready: bool
    tabular_model_ready: bool
    vision_models_ready: bool
    issues: list[str] = Field(default_factory=list)
    timestamp_utc: str


class SystemStatusResponse(BaseModel):
    api_status: str
    version: str
    timestamp_utc: str
    database: dict[str, Any]
    datasets: dict[str, Any]
    models: dict[str, Any]
    simulation: dict[str, Any]
    oee_service: dict[str, Any]
    startup_errors: list[str] = Field(default_factory=list)

