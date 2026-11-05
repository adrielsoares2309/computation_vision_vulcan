"""Rotas REST para controle do Simulador Industrial."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_simulation_service
from backend.schemas.simulation import (
    SimulationModeRequest,
    SimulationStartRequest,
    SimulationStatusResponse,
    SimulationStepRequest,
)
from backend.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["Simulação Industrial"])


@router.get("/status", response_model=SimulationStatusResponse, summary="Consulta o estado atual do simulador industrial")
def get_simulation_status(service: SimulationService = Depends(get_simulation_service)) -> SimulationStatusResponse:
    return SimulationStatusResponse(**service.get_status())


@router.post("/start", response_model=SimulationStatusResponse, summary="Inicia o simulador em background de forma controlada")
def start_simulation(
    payload: SimulationStartRequest | None = None,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStatusResponse:
    req = payload or SimulationStartRequest()
    try:
        result = service.start(
            mode=req.mode,
            interval_seconds=req.interval_seconds,
            generate_initial_batch=req.generate_initial_batch,
        )
        return SimulationStatusResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/stop", response_model=SimulationStatusResponse, summary="Interrompe o simulador em background")
def stop_simulation(service: SimulationService = Depends(get_simulation_service)) -> SimulationStatusResponse:
    return SimulationStatusResponse(**service.stop())


@router.post("/mode", response_model=SimulationStatusResponse, summary="Altera o modo operacional do simulador")
def change_simulation_mode(
    payload: SimulationModeRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStatusResponse:
    try:
        return SimulationStatusResponse(**service.set_mode(payload.mode))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/step", summary="Executa imediatamente N ciclos simulados sob demanda")
def step_simulation(
    payload: SimulationStepRequest | None = None,
    service: SimulationService = Depends(get_simulation_service),
) -> dict[str, Any]:
    req = payload or SimulationStepRequest()
    try:
        generated = []
        for _ in range(req.count):
            generated.append(service.execute_cycle(mode=req.mode, equipment_id=req.equipment_id))
        return {
            "executed_cycles": len(generated),
            "events": generated,
            "status": service.get_status(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/plc/history", summary="Retorna histórico de comandos e intertravamentos do CLP simulado")
def get_plc_history(limit: int = 50) -> list[dict[str, Any]]:
    from src.simulation.plc_controller import obter_historico_acoes_clp
    return obter_historico_acoes_clp(limite=limit)


@router.post("/plc/evaluate", summary="Avalia uma condição operacional e retorna a ação determinística do CLP")
def evaluate_plc_action(payload: dict[str, Any]) -> dict[str, Any]:
    from src.simulation.plc_controller import avaliar_acao_clp
    try:
        leitura = payload.get("leitura", payload)
        tipo_falha = int(payload.get("tipo_falha_previsto", 0))
        probabilidade = float(payload.get("probabilidade_falha", 0.0))
        anomalia = float(payload.get("score_anomalia", 0.0))
        return avaliar_acao_clp(
            leitura,
            tipo_falha_previsto=tipo_falha,
            probabilidade_falha=probabilidade,
            score_anomalia=anomalia,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

