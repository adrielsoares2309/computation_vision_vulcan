"""Pipeline modular de inspeção visual e térmica de soldas."""

from .predict import predict_image
from .thermal_analysis import analisar_termografia_solda
from .weld_inspection import inspecionar_solda

__all__ = [
    "predict_image",
    "inspecionar_solda",
    "analisar_termografia_solda",
]
