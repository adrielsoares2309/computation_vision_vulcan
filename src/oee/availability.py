"""Cálculo de Disponibilidade operacional (Availability)."""

from __future__ import annotations


def calculate_availability(planned_production_time_min: float, operating_time_min: float | None = None,
                           downtime_min: float | None = None) -> float:
    """Calcula Disponibilidade = Tempo de operação / Tempo de produção planejado (como proporção)."""
    if planned_production_time_min is None or planned_production_time_min <= 0:
        raise ValueError("O tempo de produção planejado deve ser maior que zero para calcular a disponibilidade.")
    if operating_time_min is None:
        if downtime_min is None:
            raise ValueError("Informe o tempo de operação ou o tempo de parada.")
        if downtime_min < 0:
            raise ValueError("O tempo de parada não pode ser negativo.")
        operating_time_min = planned_production_time_min - downtime_min
    if operating_time_min < 0:
        raise ValueError("O tempo de operação não pode ser negativo.")
    if operating_time_min > planned_production_time_min + 1e-6:
        raise ValueError("O tempo de operação não pode exceder o tempo de produção planejado.")
    return float(operating_time_min) / float(planned_production_time_min)

