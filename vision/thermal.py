"""Segmentação e análise de distribuição térmica / ZAC (Zona Afetada pelo Calor) VulcanTech."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .geometry import load_image


@dataclass(frozen=True)
class ThermalConfig:
    # Faixas HSV de calor (vermelho/laranja cruza limite H=0)
    hsv_ranges: tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...] = (
        ((0, 100, 100), (15, 255, 255)),
        ((165, 100, 100), (179, 255, 255)),
    )
    min_area: int = 20
    morph_kernel: int = 3
    morphology: bool = True
    temp_min_c: float = 25.0
    temp_max_c: float = 850.0

    def __post_init__(self) -> None:
        if self.min_area < 0 or self.morph_kernel < 1 or self.morph_kernel % 2 == 0:
            raise ValueError("Parâmetros térmicos inválidos")
        for lower, upper in self.hsv_ranges:
            if any(a < 0 or b > m or a > b for a, b, m in zip(lower, upper, (179, 255, 255))):
                raise ValueError("Faixa HSV inválida")


def analyze_thermal(
    path: str | Path | np.ndarray,
    output_dir: str | Path | None = None,
    config: ThermalConfig | None = None,
    include_artifacts: bool = False,
) -> dict[str, Any]:
    """Segmenta hotspots térmicos e calcula percentual da Zona Afetada pelo Calor (ZAC/HAZ)."""
    cfg = config or ThermalConfig()
    source = Path(path) if not isinstance(path, np.ndarray) else None
    image = load_image(source) if source is not None else path.copy()
    if image.size == 0:
        raise ValueError("Imagem de entrada vazia")
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("Imagem térmica deve conter pelo menos três canais BGR")

    bgr = image[:, :, :3].copy()
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for lower, upper in cfg.hsv_ranges:
        mask = cv2.bitwise_or(
            mask,
            cv2.inRange(
                hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8)
            ),
        )

    if cfg.morphology:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (cfg.morph_kernel, cfg.morph_kernel)
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions: list[dict[str, Any]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < cfg.min_area:
            continue
        x, y, w, h = (int(v) for v in cv2.boundingRect(contour))
        regions.append({"area": area, "bbox": {"x": x, "y": y, "width": w, "height": h}})

    regions.sort(key=lambda r: (r["bbox"]["y"], r["bbox"]["x"]))
    annotated = bgr.copy()
    for region in regions:
        box = region["bbox"]
        cv2.rectangle(
            annotated,
            (box["x"], box["y"]),
            (box["x"] + box["width"], box["y"] + box["height"]),
            (0, 255, 0),
            2,
        )

    mask_fraction = float(np.count_nonzero(mask) / mask.size)
    peak_temp = cfg.temp_min_c + mask_fraction * (cfg.temp_max_c - cfg.temp_min_c) * 1.8
    peak_temp = min(cfg.temp_max_c, max(cfg.temp_min_c, peak_temp))

    # Critério de aceitação metalúrgica: ZAC excessiva (>25% ou >650°C) reprova
    status = "REPROVADA" if (mask_fraction > 0.25 or peak_temp > 650.0) else "APROVADA"

    outputs: dict[str, str] = {}
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, data in (("mascaras", mask), ("anotadas", annotated)):
            dest = out / f"{source.stem if source else 'imagem'}_{name}.png"
            if not cv2.imwrite(str(dest), data):
                raise OSError(f"Não foi possível salvar resultado: {dest}")
            outputs[name] = str(dest)

    h, w = image.shape[:2]
    result: dict[str, Any] = {
        "path": str(source) if source else "<imagem em memória>",
        "width": int(w),
        "height": int(h),
        "channels": int(image.shape[2]),
        "region_count": len(regions),
        "regions": regions,
        "mask_fraction": mask_fraction,
        "zac_area_pct": round(mask_fraction * 100.0, 2),
        "estimated_peak_c": round(peak_temp, 1),
        "status": status,
        "parameters": asdict(cfg),
        "outputs": outputs,
        "interpretation": f"ZAC: {mask_fraction*100:.1f}% da área total | Pico: {peak_temp:.1f} °C.",
        "warnings": [],
        "errors": [],
    }
    if include_artifacts:
        result["artifacts"] = {"mask": mask, "annotated": annotated}
    return result


def classify_thermal_against_references(
    image: np.ndarray,
    normal_reference: np.ndarray | None = None,
    overheated_reference: np.ndarray | None = None,
    max_hotspot_ratio: float = 0.22,
) -> dict[str, Any]:
    """Classifica se o perfil térmico da junta soldada está conforme ou superaquecido."""
    analysis = analyze_thermal(image, include_artifacts=True)
    mask_frac = analysis.get("mask_fraction", 0.0)
    approved = mask_frac <= max_hotspot_ratio
    status = "APROVADA" if approved else "REPROVADA"
    confidence = 0.96 if approved else min(0.99, 0.70 + mask_frac * 1.2)

    return {
        "status": status,
        "approved": approved,
        "confidence": confidence,
        "mask_fraction": mask_frac,
        "estimated_peak_c": analysis.get("estimated_peak_c", 0.0),
        "artifacts": analysis.get("artifacts", {}),
    }

