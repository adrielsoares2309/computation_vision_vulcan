"""Cálculo de Qualidade operacional."""

from __future__ import annotations


def calculate_quality(good_count: int, total_count: int) -> float:
    """Calcula Qualidade = Quantidade de unidades boas / Quantidade total produzida."""
    if total_count is None or total_count <= 0:
        raise ValueError("A quantidade total produzida deve ser maior que zero para calcular a qualidade.")
    if good_count is None or good_count < 0:
        raise ValueError("A quantidade de unidades boas não pode ser negativa.")
    if good_count > total_count:
        raise ValueError("A quantidade de unidades boas não pode exceder a quantidade total produzida.")
    return float(good_count) / float(total_count)

