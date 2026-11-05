"""Pacote de Visão Computacional Industrial da VulcanTech Smart Metals S.A."""
from __future__ import annotations

from .geometry import (
    GeometryConfig,
    analyze_geometry,
    classify_geometry_against_references,
    contour_features,
    load_image,
)
from .pipeline import (
    diagnose_image_dataset,
    discover_images,
    predict_image,
    process_batch,
    process_image,
)
from .thermal import (
    ThermalConfig,
    analyze_thermal,
    classify_thermal_against_references,
)

__all__ = [
    "GeometryConfig",
    "ThermalConfig",
    "load_image",
    "contour_features",
    "analyze_geometry",
    "analyze_thermal",
    "classify_geometry_against_references",
    "classify_thermal_against_references",
    "discover_images",
    "process_image",
    "process_batch",
    "diagnose_image_dataset",
    "predict_image",
]

