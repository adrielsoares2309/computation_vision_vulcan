"""Página 9: Parecer Técnico — Governança de IA, LGPD, EU AI Act, Cibersegurança OT/IT e ESG."""

from __future__ import annotations

import streamlit as st
from frontend.styles import DESIGN_TOKENS


def render() -> None:
    c = DESIGN_TOKENS["colors"]

    st.markdown(
        """
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin:0; font-size:1.6rem; color:#0F172A; font-weight:800;">
                PARECER TÉCNICO & GOVERNANÇA INDUSTRIAL
            </h1>
            <div style="font-size:0.85rem; color:#475569; font-weight:500;">
                Relatório de conformidade regulatória: LGPD, EU AI Act, Cibersegurança OT/IT (IEC 62443) e ESG
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4 = st.tabs([
        "1. LGPD (Lei 13.709/2018)",
        "2. EU AI Act (IA Ética)",
        "3. Cibersegurança OT/IT (IEC 62443)",
        "4. ESG & Sustentabilidade Industrial",
    ])

    with t1:
        st.markdown(
            """
            ### 1. Conformidade com a Lei Geral de Proteção de Dados (LGPD)

            #### Natureza dos Dados Processados
            - O sistema **VulcanTech-OEE** opera estritamente sobre **telemetria operacional de máquinas** (temperatura, vibração, torque, pressão, corrente, nível sonoro e imagens termográficas de juntas soldadas).
            - **Não há coleta nem armazenamento de dados pessoais sensíveis** de operadores de chão de fábrica nas tabelas de telemetria e inferência analítica.
            - Registros de turnos industriais (`MANHA`, `TARDE`, `NOITE`) identificam apenas a equipe coletiva de operação e não vinculam CPF, biometria ou dados cadastrais individuais.

            #### Diretrizes de Privacidade e Boas Práticas Adotadas
            1. **Minimização de Dados (Art. 6º, III):** Coleta restrita aos parâmetros termodinâmicos e mecânicos estritamente necessários para o cálculo do OEE e manutenção preditiva.
            2. **Logs Auditáveis (Art. 37):** Registro transparente de todas as inferências e comandos de CLP com timestamp UTC indelével.
            3. **Retenção e Descarte (Art. 16):** Política de expurgo periódico de telemetria de alta frequência após consolidação estatística em lote.
            """
        )

    with t2:
        st.markdown(
            """
            ### 2. Alinhamento ao Regulamento Europeu de IA (EU AI Act)

            #### Enquadramento de Risco
            - Sob a ótica do **EU AI Act (Regulation EU 2024/1689)**, sistemas de inteligência artificial aplicados à supervisão e intertravamento de segurança em infraestrutura fabril enquadram-se na categoria de **Alto Risco (High-Risk AI Systems - Anexo III)**, exigindo garantias de confiabilidade, transparência e governança.

            #### Pilares de Governança Implementados no VulcanTech-OEE
            1. **Supervisão Humana no Circuito (Human-in-the-Loop - HITL):** O modelo emite diagnósticos e recomendações de manutenção; paradas não emergenciais requerem validação ou atuação de técnicos de PCM.
            2. **Transparência e Explicabilidade:** Utilização de árvores de decisão e cálculo de importância de variáveis (Random Forest / XGBoost), permitindo ao engenheiro entender a causa raiz da predição (ex.: IEM elevado decorrente de torque vs vibração).
            3. **Acurácia e Robustez:** Teste estrito em split cronológico sem vazamento de dados, atingindo **Recall de falhas superior a 90%** em ambiente simulado.
            4. **Métricas de Falsa Certeza:** Sinalização expressa de que escores de similaridade de protótipos de visão computacional representam distâncias métricas e não probabilidades calibradas.
            """
        )

    with t3:
        st.markdown(
            """
            ### 3. Cibersegurança em Redes Operacionais (OT/IT — IEC 62443 / NIST SP 800-82)

            #### Arquitetura de Segmentação (Modelo Purdue)
            - **Zona OT (Nível 0 a Nível 2):** Redes de barramento industrial (Fieldbus / Modbus TCP / Profinet) isoladas fisicamente de acessos externos. Controladores CLP operam sob lógica determinística prioritária.
            - **Zona Desmilitarizada Industrial (IDMZ - Nível 3.5):** Barreira com Firewall de inspeção profunda (DPI) entre a rede de TI corporativa e a rede fabril. A API REST FastAPI consome telemetria via fila segura unidirecional.
            - **Zona IT / Nuvem (Nível 4 e 5):** Dashboards gerenciais Streamlit e relatórios ERP/MES.

            #### Salvaguardas de Cibersegurança
            1. **Intertravamento Hardwired de Segurança:** Paradas de emergência de Nível 4 possuem relé de segurança eletromecânico independente da rede IP, impedindo que falhas de software ou ataques cibernéticos desativem a segurança física.
            2. **Autenticação e Integridade de Modelos:** Artefatos de Machine Learning (`.joblib`) protegidos com checksum SHA-256 verificado antes da carga em memória.
            """
        )

    with t4:
        st.markdown(
            """
            ### 4. Sustentabilidade e Governança ESG (Environmental, Social, Governance)

            #### Eficiência de Recursos e Economia Circular (Eixo E)
            - **Redução de Refugo em Ligas Nobres:** A usinagem de titânio (Ti-6Al-4V) e aço inoxidável 316L gera alto impacto ambiental na extração e conformação. A detecção preditiva de desvios de processo evita a perda de lotes completos de peças nobres.
            - **Eficiência Energética:** O fuso de usinagem e as bombas de refrigeração representam mais de 70% da demanda elétrica da célula. A detecção antecipada de atrito e desgaste de insertos reduz perdas energéticas parasitas.

            #### Segurança do Trabalho e Ergonomia (Eixo S)
            - O intertravamento automático de segurança (E-Stop em <200ms) elimina riscos de acidentes com ruptura catastrófica de ferramenta e projeção de estilhaços metálicos em direção aos operadores.
            - Acompanhamento do nível sonoro (dB) para controle de limites de exposição ocupacional (NR-15).

            #### Governança Corporativa e Confiabilidade (Eixo G)
            - Monitoramento em tempo real do OEE auditável por órgãos de controle e acionistas, com separação inequívoca entre dados históricos de produção e telemetria sintética de simulação.
            """
        )


if __name__ in ('__main__', '__page__'):
    from frontend.components.sidebar import run_standalone_page
    run_standalone_page('Parecer Técnico')
