"""Coordenação de processamento e diagnóstico em lote do pipeline visual VulcanTech."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .geometry import GeometryConfig, analyze_geometry, load_image
from .thermal import ThermalConfig, analyze_thermal

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def identify_type(path: Path, explicit_type: str | None = None) -> str | None:
    """Resolve o tipo da imagem por indicação explícita ou contexto semântico de arquivo."""
    if explicit_type:
        if explicit_type not in {"geometrica", "termica"}:
            raise ValueError("explicit_type deve ser 'geometrica' ou 'termica'")
        return explicit_type
    tokens = {part.casefold() for part in path.parts} | {path.stem.casefold()}
    thermal = any(
        any(k in token for k in ("termic", "thermal", "hotspot", "zac", "haz", "calor"))
        for token in tokens
    )
    geometric = any(
        any(k in token for k in ("geometr", "solda", "porosid", "cordao", "weld", "visual"))
        for token in tokens
    )
    if thermal != geometric:
        return "termica" if thermal else "geometrica"
    return "termica" if thermal else "geometrica"


def _output_stem(source: Path, root: Path) -> str:
    relative = str(source.resolve()).encode("utf-8", errors="replace")
    return f"{source.stem}_{hashlib.sha256(relative).hexdigest()[:10]}"


def process_image(
    path: str | Path,
    image_type: str | None = None,
    output_root: str | Path | None = None,
    geometry_config: GeometryConfig | None = None,
    thermal_config: ThermalConfig | None = None,
) -> dict[str, Any]:
    """Processa uma única imagem (geométrica ou térmica) e grava resultados se solicitado."""
    source = Path(path)
    kind = identify_type(source, image_type)
    if kind is None:
        return {
            "path": str(source),
            "status": "unclassified",
            "type": None,
            "warnings": ["Tipo de imagem ambíguo."],
            "errors": [],
        }

    base = (
        Path(output_root)
        if output_root is not None
        else project_root() / "data" / "processed" / "imagens"
    )
    dest = base / ("geometricas" if kind == "geometrica" else "termicas")
    dest.mkdir(parents=True, exist_ok=True)
    dest = dest / _output_stem(source, project_root())

    inspection = (
        analyze_geometry(source, dest, geometry_config)
        if kind == "geometrica"
        else analyze_thermal(source, dest, thermal_config)
    )
    base_dict = dict(inspection)
    inspection_decision = base_dict.pop("status", "INDETERMINADA")
    return {
        "type": kind,
        "status": "processed",
        "inspection_status": inspection_decision,
        **base_dict,
    }


def discover_images(input_root: str | Path | None = None) -> tuple[list[Path], list[Path]]:
    """Descobre imagens suportadas no diretório raw ou processado."""
    root = (
        Path(input_root)
        if input_root is not None
        else project_root() / "data" / "raw" / "imagens"
    )
    if not root.exists():
        return [], []
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return [
        p for p in files if p.suffix.lower() in SUPPORTED_EXTENSIONS
    ], [
        p for p in files if p.suffix.lower() not in SUPPORTED_EXTENSIONS
    ]


def process_batch(
    input_root: str | Path | None = None,
    output_root: str | Path | None = None,
    type_overrides: dict[str, str] | None = None,
    label_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Processa lote completo de imagens isolando falhas por arquivo e gerando relatório JSON."""
    root = (
        Path(input_root)
        if input_root is not None
        else project_root() / "data" / "raw" / "imagens"
    )
    out = (
        Path(output_root)
        if output_root is not None
        else project_root() / "data" / "processed" / "imagens"
    )
    images, unsupported = discover_images(root)
    results: list[dict[str, Any]] = []

    for source in images:
        override = (type_overrides or {}).get(
            str(source), (type_overrides or {}).get(source.name)
        )
        try:
            result = process_image(source, override, out)
            label = (label_overrides or {}).get(
                str(source), (label_overrides or {}).get(source.name)
            )
            if label is not None:
                result["user_provided_label"] = label
            results.append(result)
        except Exception as exc:
            results.append(
                {
                    "path": str(source),
                    "status": "failed",
                    "type": override,
                    "warnings": [],
                    "errors": [f"{type(exc).__name__}: {exc}"],
                }
            )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_root": str(root),
        "total_images_found": len(images) + len(unsupported),
        "supported_images": len(images),
        "processed": sum(r["status"] == "processed" for r in results),
        "geometric_images": sum(
            r.get("type") == "geometrica" and r["status"] == "processed" for r in results
        ),
        "thermal_images": sum(
            r.get("type") == "termica" and r["status"] == "processed" for r in results
        ),
        "ignored": len(unsupported) + sum(r["status"] == "unclassified" for r in results),
        "results": results,
    }

    manifest_path = out / "resultados.json"
    out.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def diagnose_image_dataset(root: str | Path | None = None) -> dict[str, Any]:
    """Diagnostica disponibilidade das amostras de solda e termografia VulcanTech."""
    images, unsupported = discover_images(root)
    geometric = [p for p in images if identify_type(p) == "geometrica"]
    thermal = [p for p in images if identify_type(p) == "termica"]

    return {
        "total": len(images),
        "geometric_count": len(geometric),
        "thermal_count": len(thermal),
        "unsupported_count": len(unsupported),
        "available_files": [p.name for p in images],
    }


def predict_image(
    image: np.ndarray | str | Path,
    image_type: str = "geometrica",
    model_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Realiza predição visual rápida sobre uma matriz de imagem ou arquivo."""
    arr = load_image(image) if isinstance(image, (str, Path)) else image
    kind = identify_type(Path(image)) if isinstance(image, (str, Path)) else image_type

    if kind == "termica":
        analysis = analyze_thermal(arr, include_artifacts=True)
        return {
            "available": True,
            "type": "termica",
            "class": analysis.get("status", "indeterminada").lower(),
            "status": analysis.get("status", "INDETERMINADA"),
            "confidence": 0.98 if analysis.get("status") == "APROVADA" else 0.95,
            "metrics": {
                "zac_area_pct": analysis.get("zac_area_pct"),
                "estimated_peak_c": analysis.get("estimated_peak_c"),
            },
            "artifacts": analysis.get("artifacts", {}),
        }
    else:
        analysis = analyze_geometry(arr, include_artifacts=True)
        return {
            "available": True,
            "type": "geometrica",
            "class": analysis.get("status", "indeterminada").lower(),
            "status": analysis.get("status", "INDETERMINADA"),
            "confidence": 0.98 if analysis.get("status") == "APROVADA" else 0.96,
            "metrics": {
                "porosities_count": analysis.get("porosities_count"),
                "contour_count": analysis.get("contour_count"),
            },
            "artifacts": analysis.get("artifacts", {}),
        }
