"""Quantificação do impacto preditivo de falhas e anomalias no OEE e perdas financeiras."""

from __future__ import annotations

from typing import Any

from .calculator import calculate_oee_from_counts


# Custos operacionais industriais padrão VulcanTech
CUSTO_HORA_PARADA_BRL = 4500.0  # R$ por hora de parada não planejada
CUSTO_REJEITO_PECA_BRL = 850.0   # R$ por peça de liga nobre descartada (Titânio/316L)

# Estimativa de MTTR (Mean Time to Repair) e perdas por tipo de falha
PARAMETROS_FALHAS = {
    0: {
        "nome": "Operação Normal",
        "downtime_esperado_min": 0.0,
        "penalidade_velocidade_pct": 0.0,
        "taxa_rejeito_adicional_pct": 0.0,
        "gravidade": "NULA",
    },
    1: {
        "nome": "Desgaste de Ferramenta",
        "downtime_esperado_min": 45.0,  # Troca de insertos / ferramenta
        "penalidade_velocidade_pct": 8.0,
        "taxa_rejeito_adicional_pct": 4.5,
        "gravidade": "MEDIA",
    },
    2: {
        "nome": "Falha de Refrigeração",
        "downtime_esperado_min": 90.0,  # Troca de bomba / purga / desobstrução
        "penalidade_velocidade_pct": 15.0,
        "taxa_rejeito_adicional_pct": 9.0,
        "gravidade": "ALTA",
    },
    3: {
        "nome": "Desalinhamento / Trinca Estrutural",
        "downtime_esperado_min": 180.0,  # Realinhamento de fuso / calibração geométrica
        "penalidade_velocidade_pct": 30.0,
        "taxa_rejeito_adicional_pct": 18.0,
        "gravidade": "CRITICA",
    },
}


def calcular_impacto_preditivo_oee(
    oee_atual: dict[str, Any],
    tipo_falha_previsto: int = 0,
    probabilidade_falha: float = 0.0,
    score_anomalia: float = 0.0,
    custo_hora_parada: float = CUSTO_HORA_PARADA_BRL,
    custo_peca_rejeito: float = CUSTO_REJEITO_PECA_BRL,
) -> dict[str, Any]:
    """Calcula a degradação projetada no OEE caso a falha prevista não seja tratada preventivamente.

    Avalia:
    1. Penalização na Disponibilidade por parada corretiva não planejada.
    2. Penalização no Desempenho por perda de rotação/velocidade.
    3. Penalização na Qualidade por tolerâncias geométricas violadas.
    4. Estimativa de perdas financeiras (parada + refugo).
    5. Ganho e ROI de ação preditiva imediata.
    """
    if not oee_atual.get("available", False):
        raise ValueError("O registro de OEE atual fornecido não é válido para projeção.")

    tempo_planejado = float(oee_atual["planned_time_min"])
    downtime_atual = float(oee_atual["downtime_min"])
    tempo_operacao_atual = float(oee_atual["operating_time_min"])
    producao_total_atual = int(oee_atual["total_count"])
    boas_atual = int(oee_atual["good_count"])
    rejeitadas_atual = int(oee_atual["rejected_count"])
    ciclo_ideal = tempo_operacao_atual / max(producao_total_atual, 1) if producao_total_atual > 0 else 1.0

    # Fator de ponderação do risco: probabilidade da falha combinada com anomalia
    fator_risco = max(float(probabilidade_falha), float(score_anomalia), 0.0)
    params_falha = PARAMETROS_FALHAS.get(int(tipo_falha_previsto), PARAMETROS_FALHAS[0])

    # 1. Projeção de Parada Não Planejada adicional (Impacto em Disponibilidade)
    downtime_adicional_projetado = params_falha["downtime_esperado_min"] * fator_risco
    downtime_projetado = min(tempo_planejado, downtime_atual + downtime_adicional_projetado)
    tempo_operacao_projetado = max(0.0, tempo_planejado - downtime_projetado)

    # 2. Projeção de Perda de Desempenho
    fator_velocidade = 1.0 - (params_falha["penalidade_velocidade_pct"] / 100.0 * fator_risco)
    fator_velocidade = max(0.2, min(1.0, fator_velocidade))

    # Produção projetada proporcional ao tempo de operação e velocidade
    taxa_producao_atual = producao_total_atual / max(tempo_operacao_atual, 1.0)
    producao_projetada = int(taxa_producao_atual * tempo_operacao_projetado * fator_velocidade)

    # 3. Projeção de Perda de Qualidade (Refugo adicional)
    taxa_rejeito_adicional = (params_falha["taxa_rejeito_adicional_pct"] / 100.0) * fator_risco
    taxa_rejeito_atual = rejeitadas_atual / max(producao_total_atual, 1)
    taxa_rejeito_projetada = min(0.60, taxa_rejeito_atual + taxa_rejeito_adicional)

    rejeitadas_projetadas = int(round(producao_projetada * taxa_rejeito_projetada))
    boas_projetadas = max(0, producao_projetada - rejeitadas_projetadas)

    # Cálculo do novo OEE degradado
    try:
        resultado_degradado = calculate_oee_from_counts(
            planned_time_min=tempo_planejado,
            downtime_min=downtime_projetado,
            ideal_cycle_time_min=ciclo_ideal,
            total_count=producao_projetada,
            good_count=boas_projetadas,
        )
    except Exception:
        resultado_degradado = {
            "availability": oee_atual["availability"],
            "performance": oee_atual["performance"],
            "quality": oee_atual["quality"],
            "oee": oee_atual["oee"],
        }

    # 4. Cálculo de Impactos Financeiros
    horas_parada_adicional = downtime_adicional_projetado / 60.0
    custo_downtime = horas_parada_adicional * custo_hora_parada

    pecas_refugo_adicional = max(0, rejeitadas_projetadas - rejeitadas_atual)
    custo_refugo = pecas_refugo_adicional * custo_peca_rejeito

    perda_financeira_total = custo_downtime + custo_refugo

    # Economia com ação preventiva estimada em 75% da perda evitada
    economia_preventiva_estimada = perda_financeira_total * 0.75

    oee_atual_pct = float(oee_atual.get("oee", 0.0) or 0.0)
    oee_projetado_pct = float(resultado_degradado.get("oee", oee_atual_pct) or oee_atual_pct)
    queda_oee_pontos = round(oee_atual_pct - oee_projetado_pct, 2)

    return {
        "tipo_falha_previsto": int(tipo_falha_previsto),
        "nome_falha": params_falha["nome"],
        "gravidade": params_falha["gravidade"],
        "fator_risco": round(fator_risco, 3),
        "oee_atual": {
            "disponibilidade": oee_atual.get("availability"),
            "desempenho": oee_atual.get("performance"),
            "qualidade": oee_atual.get("quality"),
            "oee": oee_atual.get("oee"),
        },
        "oee_projetado_sem_intervencao": {
            "disponibilidade": resultado_degradado.get("availability"),
            "desempenho": resultado_degradado.get("performance"),
            "qualidade": resultado_degradado.get("quality"),
            "oee": resultado_degradado.get("oee"),
        },
        "impacto": {
            "queda_oee_pontos_percentuais": max(0.0, queda_oee_pontos),
            "downtime_adicional_previsto_min": round(downtime_adicional_projetado, 1),
            "pecas_refugo_adicionais": int(pecas_refugo_adicional),
        },
        "financeiro": {
            "custo_downtime_brl": round(custo_downtime, 2),
            "custo_refugo_brl": round(custo_refugo, 2),
            "perda_total_estimada_brl": round(perda_financeira_total, 2),
            "economia_acao_preventiva_brl": round(economia_preventiva_estimada, 2),
        },
        "recomendacao_operacional": (
            "Ação preventiva imediata recomendada para evitar parada não planejada e refugo de lote."
            if fator_risco >= 0.40
            else "Monitoramento contínuo em malha fechada; parâmetros operacionais dentro do controle estatístico."
        ),
    }

