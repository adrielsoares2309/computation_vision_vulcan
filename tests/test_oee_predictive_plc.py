"""Testes para o cálculo de impacto preditivo no OEE e controlador CLP em malha fechada."""

import pytest

from src.oee.calculator import calculate_oee_from_counts
from src.oee.predictive_impact import calcular_impacto_preditivo_oee
from src.simulation.plc_controller import avaliar_acao_clp, obter_historico_acoes_clp, limpar_historico_clp


def test_impacto_preditivo_oee_queda_e_perdas():
    oee_base = calculate_oee_from_counts(480.0, 20.0, 1.5, 300, good_count=290)
    assert oee_base["available"] is True

    # Falha grave de classe 3 (Desalinhamento/Trinca) com 90% de probabilidade
    resultado = calcular_impacto_preditivo_oee(
        oee_atual=oee_base,
        tipo_falha_previsto=3,
        probabilidade_falha=0.90,
        score_anomalia=0.85,
    )
    assert resultado["gravidade"] == "CRITICA"
    assert resultado["oee_projetado_sem_intervencao"]["oee"] < resultado["oee_atual"]["oee"]
    assert resultado["impacto"]["queda_oee_pontos_percentuais"] > 0.0
    assert resultado["financeiro"]["perda_total_estimada_brl"] > 5000.0
    assert resultado["financeiro"]["economia_acao_preventiva_brl"] > 0.0


def test_clp_intertravamento_emergencia_nivel_4():
    limpar_historico_clp()
    # Condição crítica: vibração extrema acima de 8 mm/s
    leitura_critica = {
        "id_celula": "CEL-201",
        "vibracao_triaxial_rms_mms": 9.5,
        "temperatura_fuso_c": 98.0,
        "torque_fuso_nm": 180.0,
    }
    acao = avaliar_acao_clp(leitura_critica, tipo_falha_previsto=3, probabilidade_falha=0.95)
    assert acao["nivel_seguranca"] == 4
    assert acao["categoria"] == "EMERGENCY_STOP"
    assert acao["intertravamento_ativo"] is True
    assert acao["ajuste_velocidade_feed_pct"] == 0
    assert len(obter_historico_acoes_clp()) == 1


def test_clp_operacao_normal_nivel_0():
    limpar_historico_clp()
    leitura_normal = {
        "id_celula": "CEL-202",
        "vibracao_triaxial_rms_mms": 1.2,
        "temperatura_fuso_c": 48.0,
        "torque_fuso_nm": 95.0,
        "vazao_refrigerante_lmin": 28.0,
        "pressao_hidraulica_bar": 160.0,
    }
    acao = avaliar_acao_clp(leitura_normal, tipo_falha_previsto=0, probabilidade_falha=0.02)
    assert acao["nivel_seguranca"] == 0
    assert acao["intertravamento_ativo"] is False
    assert acao["ajuste_velocidade_feed_pct"] == 100

