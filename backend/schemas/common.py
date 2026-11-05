"""Schemas comuns de resposta, erro e metadados de origem."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DataSourceType = Literal["historical", "simulated", "api", "all", "unavailable"]


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Código identificador do erro.")
    message: str = Field(..., description="Mensagem explicativa segura para o cliente.")
    details: dict[str, Any] | list[Any] | None = Field(default=None, description="Detalhes técnicos adicionais.")

