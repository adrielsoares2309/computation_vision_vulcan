"""Configuração centralizada do backend FastAPI VulcanTech."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _parse_origins(raw: str) -> list[str]:
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items or ["http://localhost:8501", "http://127.0.0.1:8501"]


@dataclass
class Settings:
    """Configurações carregadas de variáveis de ambiente com padrões seguros para o MVP."""

    app_name: str = "VulcanTech Smart Metals S.A. — API Industrial"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    api_base_url: str = field(default_factory=lambda: os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///database/vulcantech.db"))
    frontend_origins: list[str] = field(
        default_factory=lambda: _parse_origins(
            os.getenv("FRONTEND_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
        )
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    model_dir: Path = field(
        default_factory=lambda: (
            Path(os.getenv("MODEL_DIR", "models"))
            if Path(os.getenv("MODEL_DIR", "models")).is_absolute()
            else (ROOT / os.getenv("MODEL_DIR", "models")).resolve()
        )
    )
    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    max_upload_size_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))
    )
    simulation_interval_seconds: float = field(
        default_factory=lambda: float(os.getenv("SIMULATION_INTERVAL_SECONDS", "5.0"))
    )


def get_settings() -> Settings:
    """Retorna uma instância de configuração atualizada conforme variáveis de ambiente."""
    return Settings()

