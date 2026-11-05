"""Schemas Pydantic para controle do Simulador Industrial."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SimulationModeLiteral = Literal[
    "NORMAL",
    "DESGASTE_FERRAMENTA",
    "FALHA_REFRIGERACAO",
    "DESALINHAMENTO_TRINCA",
    "MISTO",
]


class SimulationStartRequest(BaseModel):
    mode: SimulationModeLiteral = Field(default="MISTO", description="Modo operacional inicial do simulador.")
    interval_seconds: float = Field(default=5.0, ge=1.0, le=60.0, description="Intervalo em segundos entre ciclos.")
    generate_initial_batch: int = Field(
        default=4,
        ge=0,
        le=20,
        description="Quantidade de ciclos simulados gerados imediatamente ao iniciar.",
    )


class SimulationModeRequest(BaseModel):
    mode: SimulationModeLiteral = Field(..., description="Novo modo operacional do simulador.")


class SimulationStepRequest(BaseModel):
    mode: SimulationModeLiteral | None = Field(default=None, description="Modo opcional para o ciclo avulso.")
    equipment_id: str | None = Field(default=None, description="Célula específica opcional (CEL-201 a CEL-204).")
    count: int = Field(default=1, ge=1, le=20, description="Quantidade de leituras/eventos a gerar.")


class SimulationStatusResponse(BaseModel):
    running: bool
    mode: str
    interval_seconds: float
    cycles_completed: int
    started_at_utc: str | None = None
    last_cycle_at_utc: str | None = None
    last_event: dict[str, Any] | None = None
    data_source_tag: str = "simulated"

