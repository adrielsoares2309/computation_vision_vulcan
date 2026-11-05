"""Rotas REST para Visão Computacional (inspeção visual e térmica de soldas)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from backend.dependencies import get_vision_service
from backend.schemas.vision import VisionHistoryResponse, VisionPredictionResponse, VisionSummaryResponse
from backend.services.vision_service import VisionService
from src.vision.thermal_analysis import analisar_termografia_solda
from src.vision.weld_inspection import inspecionar_solda

router = APIRouter(prefix="/vision", tags=["Visão Computacional — Inspeção de Soldas"])


@router.post(
    "/inspect",
    summary="Inspeção geométrica de solda via OpenCV (Canny, contornos, descontinuidades e porosidade)",
)
async def inspect_weld_geometric(
    file: UploadFile = File(..., description="Arquivo de imagem visual da junta soldada."),
    limiar_porosidade: float = Form(default=3.0, description="Limiar percentual de porosidade para reprovação."),
) -> dict[str, Any]:
    """Executa processamento completo de imagem: nitidez, Canny, contornos e porosidade."""
    try:
        content = await file.read()
        import cv2
        import numpy as np
        nparr = np.frombuffer(content, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Não foi possível decodificar o arquivo como imagem válida.")

        resultado = inspecionar_solda(
            img_bgr,
            limiar_porosidade_reprovacao=limiar_porosidade,
        )
        resultado["nome_arquivo"] = file.filename
        return resultado
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/thermal",
    summary="Análise termográfica de solda via OpenCV HSV (Hotspots, HAZ/ZAC e perfil térmico)",
)
async def inspect_weld_thermal(
    file: UploadFile = File(..., description="Arquivo de imagem termográfica (falsa cor)."),
) -> dict[str, Any]:
    """Converte para HSV, segmenta hotspots e calcula percentual da Zona Afetada pelo Calor."""
    try:
        content = await file.read()
        import cv2
        import numpy as np
        nparr = np.frombuffer(content, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Não foi possível decodificar o arquivo como imagem termográfica válida.")

        resultado = analisar_termografia_solda(img_bgr)
        resultado["nome_arquivo"] = file.filename
        return resultado
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/metadata", summary="Retorna metadados reais, status experimental e limitações dos modelos de visão")
def get_vision_metadata(service: VisionService = Depends(get_vision_service)) -> dict[str, Any]:
    try:
        meta = service.get_metadata()
        availability = service.check_availability()
        return {**meta, "availability": availability}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post(
    "/predict",
    response_model=VisionPredictionResponse,
    summary="Recebe imagem via multipart/form-data e executa o pipeline real de visão computacional",
)
async def predict_weld_image(
    file: UploadFile = File(..., description="Arquivo de imagem (PNG, JPG, JPEG, TIF, TIFF, BMP)."),
    modality: str | None = Form(default=None, description="Modalidade: 'visual' ou 'termica'."),
    piece_id: str | None = Form(default=None, description="Identificador opcional da peça."),
    persist: bool = Form(default=True, description="Indica se a inspeção deve ser salva no histórico SQLite."),
    service: VisionService = Depends(get_vision_service),
) -> VisionPredictionResponse:
    try:
        content = await file.read()
        result = service.validate_and_inspect(
            file_bytes=content,
            filename=file.filename or "upload.png",
            content_type=file.content_type,
            modality=modality,
            piece_id=piece_id,
            persist=persist,
        )
        return VisionPredictionResponse(**result)
    except OverflowError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/history", response_model=VisionHistoryResponse, summary="Consulta o histórico real de inspeções visuais")
def get_vision_history(
    modality: str | None = Query(default=None, description="Filtro opcional de modalidade ('visual' ou 'termica')."),
    limit: int = Query(default=100, ge=1, le=500),
    service: VisionService = Depends(get_vision_service),
) -> VisionHistoryResponse:
    result = service.get_history(modality=modality, limit=limit)
    return VisionHistoryResponse(**result)


@router.get("/summary", response_model=VisionSummaryResponse, summary="Resumo estatístico das inspeções realizadas")
def get_vision_summary(service: VisionService = Depends(get_vision_service)) -> VisionSummaryResponse:
    result = service.get_summary()
    return VisionSummaryResponse(**result)
