"""Testes unitários e de consistência para o módulo de cálculo OEE."""

from __future__ import annotations

import pytest

from src.oee import (
    aggregate_oee_records,
    calculate_availability,
    calculate_oee_from_counts,
    calculate_performance,
    calculate_quality,
)


def test_oee_valid_calculation_matches_documented_formulas():
    # Planejado = 60 min, parada = 12 min -> Operação = 48 min -> Disponibilidade = 48/60 = 0.80 (80%)
    # Ciclo ideal = 0.25 min/peça, total = 160 peças -> (0.25 * 160) / 48 = 40 / 48 = 0.833333 (83.33%)
    # Boas = 152 de 160 -> Qualidade = 152 / 160 = 0.95 (95%)
    # OEE = 0.80 * (40/48) * 0.95 = 0.633333 (63.33%)
    res = calculate_oee_from_counts(
        planned_time_min=60.0,
        downtime_min=12.0,
        ideal_cycle_time_min=0.25,
        total_count=160,
        good_count=152,
    )
    assert res["available"] is True
    assert res["status"] == "ok"
    assert res["availability"] == 80.0
    assert res["performance"] == 83.33
    assert res["quality"] == 95.0
    assert res["oee"] == 63.33
    assert res["rejected_count"] == 8


def test_oee_absence_of_data_returns_explicit_unavailable_state():
    agg = aggregate_oee_records([])
    assert agg["available"] is False
    assert agg["status"] == "no_production_records"
    assert agg["oee"] is None
    assert agg["availability"] is None


def test_oee_invalid_intervals_and_counts_raise_value_error():
    with pytest.raises(ValueError, match="planejado"):
        calculate_availability(0.0, operating_time_min=10.0)
    with pytest.raises(ValueError, match="negativo"):
        calculate_availability(60.0, downtime_min=-5.0)
    with pytest.raises(ValueError, match="superior"):
        calculate_oee_from_counts(60.0, downtime_min=75.0, ideal_cycle_time_min=0.25, total_count=10, good_count=10)
    with pytest.raises(ValueError, match="exceder"):
        calculate_quality(good_count=120, total_count=100)
    with pytest.raises(ValueError, match="ciclo ideal"):
        calculate_performance(ideal_cycle_time_min=0.0, total_count=50, operating_time_min=20.0)


def test_oee_zero_denominator_is_handled_safely_without_crash():
    # Parada igual ao tempo planejado -> operating_time_min = 0
    res_zero_op = calculate_oee_from_counts(
        planned_time_min=30.0,
        downtime_min=30.0,
        ideal_cycle_time_min=0.25,
        total_count=0,
        good_count=0,
    )
    assert res_zero_op["available"] is False
    assert res_zero_op["status"] == "zero_denominator"
    assert res_zero_op["availability"] == 0.0
    assert res_zero_op["performance"] is None
    assert res_zero_op["quality"] is None
    assert res_zero_op["oee"] is None

    # Operação > 0 mas produção total = 0
    res_zero_prod = calculate_oee_from_counts(
        planned_time_min=30.0,
        downtime_min=5.0,
        ideal_cycle_time_min=0.25,
        total_count=0,
        good_count=0,
    )
    assert res_zero_prod["available"] is False
    assert res_zero_prod["status"] == "zero_denominator"
    assert res_zero_prod["oee"] is None


def test_oee_aggregation_uses_weighted_physical_sums_not_simple_average():
    records = [
        {
            "planned_time_min": 60.0,
            "downtime_min": 0.0,
            "ideal_cycle_time_min": 0.5,
            "total_count": 120,
            "good_count": 120,
        },
        {
            "planned_time_min": 20.0,
            "downtime_min": 10.0,
            "ideal_cycle_time_min": 0.5,
            "total_count": 10,
            "good_count": 5,
        },
    ]
    agg = aggregate_oee_records(records)
    assert agg["available"] is True
    assert agg["planned_time_min"] == 80.0
    assert agg["operating_time_min"] == 70.0
    assert agg["total_count"] == 130
    assert agg["good_count"] == 125
    # Disponibilidade real = 70 / 80 = 87.5% (média simples seria (100 + 50)/2 = 75%)
    assert agg["availability"] == 87.5

