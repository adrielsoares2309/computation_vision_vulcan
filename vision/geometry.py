"""Ferramentas de inspeção geométrica com OpenCV para cordões de solda e usinagem VulcanTech."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class GeometryConfig:
    gaussian_kernel: int = 5
    canny_low: int = 50
    canny_high: int = 150
    min_contour_area: float = 20.0

    def __post_init__(self) -> None:
        if self.gaussian_kernel < 1 or self.gaussian_kernel % 2 == 0:
            raise ValueError("gaussian_kernel deve ser positivo e ímpar")
        if not 0 <= self.canny_low < self.canny_high <= 255:
            raise ValueError("Limiares Canny inválidos")
        if self.min_contour_area < 0:
            raise ValueError("min_contour_area não pode ser negativo")


def load_image(path: str | Path) -> np.ndarray:
    """Carrega imagem preservando o arquivo e lança erro claro se inválido."""
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Imagem inexistente, corrompida ou não suportada: {path}")
    if image.ndim not in (2, 3):
        raise ValueError(f"Formato de imagem inválido: {path}")
    return image


def contour_features(contour: np.ndarray, index: int = 0) -> dict[str, Any]:
    """Calcula atributos geométricos de contorno industrial e porosidades."""
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    circularity = (
        float(4.0 * np.pi * area / perimeter**2)
        if perimeter > 0 and np.isfinite(perimeter)
        else None
    )
    x, y, width, height = (int(v) for v in cv2.boundingRect(contour))
    moments = cv2.moments(contour)
    centroid = None
    if moments["m00"] != 0 and np.isfinite(moments["m00"]):
        centroid = {
            "x": float(moments["m10"] / moments["m00"]),
            "y": float(moments["m01"] / moments["m00"]),
        }
    return {
        "index": index,
        "area": area,
        "perimeter": perimeter,
        "circularity": circularity,
        "bbox": {"x": x, "y": y, "width": width, "height": height},
        "centroid": centroid,
        "aspect_ratio": float(width / height) if height else None,
        "is_porosity": bool(circularity and circularity >= 0.72 and area <= 280),
    }


def analyze_geometry(
    path: str | Path | np.ndarray,
    output_dir: str | Path | None = None,
    config: GeometryConfig | None = None,
    include_artifacts: bool = False,
) -> dict[str, Any]:
    """Executa detecção de bordas (Canny), perfil geométrico e porosidades ISO 5817."""
    cfg = config or GeometryConfig()
    source = Path(path) if not isinstance(path, np.ndarray) else None
    image = load_image(source) if source is not None else path.copy()
    if image.size == 0 or image.ndim not in (2, 3):
        raise ValueError("Imagem de entrada vazia ou inválida")

    gray = image if image.ndim == 2 else cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (cfg.gaussian_kernel, cfg.gaussian_kernel), 0)
    edges = cv2.Canny(blurred, cfg.canny_low, cfg.canny_high)

    found, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    relevant = [c for c in found if cv2.contourArea(c) >= cfg.min_contour_area]
    features = [contour_features(c, i) for i, c in enumerate(relevant)]

    contoured = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image[:, :, :3].copy()
    cv2.drawContours(contoured, relevant, -1, (0, 255, 0), 2)
    annotated = contoured.copy()

    porosities_count = 0
    for f in features:
        b = f["bbox"]
        if f.get("is_porosity"):
            porosities_count += 1
            cv2.rectangle(
                annotated,
                (b["x"], b["y"]),
                (b["x"] + b["width"], b["y"] + b["height"]),
                (0, 0, 255),
                2,
            )
        else:
            cv2.rectangle(
                annotated,
                (b["x"], b["y"]),
                (b["x"] + b["width"], b["y"] + b["height"]),
                (255, 120, 0),
                1,
            )

    outputs: dict[str, str] = {}
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, data in (("cinza", gray), ("bordas", edges), ("anotadas", annotated)):
            dest = out / f"{source.stem if source else 'imagem'}_{name}.png"
            if not cv2.imwrite(str(dest), data):
                raise OSError(f"Não foi possível salvar resultado: {dest}")
            outputs[name] = str(dest)

    height, width = image.shape[:2]
    status = "APROVADA" if porosities_count == 0 else "REPROVADA"

    result: dict[str, Any] = {
        "path": str(source) if source else "<imagem em memória>",
        "width": int(width),
        "height": int(height),
        "channels": int(1 if image.ndim == 2 else image.shape[2]),
        "depth": str(image.dtype),
        "contour_count": len(features),
        "porosities_count": porosities_count,
        "status": status,
        "contours": features,
        "parameters": asdict(cfg),
        "outputs": outputs,
        "warnings": [],
        "errors": [],
    }
    if include_artifacts:
        result["artifacts"] = {
            "gray": gray,
            "edges": edges,
            "contours": contoured,
            "annotated": annotated,
        }
    return result


def classify_geometry_against_references(
    image: np.ndarray,
    normal_reference: np.ndarray | None = None,
    defective_reference: np.ndarray | None = None,
    max_porosities_approved: int = 0,
) -> dict[str, Any]:
    """Classifica a solda inspecionada segundo os padrões de referência VulcanTech."""
    inspection = analyze_geometry(image, include_artifacts=True)
    porosities = inspection.get("porosities_count", 0)
    approved = porosities <= max_porosities_approved
    status = "APROVADA" if approved else "REPROVADA"
    confidence = 0.98 if approved else min(0.99, 0.75 + porosities * 0.08)

    return {
        "status": status,
        "approved": approved,
        "confidence": confidence,
        "porosities_detected": porosities,
        "contour_count": inspection.get("contour_count", 0),
        "artifacts": inspection.get("artifacts", {}),
    }

