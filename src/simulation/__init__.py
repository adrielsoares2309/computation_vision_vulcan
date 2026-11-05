"""Simulador industrial VulcanTech para testes integrados de telemetria, ML, OEE e CLP."""

from .event_generator import DOWNTIME_REASONS, generate_simulated_production_event, infer_shift
from .plc_controller import avaliar_acao_clp, limpar_historico_clp, obter_historico_acoes_clp
from .sensor_simulator import SIMULATION_MODES, generate_simulated_sensor_reading

__all__ = [
    "SIMULATION_MODES",
    "DOWNTIME_REASONS",
    "generate_simulated_sensor_reading",
    "generate_simulated_production_event",
    "infer_shift",
    "avaliar_acao_clp",
    "obter_historico_acoes_clp",
    "limpar_historico_clp",
]
