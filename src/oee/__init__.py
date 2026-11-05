"""Módulo de cálculo de indicadores de Eficiência Global do Equipamento (OEE)."""

from .availability import calculate_availability
from .calculator import aggregate_oee_records, calculate_oee_from_counts
from .performance import calculate_performance
from .predictive_impact import calcular_impacto_preditivo_oee
from .quality import calculate_quality

__all__ = [
    "calculate_availability",
    "calculate_performance",
    "calculate_quality",
    "calculate_oee_from_counts",
    "aggregate_oee_records",
    "calcular_impacto_preditivo_oee",
]
