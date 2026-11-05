"""Integração dos fatores de Disponibilidade, Performance e Qualidade para cálculo do OEE."""

from __future__ import annotations

from typing import Any

from .availability import calculate_availability
from .performance import calculate_performance
from .quality import calculate_quality


def calculate_oee_from_counts(
    planned_time_min: float,
    downtime_min: float,
    ideal_cycle_time_min: float,
    total_count: int,
    good_count: int | None = None,
    rejected_count: int | None = None,
) -> dict[str, Any]:
    """Calcula os componentes e o OEE final validando denominadores e consistência física."""
    if planned_time_min is None or planned_time_min <= 0:
        return {
            "available": False,
            "status": "insufficient_data",
            "reason": "Tempo planejado inválido ou igual a zero.",
            "availability": None,
            "performance": None,
            "quality": None,
            "oee": None,
        }
    if downtime_min is None or downtime_min < 0:
        raise ValueError("O tempo de parada deve ser maior ou igual a zero.")
    if downtime_min > planned_time_min:
        raise ValueError("O tempo de parada não pode ser superior ao tempo planejado.")

    operating_time_min = float(planned_time_min) - float(downtime_min)
    if total_count is None or total_count < 0:
        raise ValueError("A produção total não pode ser negativa.")

    if good_count is None:
        if rejected_count is None:
            raise ValueError("Informe a quantidade de unidades boas ou a quantidade rejeitada.")
        if rejected_count < 0 or rejected_count > total_count:
            raise ValueError("A quantidade rejeitada deve estar entre 0 e a produção total.")
        good_count = int(total_count) - int(rejected_count)
    else:
        if good_count < 0 or good_count > total_count:
            raise ValueError("A quantidade de unidades boas deve estar entre 0 e a produção total.")
        rejected_count = int(total_count) - int(good_count)

    availability = calculate_availability(planned_time_min, operating_time_min=operating_time_min)

    if operating_time_min <= 0 or total_count <= 0:
        return {
            "available": False,
            "status": "zero_denominator",
            "reason": "Tempo de operação ou produção total igual a zero no período selecionado; não é possível calcular Performance, Qualidade e OEE completo.",
            "planned_time_min": round(float(planned_time_min), 2),
            "operating_time_min": round(float(operating_time_min), 2),
            "downtime_min": round(float(downtime_min), 2),
            "total_count": int(total_count),
            "good_count": int(good_count),
            "rejected_count": int(rejected_count),
            "availability": round(availability * 100.0, 2),
            "performance": None,
            "quality": None,
            "oee": None,
        }

    performance = calculate_performance(ideal_cycle_time_min, total_count, operating_time_min)
    quality = calculate_quality(good_count, total_count)
    oee = availability * performance * quality

    return {
        "available": True,
        "status": "ok",
        "reason": None,
        "planned_time_min": round(float(planned_time_min), 2),
        "operating_time_min": round(float(operating_time_min), 2),
        "downtime_min": round(float(downtime_min), 2),
        "total_count": int(total_count),
        "good_count": int(good_count),
        "rejected_count": int(rejected_count),
        "availability": round(availability * 100.0, 2),
        "performance": round(performance * 100.0, 2),
        "quality": round(quality * 100.0, 2),
        "oee": round(oee * 100.0, 2),
        "availability_ratio": round(availability, 6),
        "performance_ratio": round(performance, 6),
        "quality_ratio": round(quality, 6),
        "oee_ratio": round(oee, 6),
    }


def aggregate_oee_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Agrega múltiplos registros de produção somando tempos e quantidades (nunca média simples de percentuais)."""
    if not records:
        return {
            "available": False,
            "status": "no_production_records",
            "reason": "Não há registros de produção e paradas para os filtros e fonte selecionados.",
            "planned_time_min": None,
            "operating_time_min": None,
            "downtime_min": None,
            "total_count": None,
            "good_count": None,
            "rejected_count": None,
            "availability": None,
            "performance": None,
            "quality": None,
            "oee": None,
        }

    planned_total = 0.0
    downtime_total = 0.0
    ideal_run_time_total = 0.0
    total_units = 0
    good_units = 0

    for row in records:
        planned = float(row["planned_time_min"])
        downtime = float(row["downtime_min"])
        ideal_cycle = float(row["ideal_cycle_time_min"])
        count = int(row["total_count"])
        good = int(row["good_count"])
        if planned <= 0 or downtime < 0 or downtime > planned or ideal_cycle <= 0 or count < 0 or good < 0 or good > count:
            raise ValueError(f"Registro de produção inválido encontrado durante agregação: {row}")
        planned_total += planned
        downtime_total += downtime
        ideal_run_time_total += ideal_cycle * count
        total_units += count
        good_units += good

    operating_total = planned_total - downtime_total
    rejected_units = total_units - good_units

    if planned_total <= 0:
        return {
            "available": False,
            "status": "zero_denominator",
            "reason": "Soma de tempo planejado igual a zero.",
            "planned_time_min": 0.0,
            "operating_time_min": 0.0,
            "downtime_min": 0.0,
            "total_count": total_units,
            "good_count": good_units,
            "rejected_count": rejected_units,
            "availability": None,
            "performance": None,
            "quality": None,
            "oee": None,
        }

    availability = operating_total / planned_total
    if operating_total <= 0 or total_units <= 0:
        return {
            "available": False,
            "status": "zero_denominator",
            "reason": "Tempo de operação agregado ou produção total agregada igual a zero.",
            "planned_time_min": round(planned_total, 2),
            "operating_time_min": round(operating_total, 2),
            "downtime_min": round(downtime_total, 2),
            "total_count": total_units,
            "good_count": good_units,
            "rejected_count": rejected_units,
            "availability": round(availability * 100.0, 2),
            "performance": None,
            "quality": None,
            "oee": None,
        }

    performance = ideal_run_time_total / operating_total
    quality = good_units / total_units
    oee = availability * performance * quality

    return {
        "available": True,
        "status": "ok",
        "reason": None,
        "planned_time_min": round(planned_total, 2),
        "operating_time_min": round(operating_total, 2),
        "downtime_min": round(downtime_total, 2),
        "total_count": total_units,
        "good_count": good_units,
        "rejected_count": rejected_units,
        "availability": round(availability * 100.0, 2),
        "performance": round(performance * 100.0, 2),
        "quality": round(quality * 100.0, 2),
        "oee": round(oee * 100.0, 2),
        "availability_ratio": round(availability, 6),
        "performance_ratio": round(performance, 6),
        "quality_ratio": round(quality, 6),
        "oee_ratio": round(oee, 6),
    }

