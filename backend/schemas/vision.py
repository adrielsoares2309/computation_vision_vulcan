"""Schemas Pydantic para Visão Computacional (inspeção de soldas)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VisionPredictionResponse(BaseModel):
    inspection_id: str = Field(..., description="Identificador único da inspeção.")
    piece_id: str = Field(..., description="Identificador da peça inspecionada.")
    filename: str = Field(..., description="Nome original do arquivo enviado.")
    modality: Literal["visual", "termica"] = Field(..., description="Modalidade utilizada na inferência.")
    predicted_class: Literal["APROVADA", "REPROVADA", "INDETERMINADA"] = Field(..., description="Classificação prevista.")
    class_scores: dict[str, float] = Field(..., description="Escores relativos de similaridade aos protótipos.")
    score_type: str = Field(..., description="Tipo de escore (não é probabilidade calibrada).")
    timestamp: str = Field(..., description="Timestamp ISO-8601 da inspeção.")
    inference_status: str = Field(default="completed", description="Estado da execução da inferência.")
    model_version: str = Field(..., description="Versão do descritor/modelo de visão.")
    model_status: str = Field(..., description="Status do modelo ('experimental' ou 'not_industrially_validated').")
    experimental: bool = Field(default=True, description="Indica se o modelo é experimental.")
    validated_for_industrial_use: bool = Field(default=False, description="Indica se há validação industrial.")
    data_source: str = Field(default="api", description="Origem da inspeção.")
    warnings: list[str] = Field(default_factory=list, description="Avisos técnicos e limitações do modelo.")


class VisionHistoryResponse(BaseModel):
    count: int
    items: list[dict[str, Any]] = Field(default_factory=list)


class VisionSummaryResponse(BaseModel):
    total_inspections: int
    by_class: dict[str, int]
    by_modality: dict[str, int]
    experimental_model: bool = True
    validated_for_industrial_use: bool = False
    latest_inspection: dict[str, Any] | None = None

