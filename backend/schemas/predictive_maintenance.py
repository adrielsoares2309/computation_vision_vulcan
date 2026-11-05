"""Schemas Pydantic para Manutenção Preditiva e Classificação Tabular."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.data.validator import VALID_ALLOYS, VALID_CELLS


class SensorFeatureInput(BaseModel):
    timestamp: str | None = Field(default=None, description="Timestamp da leitura (opcional; excluído das features do modelo).")
    id_celula: str = Field(..., description="Célula de manufatura (CEL-201 a CEL-204).")
    liga_metalica: str = Field(..., description="Liga metálica processada.")
    temperatura_fuso_c: float | None = Field(default=None, ge=-50.0, le=1200.0, description="Temperatura do fuso (°C).")
    vibracao_triaxial_rms_mms: float | None = Field(default=None, ge=-120.0, le=100.0, description="Vibração triaxial RMS (mm/s).")
    torque_fuso_nm: float | None = Field(default=None, ge=0.0, le=1000.0, description="Torque aplicado ao fuso (Nm).")
    vazao_refrigerante_lmin: float | None = Field(default=None, ge=-5.0, le=200.0, description="Vazão do fluido refrigerante (L/min).")
    corrente_estator_amp: float | None = Field(default=None, ge=0.0, le=300.0, description="Corrente do motor do estator (A).")
    pressao_hidraulica_bar: float | None = Field(default=None, ge=-10.0, le=500.0, description="Pressão hidráulica (bar).")
    nivel_ruido_db: float | None = Field(default=None, ge=0.0, le=200.0, description="Emissão acústica no corte (dB).")
    data_source: Literal["api", "simulated", "historical"] = Field(default="api", description="Origem da leitura.")
    persist: bool = Field(default=True, description="Indica se a previsão deve ser persistida no banco SQLite.")

    @field_validator("id_celula")
    @classmethod
    def validate_cell(cls, v: str) -> str:
        val = v.strip().upper()
        if val not in VALID_CELLS:
            raise ValueError(f"id_celula inválido ({v}). Valores suportados: {sorted(VALID_CELLS)}.")
        return val

    @field_validator("liga_metalica")
    @classmethod
    def validate_alloy(cls, v: str) -> str:
        val = v.strip()
        if val not in VALID_ALLOYS:
            raise ValueError(f"liga_metalica inválida ({v}). Valores suportados: {sorted(VALID_ALLOYS)}.")
        return val


class BatchPredictionRequest(BaseModel):
    readings: list[SensorFeatureInput] = Field(..., min_length=1, max_length=500)
    persist: bool = Field(default=False)


class MaintenancePredictionOutput(BaseModel):
    prediction_id: int | None = None
    equipment_id: str
    liga_metalica: str
    timestamp: str
    predicted_class_code: int
    predicted_class_name: str
    operational_state: Literal["NORMAL", "ALERTA_MANUTENCAO", "PARADA_RECOMENDADA"]
    recommended_action: Literal["MANTER_OPERACAO", "REDUZIR_VELOCIDADE_50%", "INTERROMPER_EMERGENCIA"]
    scores: dict[str, float] = Field(..., description="Probabilidades não calibradas por classe.")
    calibrated_probabilities: bool = False
    model_name: str
    model_trained_at_utc: str | None = None
    data_source: str
    inference_status: str = "completed"
    interpretation: str
    warnings: list[str] = Field(default_factory=list)

