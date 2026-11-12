"""Página 9: Parecer Técnico — Governança Industrial, Regulamentações e Segurança OT/IT."""

from __future__ import annotations

import streamlit as st

from frontend.components.header import render_header
from frontend.components.icons import svg_icon
from frontend.components.kpi_card import render_kpi
from frontend.styles import DESIGN_TOKENS


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    render_header(
        title="Parecer Técnico & Governança Industrial",
        description="Conformidade regulatória: LGPD, EU AI Act (IA de Alto Risco), Cibersegurança OT/IT (IEC 62443) e ESG.",
        icon="file_check",
        context_badge=("AUDITADO / CONFORME", "success"),
    )

    # 1. Indicadores de Status Regulatório
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("LGPD (Lei 13.709)", "100% Conforme", "Sem PII na telemetria", "verified", "success")
    with k2:
        render_kpi("EU AI Act", "Alto Risco", "Supervisão humana (HITL)", "shield_check", "primary")
    with k3:
        render_kpi("IEC 62443 (OT/IT)", "Segmentada", "Modelo Purdue Nível 0-4", "factory", "success")
    with k4:
        render_kpi("ESG Industrial", "Eixo E / S / G", "Redução de refugo e ruído", "speed", "success")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Seções Técnicas Detalhadas em Abas Profissionais
    t1, t2, t3, t4 = st.tabs(
        [
            "1. Privacidade e LGPD",
            "2. EU AI Act (IA Ética)",
            "3. Cibersegurança OT/IT (IEC 62443)",
            "4. ESG & Sustentabilidade",
        ]
    )

    with t1:
        st.markdown(
            """
            **Minimização de Dados e Anonimização**
            - O sistema processa estritamente dados termodinâmicos e mecânicos de máquinas industriais (temperatura, vibração, torque, pressão e vazão).
            - Não há armazenamento de dados pessoais sensíveis ou identificadores individuais de operadores nas tabelas de telemetria analítica.
            - Registros operacionais são indexados exclusivamente por código de célula industrial (`CEL-201` a `CEL-204`) e turno de produção.
            """
        )

    with t2:
        st.markdown(
            """
            **Enquadramento de Alto Risco e Transparência**
            - Sistemas de automação de segurança fabril são enquadrados no **Anexo III do EU AI Act**.
            - **Supervisão Humana no Circuito (Human-in-the-Loop):** Paradas não emergenciais e ajustes de parâmetros exigem validação dos técnicos do PCM.
            - **Explicabilidade:** Modelos de árvores de decisão (Random Forest) disponibilizam importância de variáveis físicas sem caixa-preta.
            """
        )

    with t3:
        st.markdown(
            """
            **Segmentação de Redes Industriais (Modelo Purdue)**
            - **Zona OT (Níveis 0 a 2):** Barramentos determinísticos (Fieldbus / Profinet) isolados fisicamente da internet corporativa.
            - **Zona IDMZ (Nível 3.5):** Barreira com Firewall e fila segura para comunicação com a API REST FastAPI.
            - **Intertravamento Hardwired:** O circuito de parada de emergência de Nível 4 possui relé eletromecânico independente da rede de dados.
            """
        )

    with t4:
        st.markdown(
            """
            **Eficiência Material e Proteção Ocupacional**
            - **Redução de Refugo em Ligas Nobres:** Prevenção de perda de peças brutas de titânio (Ti-6Al-4V) e aço inoxidável 316L.
            - **Eficiência Energética:** Redução de perdas elétricas parasitas causadas por atrito em fusos desgastados.
            - **Saúde Ocupacional:** Monitoramento de ruído em dB para atendimento aos limites da NR-15.
            """
        )


if __name__ in ("__main__", "__page__"):
    from frontend.components.sidebar import run_standalone_page

    run_standalone_page("Parecer Técnico")
