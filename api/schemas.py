"""Contratos e schemas Pydantic de telemetria industrial e predição VulcanTech."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CELULAS = {"CEL-201", "CEL-202", "CEL-203", "CEL-204"}
LIGAS = {"Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V"}
REGIMES = ("Producao_Normal", "Usinagem_Pesada", "Alta_Velocidade")


class SensorReading(BaseModel):
    timestamp: datetime
    id_celula: str = Field(pattern=r"^CEL-20[1-4]$", description="Identificador da célula CNC")
    # Compatibilidade com campo genérico
    id_equipamento: str | None = None
    liga_metalica: Literal["Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V"]
    modo_operacao: Literal["Producao_Normal", "Usinagem_Pesada", "Alta_Velocidade"] = "Producao_Normal"
    temperatura_fuso_c: float = Field(ge=-20.0, le=250.0, description="Temperatura do fuso (°C)")
    vibracao_triaxial_rms_mms: float = Field(ge=0.0, le=100.0, description="Vibração triaxial RMS (mm/s)")
    torque_fuso_nm: float = Field(ge=0.0, le=400.0, description="Torque no fuso (Nm)")
    vazao_refrigerante_lmin: float = Field(ge=0.0, le=100.0, description="Vazão de fluido de corte (L/min)")
    corrente_estator_amp: float = Field(ge=0.0, le=250.0, description="Corrente do estator (A)")
    pressao_hidraulica_bar: float = Field(ge=0.0, le=250.0, description="Pressão do circuito hidráulico (bar)")
    nivel_ruido_db: float = Field(ge=0.0, le=160.0, description="Pressão acústica / ruído operacional (dB)")
    
    # Metadados operacionais e de simulação
    regime_operacional: Literal["Producao_Normal", "Usinagem_Pesada", "Alta_Velocidade"] | None = None
    regime_anterior: str | None = None
    regime_alterado_em: datetime | None = None
    origem_leitura: Literal["simulada", "real", "desconhecida"] = Field(
        default="simulada",
        description="Distingue telemetria sintética de leitura física de campo.",
    )
    perfil_sintetico: Literal["nominal", "anormal"] | None = None
    perfil_anomalia: Literal["A", "B", "C"] | None = None

    @field_validator("timestamp", "regime_alterado_em")
    @classmethod
    def timestamp_without_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=None) if value.tzinfo else value

    @model_validator(mode="after")
    def sync_fields(self) -> "SensorReading":
        if not self.id_equipamento:
            self.id_equipamento = self.id_celula
        if self.regime_operacional is None:
            self.regime_operacional = self.modo_operacao
        if self.perfil_sintetico == "nominal":
            self.perfil_anomalia = None
        return self


class BatchRequest(BaseModel):
    leituras: list[SensorReading] = Field(min_length=1, max_length=500)


class RegimeCommand(BaseModel):
    """Comando de regime operacional enviado pelo dashboard ou CLP."""
    regime: Literal["Producao_Normal", "Usinagem_Pesada", "Alta_Velocidade"]

