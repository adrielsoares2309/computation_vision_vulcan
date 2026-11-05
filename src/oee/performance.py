"""Cálculo de Performance operacional."""

from __future__ import annotations


def calculate_performance(ideal_cycle_time_min: float, total_count: int, operating_time_min: float) -> float:
    """Calcula Performance = (Tempo de ciclo ideal × Quantidade total produzida) / Tempo de operação."""
    if operating_time_min is None or operating_time_min <= 0:
        raise ValueError("O tempo de operação deve ser maior que zero para calcular a performance.")
    if ideal_cycle_time_min is None or ideal_cycle_time_min <= 0:
        raise ValueError("O tempo de ciclo ideal deve ser maior que zero.")
    if total_count is None or total_count < 0:
        raise ValueError("A quantidade total produzida não pode ser negativa.")
    return (float(ideal_cycle_time_min) * float(total_count)) / float(operating_time_min)

