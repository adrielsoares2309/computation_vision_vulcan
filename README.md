# VulcanTech Smart Metals S.A. — Plataforma Industrial de IA, OEE e Visão Computacional

Plataforma industrial completa da **VulcanTech Smart Metals S.A.** para monitoramento de Eficiência Global do Equipamento (**OEE**), inspeção dimensional e térmica por **Visão Computacional (OpenCV)**, diagnóstico de ativos por **Machine Learning Supervisionado e Não Supervisionado** e automação de segurança com **CLP em Malha Fechada**.

Desenvolvida com base nos requisitos do documento oficial `docs/Projeto Integrador Avançado certoo.pdf`.

---

## 1. Destaques da Solução

- **Recall de Falhas em Teste Temporal:** **99.07%** (meta: $\ge 90\%$) com ensemble `RandomForestClassifier` e `XGBClassifier`.
- **Detecção de Anomalias:** `Isolation Forest` não supervisionado para mitigação de falhas incipientes com escore calibrado.
- **Engenharia de Features:** Índice de Esforço Mecânico ($\text{IEM} = (\text{Torque} \times \text{Vibração}) / (\text{Vazão} + 1)$), janelas móveis de 30m e 2h por célula, normalização e Z-score condicionais por liga metálica.
- **Visão Computacional OpenCV:**
  - Inspeção Geométrica do Cordão: escala de cinza, filtro unsharp, detector de bordas de Canny, extração de contornos, medição de perfil de largura, detecção de descontinuidades e cálculo percentual de porosidade (ISO 5817).
  - Análise Termográfica: conversão para o espaço de cor HSV, segmentação de hotspots na poça de fusão e cálculo percentual da Zona Afetada pelo Calor (ZAC/HAZ).
- **OEE & Impacto Preditivo:** Fórmulas físicas oficiais ($A \times P \times Q$), cálculo de perdas financeiras (custo hora parada de R\$ 4.500/h e refugo de R\$ 850/un) e ROI de manutenção preventiva.
- **CLP em Malha Fechada (IEC 61131 / ISO 13849):** 5 níveis determinísticos de segurança (Nível 0 Verde a Nível 4 E-Stop com desenergização do fuso em $<200\text{ ms}$).
- **API RESTful FastAPI:** 42 rotas documentadas em `/docs` e `/redoc`.
- **Frontend SCADA Streamlit:** 9 páginas industriais especializadas com paleta de alto contraste MES/SCADA e conformidade WCAG 2.2.
- **Qualidade de Código:** 53 testes automatizados (`pytest`) com 100% de aprovação.

---

## 2. Inicialização Rápida

### 2.1. Execução Local via PowerShell
Para inicializar o ecossistema completo (banco SQLite + FastAPI na porta `8000` + Streamlit na porta `8501`):

```powershell
.\iniciar_aplicacao.ps1
```

Com lote demonstrativo inicial populado no simulador:
```powershell
.\iniciar_aplicacao.ps1 -SeedSimulatedData
```

### 2.2. Execução Conteinerizada via Docker Compose
```bash
docker-compose up --build -d
```
- **Cockpit SCADA Streamlit:** `http://localhost:8501`
- **Backend FastAPI:** `http://localhost:8000`
- **Documentação Interativa Swagger:** `http://localhost:8000/docs`

---

## 3. Estrutura das 9 Páginas do Streamlit

1. **Dashboard Geral:** Cockpit SCADA executivo com status das 4 células (`CEL-201` a `CEL-204`), lâmpadas piloto, OEE global e histórico recente de intertravamentos de CLP.
2. **Monitoramento em Tempo Real:** Leituras dos 7 sensores, exibição em destaque do IEM, Z-scores da liga metálica e gráficos de séries temporais.
3. **Manutenção Preditiva:** Classificação multiclasse de falhas em tempo real, probabilidades por classe, matriz de risco e detector de anomalias (Isolation Forest).
4. **OEE e Eficiência Industrial:** Decomposição fatorial ($A, P, Q$), simulador de impacto preditivo no OEE e calculadora de perdas financeiras.
5. **Visão Computacional:** Inspeção geométrica via OpenCV Canny/contornos/porosidade + análise termográfica HSV da ZAC/HAZ + galeria de corpos de prova.
6. **Análise de Dados (EDA):** Distribuição multivariada pelas 3 ligas metálicas, comportamento do IEM, correlação cruzada e boxplots estatísticos.
7. **Modelos de IA:** Benchmark comparativo (Random Forest vs XGBoost vs Isolation Forest), matriz de confusão e ranking de importância de variáveis.
8. **Simulador Industrial:** Injeção controlada de falhas nos sensores e monitor de comandos determinísticos do CLP em malha fechada.
9. **Parecer Técnico:** Documento de conformidade com LGPD (Lei 13.709/2018), EU AI Act (IA de Alto Risco), Cibersegurança OT/IT (IEC 62443) e ESG.

---

## 4. Estrutura do Repositório

```text
VulcanTech Smart Metals S.A/
├── iniciar_aplicacao.ps1        # Script de inicialização completa (FastAPI + Streamlit)
├── Dockerfile                   # Build conteinerizado do ecossistema
├── docker-compose.yml           # Orquestração do Backend e Frontend
├── .dockerignore                # Exclusões de build Docker
├── requirements.txt             # Dependências Python (FastAPI, Streamlit, XGBoost, OpenCV, etc.)
├── backend/                     # API FastAPI e rotas RESTful (/api/v1)
│   ├── main.py                  # Ponto de entrada da API e middlewares
│   ├── routes/                  # Rotas (industrial, oee, vision, predictive_maintenance, simulation, sensors, health)
│   ├── services/                # Camada de serviços de negócio
│   └── schemas/                 # Modelos de validação Pydantic v2
├── frontend/                    # Interface Streamlit industrial
│   ├── app.py                   # Ponto de entrada do Streamlit
│   ├── components/              # Sidebar MES, gauges, cards e tokens visuais
│   ├── pages/                   # 9 páginas industriais especializadas
│   └── styles.py                # Identidade visual MES/SCADA e WCAG 2.2
├── src/                         # Módulos de domínio técnico industrial
│   ├── data/                    # Pipeline de saneamento, interpolação e feature engineering (IEM)
│   ├── ml/                      # Treinamento supervisionado, avaliação e Isolation Forest
│   ├── oee/                     # Cálculo do OEE físico e impacto preditivo financeiro
│   ├── simulation/              # Simulador de sensores, eventos e controlador de CLP
│   └── vision/                  # OpenCV: inspeção dimensional (Canny) e termografia (HSV/HAZ)
├── database/                    # Persistência SQLite (schema.sql, db.py, repositórios)
├── models/tabular/              # Artefatos treinados (.joblib) e metadados (.json)
├── reports/                     # Gráficos, matrizes de confusão e relatórios analíticos
├── tests/                       # 53 testes automatizados cobrindo todo o sistema
└── docs/                        # Documentação técnica e regulatória detalhada
    ├── ARQUITETURA.md           # Arquitetura em camadas e modelo Purdue
    ├── PIPELINE_DADOS.md        # Saneamento e Feature Engineering
    ├── MODELOS_ML.md            # Benchmark de IA e métricas de teste
    ├── VISAO_COMPUTACIONAL.md   # OpenCV Canny, contornos, porosidade e HSV/HAZ
    ├── OEE.md                   # Metodologia de cálculo e impacto financeiro
    ├── API.md                   # Catálogo completo das 42 rotas REST
    ├── PARECER_TECNICO.md       # LGPD, EU AI Act, Cibersegurança OT/IT e ESG
    ├── EXECUCAO.md              # Guia de execução local e Docker
    ├── AUDITORIA_INICIAL.md     # Auditoria completa do projeto
    └── ACOMPANHAMENTO_REQUISITOS.md # Matriz de rastreabilidade 100% concluída
```

---

## 5. Validação com Testes Automatizados

Para executar toda a suíte de testes do projeto:
```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v
```
Resultado: **53 testes executados com 100% de sucesso**.
