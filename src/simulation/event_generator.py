"""Gerador de eventos operacionais e lotes de produção simulados para cálculo de OEE."""

from __future__ import annotations

from datetime import datetime, timezone
import random
from typing import Any


DOWNTIME_REASONS = {
    0: "Sem parada relevante (ajuste de lote)",
    1: "Troca preventiva/corretiva de ferramenta",
    2: "Inspeção e desobstrução do circuito de refrigeração",
    3: "Alinhamento mecânico de matriz e inspeção de trinca",
}


def infer_shift(dt: datetime) -> str:
    """Determina o turno industrial a partir do horário (MANHA 06-14, TARDE 14-22, NOITE 22-06)."""
    hour = dt.hour
    if 6 <= hour < 14:
        return "MANHA"
    if 14 <= hour < 22:
        return "TARDE"
    return "NOITE"


def generate_simulated_production_event(
    equipment_id: str,
    alloy: str,
    fault_class: int = 0,
    planned_time_min: float = 15.0,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Gera um registro de produção/parada explicitamente identificado como simulado."""
    gen = rng or random
    now = datetime.now(timezone.utc).replace(microsecond=0)
    shift = infer_shift(now)

    ideal_cycle_time_min = 0.25  # 15 segundos por peça (4 peças/min ideal)
    if fault_class == 0:
        downtime_min = round(gen.uniform(0.0, 1.2), 2)
        efficiency_factor = gen.uniform(0.88, 0.98)
        scrap_rate = gen.uniform(0.005, 0.025)
    elif fault_class == 1:
        downtime_min = round(gen.uniform(2.5, 5.5), 2)
        efficiency_factor = gen.uniform(0.72, 0.85)
        scrap_rate = gen.uniform(0.06, 0.14)
    elif fault_class == 2:
        downtime_min = round(gen.uniform(4.0, 8.0), 2)
        efficiency_factor = gen.uniform(0.65, 0.80)
        scrap_rate = gen.uniform(0.08, 0.18)
    else:
        downtime_min = round(gen.uniform(6.0, 11.0), 2)
        efficiency_factor = gen.uniform(0.55, 0.72)
        scrap_rate = gen.uniform(0.12, 0.25)

    operating_time_min = max(0.0, planned_time_min - downtime_min)
    max_possible_units = operating_time_min / ideal_cycle_time_min
    total_count = max(1, int(round(max_possible_units * efficiency_factor))) if operating_time_min > 0 else 0
    rejected_count = int(round(total_count * scrap_rate))
    good_count = max(0, total_count - rejected_count)

    return {
        "timestamp": now.isoformat(),
        "id_celula": equipment_id,
        "liga_metalica": alloy,
        "shift": shift,
        "planned_time_min": round(planned_time_min, 2),
        "downtime_min": round(downtime_min, 2),
        "ideal_cycle_time_min": ideal_cycle_time_min,
        "total_count": total_count,
        "good_count": good_count,
        "rejected_count": rejected_count,
        "downtime_reason": DOWNTIME_REASONS.get(fault_class, "Parada operacional simulada") if downtime_min > 0.5 else None,
        "associated_fault_class": fault_class,
        "data_source": "simulated",
    }

