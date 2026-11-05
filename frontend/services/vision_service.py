"""Serviço do frontend para Visão Computacional consumindo a API FastAPI."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from frontend.services.api_client import get_api_client

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
RAW_IMAGES_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "imagens"


def get_vision_metadata() -> dict[str, Any]:
    """Consulta os metadados reais e disponibilidade dos modelos de visão na API."""
    return get_api_client().get("/vision/metadata")


def list_sample_images() -> list[Path]:
    """Lista as imagens de amostra reais disponíveis em data/raw/imagens/."""
    if not RAW_IMAGES_DIR.is_dir():
        return []
    return sorted(p for p in RAW_IMAGES_DIR.iterdir() if p.suffix.lower() in ALLOWED_SUFFIXES)


def load_sample_preview(sample_path: Path) -> tuple[Image.Image, str]:
    """Carrega pré-visualização e dimensões de uma imagem de amostra local."""
    with Image.open(sample_path) as image:
        preview = image.convert("RGB").copy()
        dimensions = f"{image.width} × {image.height} px"
    return preview, dimensions


def validate_image(uploaded_file: Any) -> tuple[Image.Image, str]:
    """Valida extensão e decodificação da imagem para pré-visualização no navegador."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Formato não suportado. Use PNG, JPEG, TIFF ou BMP.")
    data = uploaded_file.getvalue()
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            preview = image.convert("RGB").copy()
            dimensions = f"{image.width} × {image.height} px"
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("O arquivo enviado não pôde ser decodificado como imagem válida.") from error
    return preview, dimensions


def inspect_uploaded_image(uploaded_file: Any, modality: str, piece_id: str | None = None) -> dict[str, Any]:
    """Envia a imagem via multipart/form-data para POST /api/v1/vision/predict."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Formato não suportado.")
    file_bytes = uploaded_file.getvalue()
    mime_type = getattr(uploaded_file, "type", None) or "image/png"
    client = get_api_client()
    return client.post(
        "/vision/predict",
        data={
            "modality": modality,
            "piece_id": (piece_id or "").strip() or "Sem identificação",
            "persist": "true",
        },
        files={"file": (uploaded_file.name, file_bytes, mime_type)},
        timeout=20.0,
    )


def inspect_sample_image(sample_path: Path, modality: str, piece_id: str | None = None) -> dict[str, Any]:
    """Envia uma imagem de amostra real do repositório para POST /api/v1/vision/predict."""
    file_bytes = sample_path.read_bytes()
    client = get_api_client()
    return client.post(
        "/vision/predict",
        data={
            "modality": modality,
            "piece_id": (piece_id or "").strip() or f"AMOSTRA-{sample_path.stem.upper()}",
            "persist": "true",
        },
        files={"file": (sample_path.name, file_bytes, "image/png")},
        timeout=20.0,
    )


def get_vision_history(modality: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Consulta o histórico real de inspeções persistidas no banco SQLite."""
    return get_api_client().get("/vision/history", params={"modality": modality, "limit": limit})


def get_vision_summary() -> dict[str, Any]:
    """Consulta o resumo estatístico das inspeções visuais na API."""
    return get_api_client().get("/vision/summary")
