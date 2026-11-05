"""Camada de banco de dados SQLite para o ecossistema VulcanTech."""

from .db import DEFAULT_DB_PATH, check_db_health, db_session, get_connection, init_db, resolve_sqlite_path
from .repositories import MaintenanceRepository, OEERepository, SensorRepository, VisionRepository

__all__ = [
    "DEFAULT_DB_PATH",
    "resolve_sqlite_path",
    "get_connection",
    "db_session",
    "init_db",
    "check_db_health",
    "SensorRepository",
    "MaintenanceRepository",
    "VisionRepository",
    "OEERepository",
]

