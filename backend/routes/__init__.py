"""Agrupamento das rotas HTTP da API VulcanTech."""

from . import health, oee, predictive_maintenance, sensors, simulation, vision

__all__ = [
    "health",
    "oee",
    "vision",
    "predictive_maintenance",
    "sensors",
    "simulation",
]

