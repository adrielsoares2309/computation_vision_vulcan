"""Gerador de leituras simuladas de sensores industriais com modos operacionais."""

from __future__ import annotations

from datetime import datetime, timezone
import random
from typing import Any

from src.data.validator import VALID_ALLOYS, VALID_CELLS

SIMULATION_MODES = {
    "NORMAL",
    "DESGASTE_FERRAMENTA",
    "FALHA_REFRIGERACAO",
    "DESALINHAMENTO_TRINCA",
    "MISTO",
}

ALLOY_BASELINES = {
    "Aco_Carbono_316L": {"torque": 110.0, "corrente": 28.5, "ruido": 54.0, "temp": 52.0},
    "Aluminio_7075": {"torque": 85.0, "corrente": 22.0, "ruido": 48.5, "temp": 45.0},
    "Liga_Titanio_Ti6Al4V": {"torque": 145.0, "corrente": 37.5, "ruido": 71.0, "temp": 63.0},
}


def generate_simulated_sensor_reading(
    mode: str = "MISTO",
    equipment_id: str | None = None,
    alloy: str | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Gera uma leitura sintética coerente com a liga metálica e o cenário operacional."""
    gen = rng or random
    mode = mode.upper().strip()
    if mode not in SIMULATION_MODES:
        raise ValueError(f"Modo de simulação inválido: {mode}. Use um de {sorted(SIMULATION_MODES)}.")

    cell = equipment_id if equipment_id in VALID_CELLS else gen.choice(sorted(VALID_CELLS))
    chosen_alloy = alloy if alloy in VALID_ALLOYS else gen.choice(sorted(VALID_ALLOYS))
    base = ALLOY_BASELINES[chosen_alloy]

    effective_mode = mode
    if mode == "MISTO":
        roll = gen.random()
        if roll < 0.78:
            effective_mode = "NORMAL"
        elif roll < 0.86:
            effective_mode = "DESGASTE_FERRAMENTA"
        elif roll < 0.94:
            effective_mode = "FALHA_REFRIGERACAO"
        else:
            effective_mode = "DESALINHAMENTO_TRINCA"

    temperatura = gen.gauss(base["temp"], 3.0)
    vibracao = gen.gauss(1.85, 0.25)
    torque = gen.gauss(base["torque"], 8.0)
    vazao = gen.gauss(28.0, 1.8)
    corrente = gen.gauss(base["corrente"], 2.2)
    pressao = gen.gauss(160.0, 6.0)
    ruido = gen.gauss(base["ruido"], 2.5)
    expected_fault = 0

    if effective_mode == "DESGASTE_FERRAMENTA":
        vibracao = gen.uniform(4.2, 6.8)
        torque = base["torque"] + gen.uniform(45.0, 80.0)
        corrente = base["corrente"] + gen.uniform(10.0, 18.0)
        ruido = base["ruido"] + gen.uniform(16.0, 26.0)
        temperatura = base["temp"] + gen.uniform(8.0, 16.0)
        expected_fault = 1
    elif effective_mode == "FALHA_REFRIGERACAO":
        vazao = gen.uniform(4.0, 11.5)
        temperatura = gen.uniform(84.0, 108.0)
        pressao = gen.uniform(135.0, 155.0)
        expected_fault = 2
    elif effective_mode == "DESALINHAMENTO_TRINCA":
        vibracao = gen.uniform(6.5, 10.2)
        torque = base["torque"] + gen.uniform(65.0, 115.0)
        corrente = base["corrente"] + gen.uniform(16.0, 26.0)
        pressao = gen.uniform(95.0, 118.0)
        ruido = gen.uniform(88.0, 108.0)
        expected_fault = 3

    return {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "id_celula": cell,
        "liga_metalica": chosen_alloy,
        "temperatura_fuso_c": round(max(20.0, temperatura), 3),
        "vibracao_triaxial_rms_mms": round(max(0.2, vibracao), 3),
        "torque_fuso_nm": round(max(20.0, torque), 3),
        "vazao_refrigerante_lmin": round(max(0.0, vazao), 3),
        "corrente_estator_amp": round(max(5.0, corrente), 3),
        "pressao_hidraulica_bar": round(max(30.0, pressao), 3),
        "nivel_ruido_db": round(max(30.0, ruido), 3),
        "scenario_mode": effective_mode,
        "expected_fault_code": expected_fault,
        "data_source": "simulated",
    }

