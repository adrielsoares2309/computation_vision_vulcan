"""Schemas Pydantic para Sensores e Telemetria Industrial."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.data.validator import VALID_ALLOYS, VALID_CELLS


class SensorReadingCreate(BaseModel):
    timestamp: str | None = Field(default=None, description="Timestamp ISO-8601 da leitura.")
    id_celula: str = Field(..., description="Identificador da célula (CEL-201 a CEL-204).")
    liga_metalica: str = Field(..., description="Liga metálica processada.")
    temperatura_fuso_c: float | None = Field(default=None, ge=-50.0, le=1200.0, description="Temperatura do fuso (°C).")
    vibracao_triaxial_rms_mms: float | None = Field(default=None, ge=-120.0, le=100.0, description="Vibração triaxial RMS (mm/s).")
    torque_fuso_nm: float = Field(..., ge=0.0, le=1000.0, description="Torque do fuso (Nm).")
    vazao_refrigerante_lmin: float | None = Field(default=None, ge=-5.0, le=200.0, description="Vazão do refrigerante (L/min).")
    corrente_estator_amp: float = Field(..., ge=0.0, le=300.0, description="Corrente do estator (A).")
    pressao_hidraulica_bar: float | None = Field(default=None, ge=-10.0, le=500.0, description="Pressão hidráulica (bar).")
    nivel_ruido_db: float = Field(..., ge=0.0, le=200.0, description="Nível de ruído (dB).")
    data_source: Literal["api", "simulated"] = Field(default="api", description="Origem do dado.")
    run_prediction: bool = Field(default=True, description="Executa inferência automática ao registrar leitura.")

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


class SensorReadingResponse(BaseModel):
    reading_id: int
    reading: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    prediction: dict[str, Any] | None = None

