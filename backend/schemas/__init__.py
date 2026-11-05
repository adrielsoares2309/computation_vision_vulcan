"""Exportação dos schemas Pydantic da API VulcanTech."""

from .common import DataSourceType, ErrorDetail
from .health import HealthResponse, ReadinessResponse, SystemStatusResponse
from .oee import OEEDowntimeResponse, OEEEquipmentResponse, OEEHistoryResponse, OEESummaryResponse, ProductionEventCreate
from .predictive_maintenance import BatchPredictionRequest, MaintenancePredictionOutput, SensorFeatureInput
from .sensors import SensorReadingCreate, SensorReadingResponse
from .simulation import (
    SimulationModeRequest,
    SimulationStartRequest,
    SimulationStatusResponse,
    SimulationStepRequest,
)
from .vision import VisionHistoryResponse, VisionPredictionResponse, VisionSummaryResponse

__all__ = [
    "DataSourceType",
    "ErrorDetail",
    "HealthResponse",
    "ReadinessResponse",
    "SystemStatusResponse",
    "ProductionEventCreate",
    "OEESummaryResponse",
    "OEEHistoryResponse",
    "OEEEquipmentResponse",
    "OEEDowntimeResponse",
    "VisionPredictionResponse",
    "VisionHistoryResponse",
    "VisionSummaryResponse",
    "SensorFeatureInput",
    "BatchPredictionRequest",
    "MaintenancePredictionOutput",
    "SensorReadingCreate",
    "SensorReadingResponse",
    "SimulationStartRequest",
    "SimulationModeRequest",
    "SimulationStepRequest",
    "SimulationStatusResponse",
]

