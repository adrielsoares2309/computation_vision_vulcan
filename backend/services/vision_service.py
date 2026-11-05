"""Serviço de Visão Computacional para inspeção visual e termográfica de soldas."""

from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import threading
from typing import Any
import uuid

import joblib
from PIL import Image, UnidentifiedImageError

from backend.config import Settings, get_settings
from database.repositories import VisionRepository
from src.vision.predict import predict_image

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/x-tiff",
    "image/bmp",
    "image/x-bmp",
    "application/octet-stream",
}


class VisionService:
    """Gerencia o carregamento controlado dos modelos de visão, validação de upload e persistência."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._lock = threading.Lock()
        self._models_cache: dict[str, tuple[int, dict[str, Any]]] = {}
        self._metadata_cache: tuple[int, dict[str, Any]] | None = None
        self.repo = VisionRepository(self.settings.database_url)

    @property
    def vision_dir(self) -> Path:
        return self.settings.model_dir / "vision"

    @property
    def metadata_path(self) -> Path:
        return self.vision_dir / "model_metadata.json"

    @property
    def inference_temp_dir(self) -> Path:
        path = self.settings.data_dir / "raw" / "inference"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def check_availability(self) -> dict[str, Any]:
        """Verifica se os artefatos visual e térmico e os metadados estão disponíveis."""
        visual_ok = (self.vision_dir / "visual_model.joblib").is_file()
        termica_ok = (self.vision_dir / "termica_model.joblib").is_file()
        meta_ok = self.metadata_path.is_file()
        meta = {}
        error = None
        if meta_ok:
            try:
                meta = self.get_metadata()
            except Exception as exc:
                error = str(exc)
        else:
            error = "Metadados de visão ausentes em models/vision/model_metadata.json."
        return {
            "available": bool(visual_ok and termica_ok and meta_ok and error is None),
            "visual_model_available": visual_ok,
            "termica_model_available": termica_ok,
            "metadata_available": meta_ok,
            "experimental": bool(meta.get("experimental", True)),
            "validated_for_industrial_use": bool(meta.get("validated_for_industrial_use", False)),
            "status": meta.get("status", "unavailable"),
            "error": error,
        }

    def get_metadata(self) -> dict[str, Any]:
        """Lê os metadados reais dos modelos de visão computacional."""
        if not self.metadata_path.is_file():
            raise FileNotFoundError("Metadados de visão não encontrados em models/vision/model_metadata.json.")
        mtime = self.metadata_path.stat().st_mtime_ns
        with self._lock:
            if self._metadata_cache is None or self._metadata_cache[0] != mtime:
                data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                self._metadata_cache = (mtime, data)
            return dict(self._metadata_cache[1])

    def get_model_artifact(self, modality: str) -> dict[str, Any]:
        """Carrega e mantém em cache o artefato do modelo por modalidade."""
        mod = modality.strip().lower()
        if mod not in {"visual", "termica"}:
            raise ValueError("Modalidade inválida. Use 'visual' ou 'termica'.")
        model_path = self.vision_dir / f"{mod}_model.joblib"
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Modelo para modalidade '{mod}' não encontrado em models/vision/{mod}_model.joblib."
            )
        mtime = model_path.stat().st_mtime_ns
        with self._lock:
            cached = self._models_cache.get(mod)
            if cached is None or cached[0] != mtime:
                artifact = joblib.load(model_path)
                self._models_cache[mod] = (mtime, artifact)
            return self._models_cache[mod][1]

    def validate_and_inspect(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
        modality: str | None = None,
        piece_id: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Valida extensão, MIME, tamanho, decodificação e executa o pipeline real de visão."""
        if not filename:
            raise ValueError("Nome do arquivo não informado.")
        safe_name = Path(filename).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Extensão '{suffix}' não suportada. Formatos aceitos: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )
        if content_type and content_type.lower() not in ALLOWED_MIME_TYPES and not content_type.lower().startswith("image/"):
            raise ValueError(f"Tipo MIME não suportado para inspeção visual: {content_type}.")
        if not file_bytes:
            raise ValueError("O arquivo enviado está vazio.")
        if len(file_bytes) > self.settings.max_upload_size_bytes:
            raise OverflowError(
                f"Arquivo excede o tamanho máximo permitido de {self.settings.max_upload_size_bytes // (1024 * 1024)} MB."
            )

        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                if width < 8 or height < 8:
                    raise ValueError("Dimensões da imagem inválidas ou insuficientes para inspeção.")
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("O arquivo enviado não pôde ser decodificado como uma imagem válida.") from exc

        effective_modality = modality.strip().lower() if modality else None
        if effective_modality and effective_modality not in {"visual", "termica"}:
            raise ValueError("Modalidade inválida; informe 'visual' ou 'termica'.")

        resolved_modality = effective_modality
        if resolved_modality is None:
            stem_lower = Path(safe_name).stem.casefold()
            resolved_modality = "termica" if ("termica" in stem_lower or "thermal" in stem_lower) else "visual"

        artifact = self.get_model_artifact(resolved_modality)
        metadata = self.get_metadata()

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.inference_temp_dir,
                prefix="insp_",
                suffix=suffix,
                delete=False,
            ) as tmp:
                tmp.write(file_bytes)
                temp_path = Path(tmp.name)

            raw_result = predict_image(temp_path, modality=effective_modality, artifact=artifact)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

        inspection_id = f"INSP-{uuid.uuid4().hex[:10].upper()}"
        timestamp_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        clean_piece = (piece_id or "").strip() or "Sem identificação"

        response = {
            "inspection_id": inspection_id,
            "piece_id": clean_piece,
            "filename": safe_name,
            "modality": raw_result["modality"],
            "predicted_class": raw_result["predicted_class"],
            "class_scores": {k: round(float(v), 6) for k, v in raw_result["class_scores"].items()},
            "score_type": raw_result["score_type"],
            "timestamp": timestamp_iso,
            "inference_status": "completed",
            "model_version": str(metadata.get("preprocessing", {}).get("feature_version", "hog_rgb_hist_v1")),
            "model_status": raw_result["model_status"],
            "experimental": bool(metadata.get("experimental", True)),
            "validated_for_industrial_use": bool(raw_result.get("validated_for_industrial_use", False)),
            "data_source": "api",
            "warnings": list(raw_result.get("warnings", [])),
        }

        if persist:
            self.repo.insert_inspection(response)

        return response

    def get_history(self, modality: str | None = None, limit: int = 100) -> dict[str, Any]:
        """Retorna somente inspeções realmente persistidas no banco SQLite."""
        items = self.repo.list_inspections(modality=modality, limit=limit)
        return {
            "count": len(items),
            "items": items,
        }

    def get_summary(self) -> dict[str, Any]:
        """Calcula estatísticas sobre as inspeções reais registradas."""
        items = self.repo.list_inspections(limit=1000)
        by_class = {"APROVADA": 0, "REPROVADA": 0}
        by_modality = {"visual": 0, "termica": 0}
        for row in items:
            cls = row.get("predicted_class")
            mod = row.get("modality")
            if cls in by_class:
                by_class[cls] += 1
            if mod in by_modality:
                by_modality[mod] += 1

        meta = {}
        try:
            meta = self.get_metadata()
        except Exception:
            pass

        return {
            "total_inspections": len(items),
            "by_class": by_class,
            "by_modality": by_modality,
            "experimental_model": bool(meta.get("experimental", True)),
            "validated_for_industrial_use": bool(meta.get("validated_for_industrial_use", False)),
            "latest_inspection": items[0] if items else None,
        }

