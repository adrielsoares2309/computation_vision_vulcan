# Parecer Técnico e Governança Industrial

**Empresa:** VulcanTech Smart Metals S.A.  
**Projeto:** VulcanTech-OEE — Inteligência Artificial Industrial  
**Normas de Referência:** LGPD (Lei 13.709/2018), EU AI Act (Regulamento UE 2024/1689), IEC 62443, ISO 13849, Diretrizes ESG.

---

## 1. Conformidade com a Lei Geral de Proteção de Dados (LGPD)

O sistema foi arquitetado com base no princípio de **Privacy by Design**:
1. **Dados Estritamente Operacionais:** Os bancos de dados e canais de mensageria processam exclusivamente telemetria física (temperatura, vibração, torque, pressão, corrente, áudio bruto e laudos de imagem).
2. **Ausência de Identificadores Pessoais:** Nenhuma tabela armazena nomes, CPFs, matrículas, endereços IP de operadores ou dados biométricos.
3. **Agregação por Turno Coletivo:** O rastreamento de produção é segregado por turnos industriais (`MANHA`, `TARDE`, `NOITE`), garantindo conformidade com o princípio da **não discriminação** (Art. 6º, IX) e **minimização** (Art. 6º, III).

---

## 2. Alinhamento com o Regulamento de Inteligência Artificial da União Europeia (EU AI Act)

### 2.1. Classificação de Risco
O sistema atua como componente de segurança e otimização em ambiente de manufatura pesada, enquadrando-se nos requisitos de **Sistemas de IA de Alto Risco (High-Risk AI Systems)**:

### 2.2. Mitigações e Salvaguardas Implementadas:
- **Supervisão Humana (Human-in-the-Loop - Artigo 14):** As predições de manutenção preditiva sugerem aberturas de Ordens de Serviço (OS) e reduções de velocidade preventiva, mantendo o operador ou engenheiro de PCM na tomada de decisão final sobre paradas de linha planejadas.
- **Transparência e Explicabilidade (Artigo 13):** Adoção de modelos baseados em árvores (Random Forest / XGBoost) e extração de feature importance, permitindo aos mantenedores rastrear exatamente quais grandezas físicas (ex.: pico de IEM ou queda de vazão) dispararam a classificação de falha.
- **Robustez e Acurácia Técnica (Artigo 15):** Validação estrita em split temporal que alcançou **Recall de falhas de 99.07%**, minimizando o risco de paradas catastróficas não detectadas (falsos negativos).

---

## 3. Cibersegurança em Ambientes Operacionais (OT/IT — IEC 62443 / NIST SP 800-82)

1. **Intertravamento Hardwired Físico:** Paradas de Emergência (Nível 4 do CLP) contam com linha física de emergência (relé de segurança eletromecânico e botoeira cogumelo) em paralelo com o software, garantindo que o fuso seja desenergizado em $< 200\text{ ms}$ mesmo em caso de falha de comunicação ou ataque de rede.
2. **Integridade de Modelos Analíticos:** Todos os artefatos de IA persistidos possuem hash SHA-256 verificado antes da carga pelo serviço FastAPI.
3. **Segregação de Rede:** O backend atua em camada intermediária (DMZ Industrial), isolando o barramento Modbus/CLP do acesso direto pelos navegadores de internet.

---

## 4. Governança ESG e Sustentabilidade Industrial

- **Ambiental (E):** Redução comprovada do descarte de peças usinadas em ligas nobres (como titânio aeroespacial e aço 316L). A antecipação de falhas de refrigeração e desgaste de insertos evita o refugo de peças semi-acabadas de alto valor agregado e diminui o consumo elétrico parasita por atrito excessivo.
- **Social (S):** O sistema previne a quebra catastrófica de ferramentas em alta rotação (acima de 12.000 RPM), eliminando riscos de projeção de estilhaços e acidentes com operadores na célula. O monitoramento contínuo de ruído (dB) atua na prevenção de doenças ocupacionais auditivas (NR-15).
- **Governança (G):** Transparência total nos cálculos de OEE, auditáveis pelo conselho administrativo e clientes da cadeia aeroespacial e biomédica.

