"""Injeção de dependências e singletons controlados para o FastAPI."""

from __future__ import annotations

from dataclasses import dataclass

from backend.config import Settings, get_settings
from backend.services.ml_service import MLService
from backend.services.oee_service import OEEService
from backend.services.sensor_service import SensorService
from backend.services.simulation_service import SimulationService
from backend.services.vision_service import VisionService


@dataclass
class ServiceContainer:
    settings: Settings
    ml_service: MLService
    vision_service: VisionService
    oee_service: OEEService
    sensor_service: SensorService
    simulation_service: SimulationService
    startup_errors: list[str]


_CONTAINER: ServiceContainer | None = None


def build_container(settings: Settings | None = None) -> ServiceContainer:
    cfg = settings or get_settings()
    ml = MLService(cfg)
    vision = VisionService(cfg)
    oee = OEEService(cfg)
    sensor = SensorService(cfg, ml_service=ml)
    sim = SimulationService(cfg, sensor_service=sensor, oee_service=oee)
    return ServiceContainer(
        settings=cfg,
        ml_service=ml,
        vision_service=vision,
        oee_service=oee,
        sensor_service=sensor,
        simulation_service=sim,
        startup_errors=[],
    )


def get_container() -> ServiceContainer:
    global _CONTAINER
    current = get_settings()
    if (
        _CONTAINER is None
        or _CONTAINER.settings.database_url != current.database_url
        or _CONTAINER.settings.model_dir != current.model_dir
    ):
        _CONTAINER = build_container(current)
    return _CONTAINER


def reset_container(settings: Settings | None = None) -> ServiceContainer:
    global _CONTAINER
    if _CONTAINER is not None:
        try:
            _CONTAINER.simulation_service.stop()
        except Exception:
            pass
    _CONTAINER = build_container(settings)
    return _CONTAINER


def get_ml_service() -> MLService:
    return get_container().ml_service


def get_vision_service() -> VisionService:
    return get_container().vision_service


def get_oee_service() -> OEEService:
    return get_container().oee_service


def get_sensor_service() -> SensorService:
    return get_container().sensor_service


def get_simulation_service() -> SimulationService:
    return get_container().simulation_service

