"""Schemas Pydantic para os endpoints de OEE."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.data.validator import VALID_ALLOYS, VALID_CELLS


class ProductionEventCreate(BaseModel):
    timestamp: str | None = Field(default=None, description="Timestamp ISO-8601; se omitido, utiliza o horário atual UTC.")
    id_celula: str = Field(..., description="Célula de manufatura (CEL-201 a CEL-204).")
    liga_metalica: str = Field(..., description="Liga processada.")
    shift: Literal["MANHA", "TARDE", "NOITE"] | None = Field(default=None, description="Turno operacional.")
    planned_time_min: float = Field(..., gt=0, le=1440, description="Tempo planejado em minutos.")
    downtime_min: float = Field(..., ge=0, le=1440, description="Tempo de parada em minutos.")
    ideal_cycle_time_min: float = Field(default=0.25, gt=0, le=120, description="Tempo de ciclo ideal em minutos por peça.")
    total_count: int = Field(..., ge=0, le=100000, description="Quantidade total produzida.")
    good_count: int = Field(..., ge=0, le=100000, description="Quantidade de unidades aprovadas.")
    downtime_reason: str | None = Field(default=None, max_length=240, description="Motivo da parada, quando houver.")
    associated_fault_class: int = Field(default=0, ge=0, le=3, description="Classe de falha associada (0 a 3).")
    data_source: Literal["api", "simulated"] = Field(default="api", description="Origem do registro operacional.")

    @field_validator("id_celula")
    @classmethod
    def validate_cell(cls, v: str) -> str:
        val = v.strip().upper()
        if val not in VALID_CELLS:
            raise ValueError(f"id_celula inválido ({v}). Valores aceitos: {sorted(VALID_CELLS)}.")
        return val

    @field_validator("liga_metalica")
    @classmethod
    def validate_alloy(cls, v: str) -> str:
        val = v.strip()
        if val not in VALID_ALLOYS:
            raise ValueError(f"liga_metalica inválida ({v}). Valores aceitos: {sorted(VALID_ALLOYS)}.")
        return val


class OEESummaryResponse(BaseModel):
    available: bool
    status: str
    reason: str | None = None
    data_source: str
    records_count: int = 0
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float | int | None]
    last_timestamp: str | None = None
    notes: list[str] = Field(default_factory=list)


class OEEHistoryResponse(BaseModel):
    available: bool
    data_source: str
    reason: str | None = None
    series: list[dict[str, Any]] = Field(default_factory=list)


class OEEEquipmentResponse(BaseModel):
    available: bool
    data_source: str
    reason: str | None = None
    equipment: list[dict[str, Any]] = Field(default_factory=list)


class OEEDowntimeResponse(BaseModel):
    available: bool
    data_source: str
    total_downtime_min: float = 0.0
    by_reason: list[dict[str, Any]] = Field(default_factory=list)
    recent_stops: list[dict[str, Any]] = Field(default_factory=list)

