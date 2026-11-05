"""Controlador lógico programável (CLP/PLC) simulado para controle em malha fechada.

Implementa arquitetura de segurança industrial em 4 níveis (conforme IEC 61131 / ISO 13849):
- Nível 0: Operação Nominal (Normal)
- Nível 1: Alerta Preventivo (Notificação em IHM / Sinalizador Amarelo)
- Nível 2: Solicitação de Inspeção de Qualidade (Trigger de Visão Computacional)
- Nível 3: Recomendação de Manutenção / PCM (Desaceleração Feed-Rate e Abertura de OS)
- Nível 4: Intertravamento de Segurança / Parada de Emergência (E-Stop Imediato)
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any


# Buffer circular em memória das últimas 500 ações executadas pelo CLP simulado
HISTORICO_CLP: deque[dict[str, Any]] = deque(maxlen=500)


def avaliar_acao_clp(
    leitura_sensores: dict[str, Any],
    tipo_falha_previsto: int = 0,
    probabilidade_falha: float = 0.0,
    score_anomalia: float = 0.0,
) -> dict[str, Any]:
    """Avalia as regras determinísticas e preditivas para emissão de comandos industriais de CLP."""
    id_celula = str(leitura_sensores.get("id_celula", "CEL-201"))
    temp = float(leitura_sensores.get("temperatura_fuso_c", 50.0))
    vibracao = float(leitura_sensores.get("vibracao_triaxial_rms_mms", 1.5))
    vazao = float(leitura_sensores.get("vazao_refrigerante_lmin", 28.0))
    pressao = float(leitura_sensores.get("pressao_hidraulica_bar", 160.0))
    torque = float(leitura_sensores.get("torque_fuso_nm", 100.0))

    timestamp_utc = datetime.now(timezone.utc).isoformat()

    # 1. Nível 4: Parada de Emergência (E-Stop / Intertravamento Crítico)
    # Condições críticas de dano iminente ao maquinário ou operador
    e_stop_critico = (
        vibracao >= 8.0
        or temp >= 95.0
        or (tipo_falha_previsto == 3 and probabilidade_falha >= 0.85)
        or (score_anomalia >= 0.90 and vibracao >= 6.5)
        or pressao < 60.0
    )

    if e_stop_critico:
        acao = {
            "timestamp": timestamp_utc,
            "id_celula": id_celula,
            "nivel_seguranca": 4,
            "categoria": "EMERGENCY_STOP",
            "comando_clp": "CMD_ESTOP_DEENERGIZE_MAIN_SPINDLE",
            "status_operacional": "PARADA_DE_EMERGENCIA_ACIONADA",
            "intertravamento_ativo": True,
            "sirene_alarme": True,
            "ajuste_velocidade_feed_pct": 0,
            "solicitar_inspecao_visao": True,
            "abertura_os_pcm": True,
            "prioridade_os": "URGENTE_IMEDIATA",
            "mensagem": (
                f"INTERTRAVAMENTO CRÍTICO ACIONADO NA {id_celula}! "
                f"Condição severa detectada (Vibração={vibracao:.2f}mm/s, Temp={temp:.1f}°C). "
                "Fuso desenergizado e freio mecânico aplicado em <200ms."
            ),
        }
    # 2. Nível 3: Recomendação de Manutenção Preventiva / Desaceleração
    elif (
        tipo_falha_previsto in (1, 2, 3)
        and (probabilidade_falha >= 0.70 or score_anomalia >= 0.75)
    ) or temp >= 85.0 or vazao <= 8.0:
        acao = {
            "timestamp": timestamp_utc,
            "id_celula": id_celula,
            "nivel_seguranca": 3,
            "categoria": "MAINTENANCE_REQUIRED",
            "comando_clp": "CMD_REDUCE_FEED_RATE_25PCT",
            "status_operacional": "OPERACAO_DEGRADADA_CONTROLADA",
            "intertravamento_ativo": False,
            "sirene_alarme": False,
            "ajuste_velocidade_feed_pct": 75,
            "solicitar_inspecao_visao": True,
            "abertura_os_pcm": True,
            "prioridade_os": "ALTA",
            "mensagem": (
                f"Falha iminente classe {tipo_falha_previsto} na {id_celula} (Prob={probabilidade_falha:.1%}, Anomalia={score_anomalia:.2f}). "
                "Velocidade reduzida em 25% pelo CLP. OS emitida para o PCM com parada planejada."
            ),
        }
    # 3. Nível 2: Solicitação de Inspeção por Visão Computacional
    elif (
        score_anomalia >= 0.50
        or (tipo_falha_previsto == 1 and probabilidade_falha >= 0.40)
        or abs(pressao - 160.0) >= 25.0
        or torque >= 170.0
    ):
        acao = {
            "timestamp": timestamp_utc,
            "id_celula": id_celula,
            "nivel_seguranca": 2,
            "categoria": "QUALITY_INSPECTION_TRIGGER",
            "comando_clp": "CMD_TRIGGER_VISION_CAMERA_CAPTURE",
            "status_operacional": "MONITORAMENTO_INSPECAO_ATIVA",
            "intertravamento_ativo": False,
            "sirene_alarme": False,
            "ajuste_velocidade_feed_pct": 100,
            "solicitar_inspecao_visao": True,
            "abertura_os_pcm": False,
            "prioridade_os": None,
            "mensagem": (
                f"Sinal de trigger enviado para câmera de visão na {id_celula}. "
                "Inspeção geométrica e térmica acionada para garantir conformidade do lote."
            ),
        }
    # 4. Nível 1: Alerta Preventivo (Aviso ao Operador na IHM)
    elif score_anomalia >= 0.35 or probabilidade_falha >= 0.30:
        acao = {
            "timestamp": timestamp_utc,
            "id_celula": id_celula,
            "nivel_seguranca": 1,
            "categoria": "PREVENTIVE_WARNING",
            "comando_clp": "CMD_SET_YELLOW_STACK_LIGHT",
            "status_operacional": "ALERTA_OPERACIONAL_AMARELO",
            "intertravamento_ativo": False,
            "sirene_alarme": False,
            "ajuste_velocidade_feed_pct": 100,
            "solicitar_inspecao_visao": False,
            "abertura_os_pcm": False,
            "prioridade_os": None,
            "mensagem": (
                f"Sinalizador luminoso amarelo acionado na {id_celula}. "
                "Parâmetros próximos do limite estatístico; operador orientado a acompanhar IHM."
            ),
        }
    # 5. Nível 0: Operação Nominal
    else:
        acao = {
            "timestamp": timestamp_utc,
            "id_celula": id_celula,
            "nivel_seguranca": 0,
            "categoria": "NORMAL_OPERATION",
            "comando_clp": "CMD_STATUS_GREEN_STEADY",
            "status_operacional": "OPERACAO_NOMINAL_NORMAL",
            "intertravamento_ativo": False,
            "sirene_alarme": False,
            "ajuste_velocidade_feed_pct": 100,
            "solicitar_inspecao_visao": False,
            "abertura_os_pcm": False,
            "prioridade_os": None,
            "mensagem": f"Célula {id_celula} operando em condições nominais com estabilidade de processo.",
        }

    # Registra no buffer de telemetria
    HISTORICO_CLP.append(acao)
    return acao


def obter_historico_acoes_clp(limite: int = 50) -> list[dict[str, Any]]:
    """Retorna os registros mais recentes de ações do CLP."""
    return list(HISTORICO_CLP)[-limite:]


def limpar_historico_clp() -> None:
    """Limpa o buffer de telemetria do CLP."""
    HISTORICO_CLP.clear()

