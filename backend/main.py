"""Ponto de entrada principal da API FastAPI — VulcanTech Smart Metals S.A."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.dependencies import get_container
from backend.routes import health, industrial, oee, predictive_maintenance, sensors, simulation, vision
from database.db import init_db


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("vulcantech.api")
    container = get_container()
    container.startup_errors.clear()

    try:
        db_path = init_db(settings.database_url)
        logger.info("Banco SQLite inicializado: %s", db_path.name)
    except Exception as exc:
        msg = f"Falha ao inicializar banco SQLite: {exc}"
        logger.error(msg)
        container.startup_errors.append(msg)

    try:
        if container.ml_service.model_path.is_file():
            container.ml_service.get_model()
            logger.info("Modelo tabular carregado com sucesso.")
        else:
            container.startup_errors.append("Modelo tabular não encontrado na inicialização.")
    except Exception as exc:
        msg = f"Falha ao carregar modelo tabular na inicialização: {exc}"
        logger.warning(msg)
        container.startup_errors.append(msg)

    try:
        for mod in ("visual", "termica"):
            if (container.vision_service.vision_dir / f"{mod}_model.joblib").is_file():
                container.vision_service.get_model_artifact(mod)
        logger.info("Modelos de visão computacional verificados.")
    except Exception as exc:
        msg = f"Falha ao carregar modelos de visão na inicialização: {exc}"
        logger.warning(msg)
        container.startup_errors.append(msg)

    yield

    try:
        container.simulation_service.stop()
    except Exception:
        pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API RESTful de integração industrial VulcanTech Smart Metals S.A. "
            "para OEE, Visão Computacional de Soldas, Manutenção Preditiva, Telemetria de Sensores e Simulação."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Authorization"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        sanitized_errors = []
        for err in exc.errors():
            sanitized_errors.append(
                {
                    "loc": list(err.get("loc", [])),
                    "msg": str(err.get("msg", "")),
                    "type": str(err.get("type", "")),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "code": "validation_error",
                "message": "Dados de entrada inválidos. Verifique os parâmetros e unidades informados.",
                "details": sanitized_errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("vulcantech.api").error("Erro interno tratado na requisição: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "internal_server_error",
                "message": "Erro interno ao processar a solicitação na API VulcanTech.",
                "details": None,
            },
        )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(industrial.router, prefix=prefix)
    app.include_router(oee.router, prefix=prefix)
    app.include_router(vision.router, prefix=prefix)
    app.include_router(predictive_maintenance.router, prefix=prefix)
    app.include_router(sensors.router, prefix=prefix)
    app.include_router(simulation.router, prefix=prefix)

    @app.get("/health", tags=["Saúde e Diagnóstico"])
    def root_health():
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        }

    return app


app = create_app()
