"""Regras e faixas documentadas para validação de leituras de sensores VulcanTech."""

from __future__ import annotations

from typing import Any

VALID_CELLS = {"CEL-201", "CEL-202", "CEL-203", "CEL-204"}
VALID_ALLOYS = {"Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V"}

SENSOR_SPECS: dict[str, dict[str, Any]] = {
    "temperatura_fuso_c": {
        "label": "Temperatura do fuso",
        "unit": "°C",
        "normal_min": 30.0,
        "normal_max": 75.0,
        "physical_min": -20.0,
        "physical_max": 350.0,
        "sentinels": [999.9],
    },
    "vibracao_triaxial_rms_mms": {
        "label": "Vibração triaxial RMS",
        "unit": "mm/s RMS",
        "normal_min": 0.8,
        "normal_max": 3.8,
        "physical_min": 0.0,
        "physical_max": 50.0,
        "sentinels": [-99.0],
    },
    "torque_fuso_nm": {
        "label": "Torque do fuso",
        "unit": "Nm",
        "normal_min": 45.0,
        "normal_max": 210.0,
        "physical_min": 0.0,
        "physical_max": 600.0,
        "sentinels": [],
    },
    "vazao_refrigerante_lmin": {
        "label": "Vazão de refrigerante",
        "unit": "L/min",
        "normal_min": 15.0,
        "normal_max": 40.0,
        "physical_min": 0.0,
        "physical_max": 120.0,
        "sentinels": [],
    },
    "corrente_estator_amp": {
        "label": "Corrente do estator",
        "unit": "A",
        "normal_min": 12.0,
        "normal_max": 55.0,
        "physical_min": 0.0,
        "physical_max": 200.0,
        "sentinels": [],
    },
    "pressao_hidraulica_bar": {
        "label": "Pressão hidráulica",
        "unit": "bar",
        "normal_min": 110.0,
        "normal_max": 220.0,
        "physical_min": 0.0,
        "physical_max": 450.0,
        "sentinels": [-1.0],
    },
    "nivel_ruido_db": {
        "label": "Nível de ruído",
        "unit": "dB",
        "normal_min": 45.0,
        "normal_max": 85.0,
        "physical_min": 10.0,
        "physical_max": 160.0,
        "sentinels": [],
    },
}

FAULT_CLASSES: dict[int, str] = {
    0: "Normal",
    1: "Desgaste de ferramenta",
    2: "Falha de refrigeração",
    3: "Desalinhamento / trinca",
}

INDUSTRIAL_ACTIONS: dict[int, str] = {
    0: "MANTER_OPERACAO",
    1: "REDUZIR_VELOCIDADE_50%",
    2: "INTERROMPER_EMERGENCIA",
    3: "INTERROMPER_EMERGENCIA",
}

