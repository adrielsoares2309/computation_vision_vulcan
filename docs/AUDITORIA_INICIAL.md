# AUDITORIA INICIAL COMPLETA — PROJETO VULCANTECH-OEE

**Data da Auditoria:** 2026-11-05  
**Responsável Técnico:** Engenheiro de Software Sênior, Engenheiro de Dados Industriais & Especialista em MLOps / Visão Computacional  
**Referência Técnica Oficial:** `Projeto Integrador Avançado.pdf` (VulcanTech Smart Metals S.A.)  

---

## 1. ESTRUTURA ATUAL ENCONTRADA NO REPOSITÓRIO

A inspeção do repositório identificou os seguintes arquivos e diretórios:

```text
VulcanTech Smart Metals S.A/
├── backend/                             # API RESTful FastAPI
│   ├── routes/                          # health, oee, predictive_maintenance, sensors, simulation, vision
│   ├── schemas/                         # Schemas Pydantic v2
│   ├── services/                        # ml_service, oee_service, sensor_service, simulation_service, vision_service
│   ├── config.py                        # Configurações centralizadas
│   ├── dependencies.py                  # Injeção de dependências
│   └── main.py                          # Ponto de entrada FastAPI e middlewares CORS
├── data/
│   ├── processed/                       # Datasets tratados em Parquet e CSV (10.000 linhas)
│   │   ├── dados_sensores_vulcantech_tratados.csv
│   │   ├── dados_sensores_vulcantech_tratados.parquet
│   │   └── vision/labels.csv
│   └── raw/
│       ├── dados_sensores_vulcantech.csv # Dataset bruto (10.000 linhas, com ruídos e NaNs)
│       └── imagens/                     # 4 imagens semente (ópticas e térmicas)
│           ├── solda_aprovada.png
│           ├── solda_reprovada.png
│           ├── termica_solda_aprovada.png
│           └── termica_solda_reprovada.png
├── database/                            # Persistência relacional SQLite
│   ├── db.py, repositories.py, schema.sql, vulcantech.db
├── docs/                                # Documentação técnica e PDFs de referência
│   ├── idealização
│   ├── Projeto Integrador Avançado certoo.pdf
│   └── Prática tabela.xlsx
├── frontend/                            # Aplicação Streamlit
│   ├── app.py                           # Ponto de entrada Streamlit
│   ├── styles.py                        # Design tokens e verificação de contraste WCAG 2.2
│   ├── components/                      # charts, header, icons, kpi_card, sidebar
│   ├── pages/                           # oee.py, predictive_maintenance.py, vision.py
│   └── services/                        # api_client.py, ml_service.py, oee_service.py, vision_service.py
├── models/
│   ├── tabular/                         # best_model.joblib, random_forest.joblib, extra_trees.joblib, etc.
│   └── vision/                          # visual_model.joblib, termica_model.joblib (HOG + KNN experimental)
├── notebooks/
│   └── limpeza.ipynb                    # Análise exploratória e tratamento inicial de sentinelas
├── reports/
│   ├── architecture/                    # Relatórios de integração e contratos
│   ├── ml/                              # Métricas, matriz de confusão e feature importances
│   └── vision/                          # Relatório de dataset e avaliação experimental
├── src/                                 # Módulos de domínio industrial puro
│   ├── data/                            # validator.py, cleaner.py
│   ├── ml/                              # train.py, predict.py, evaluate.py
│   ├── oee/                             # availability.py, performance.py, quality.py, calculator.py
│   ├── simulation/                      # sensor_simulator.py, event_generator.py
│   └── vision/                          # dataset.py, preprocessing.py, train.py, predict.py, evaluate.py
├── tests/                               # 35 testes automatizados (pytest)
│   ├── test_api.py, test_frontend_client.py, test_ml.py, test_oee.py, test_vision.py
├── iniciar_aplicacao.ps1                # Script PowerShell de inicialização
├── requirements.txt                     # Dependências do projeto
└── README.md                            # Documento introdutório
```

---

## 2. TECNOLOGIAS E AMBIENTE UTILIZADOS

- **Linguagem & Runtime:** Python 3.14.6 no ambiente virtual local (`venv/`).
- **Engenharia de Dados:** Pandas 3.1.0, NumPy 2.5.4, SciPy 1.18.1, PyArrow 26.0.0.
- **Machine Learning:** Scikit-Learn 1.9.1, XGBoost 3.4.1 (instalado na auditoria), Imbalanced-Learn 0.14.2 (instalado na auditoria), Joblib 1.6.0.
- **Visão Computacional:** OpenCV (`opencv-python` 5.0.0.93), Pillow 12.1.1.
- **Backend & APIs:** FastAPI 0.162.0, Uvicorn, Pydantic v2, Python-Multipart 0.0.32.
- **Persistência:** SQLite3 com schema estruturado e rastreamento de `data_source` (`historical`, `simulated`, `api`).
- **Frontend & Visualização:** Streamlit 1.66.1, Streamlit Option Menu 0.4.0, Streamlit Autorefresh 1.0.1, Plotly, Matplotlib, Seaborn.
- **Qualidade & Testes:** Pytest 9.2.0, HTTPX 0.28.1.
- **Conteinerização:** Docker Engine 25.0.2 disponível no host.

---

## 3. AUDITORIA DETALHADA POR REQUISITO DO DOCUMENTO OFICIAL

Para cada item de requisito do `Projeto Integrador Avançado.pdf`, a situação foi rigorosamente inspecionada no código:

| Requisito do Documento Oficial | Situação Atual | Evidências e Arquivos Inspecionados | Lacunas / Ações Necessárias |
|---|---|---|---|
| **Etapa 1.1: Inspeção e Limpeza Estrutural** (Quantificar NaNs por célula/liga, interpolação temporal por `id_celula`) | **PARCIALMENTE IMPLEMENTADO** | `notebooks/limpeza.ipynb` e `src/data/cleaner.py`. NaNs foram interpolados offline para gerar o Parquet processado. | Falta exportar essas rotinas em um módulo de engenharia reutilizável (`src/data/pipeline.py`) com relatório programático. |
| **Etapa 1.2: Tratamento de Ruído Eletromagnético** (Vibração -99.0, Temp 999.9, Pressão -1.0 com limites operacionais e Z-Score condicional por liga) | **PARCIALMENTE IMPLEMENTADO** | `src/data/validator.py` e `src/data/cleaner.py` detectam sentinelas e limites físicos, mas o Z-Score condicional por liga metálica não foi implementado. | Implementar Z-Score condicional por liga metálica no pipeline de engenharia de dados. |
| **Etapa 1.3: Feature Engineering Dinâmico** (Rolling Mean/Std em 30 min e 2h, Índice de Esforço Mecânico IEM, Normalização por liga metálica) | **NÃO IMPLEMENTADO** | O arquivo `data/processed/dados_sensores_vulcantech_tratados.parquet` possui apenas as 11 colunas brutas tratadas. Não há IEM nem Rolling features calculadas. | Implementar `src/data/feature_engineering.py` calculando $IEM = \frac{\text{Torque} \times \text{Vibração}}{\text{Vazão} + 1}$, rolling windows e normalização por liga. |
| **Etapa 2.1: Tratamento de Desbalanceamento** (Divisão temporal 70%/30%, SMOTE ou `class_weight='balanced'`) | **PARCIALMENTE IMPLEMENTADO** | `src/ml/train.py` usa divisão temporal e `class_weight='balanced'`, mas SMOTE não havia sido avaliado. | Comparar SMOTE e ponderação com `imbalanced-learn` no pipeline de retreinamento. |
| **Etapa 2.2: Modelagem Multiclasse Ensemble** (Random Forest vs XGBoost / LightGBM para 4 alvos de `tipo_falha`) | **PARCIALMENTE IMPLEMENTADO** | `src/ml/train.py` treinou Logistic Regression, Random Forest, Extra Trees e Gradient Boosting. XGBoost não estava treinado. | Integrar XGBoost, treinar modelos comparativos com as novas features de engenharia e perseguir meta de Recall >= 90%. |
| **Etapa 2.3: Módulo de Cálculo Preditivo de OEE** (Impacto do estado predito penalizando Disponibilidade ou Qualidade) | **PARCIALMENTE IMPLEMENTADO** | `src/oee/` calcula OEE operacional por somas ponderadas físicas, mas a penalização preditiva formal com base no modelo de IA ainda não estava desacoplada. | Implementar módulo de estimativa preditiva de OEE em `src/oee/predictive_impact.py`. |
| **Etapa 2.4: Explicabilidade e MLOps** (Matriz de confusão, Recall por classe de falha, SHAP Values / Feature Importances, exportação joblib) | **PARCIALMENTE IMPLEMENTADO** | `src/ml/evaluate.py` gera matriz e feature importances, mas SHAP e análise aprofundada de recall por classe de falha precisam ser atualizados com o novo modelo. | Gerar relatório de explicabilidade completo e gráficos atualizados em `reports/ml/`. |
| **Etapa 3.1: Visão Computacional OpenCV - Inspeção Geométrica** (Filtros de nitidez, escala de cinza, Canny, contornos, porosidade e descontinuidade) | **NÃO IMPLEMENTADO** | O módulo `src/vision/` possui apenas descritor HOG + KNN experimental. Não possui implementação do pipeline geométrico de cordão de solda OpenCV. | Implementar `src/vision/weld_inspection.py` contendo filtros de nitidez, Canny, contornos, medição de porosidade e descontinuidade. |
| **Etapa 3.1: Visão Computacional OpenCV - Análise Termográfica HAZ** (Conversão HSV, thresholding, segmentação de sobreaquecimento e área crítica) | **NÃO IMPLEMENTADO** | Ausente em `src/vision/`. Imagens térmicas eram tratadas apenas pelo mesmo HOG+KNN. | Implementar `src/vision/thermal_analysis.py` com conversão HSV, limiarização de zonas quentes e cálculo da área afetada pelo calor. |
| **Etapa 3.2: API RESTful FastAPI** (Endpoints assíncronos com validação Pydantic, rotas para `/predict`, `/predict-batch`, `/health`, etc.) | **IMPLEMENTADO** | `backend/main.py` e rotas sob `/api/v1`. | Adicionar aliases/rotas formais literais solicitadas no PDF (`/api/v1/industrial/*`, `/api/v1/vision/inspect`, etc.). |
| **Etapa 3.3: Conteinerização em Docker** (Dockerfile otimizado e docker-compose.yml para Edge Computing) | **NÃO IMPLEMENTADO** | Inexistentes na raiz do repositório. | Criar `Dockerfile`, `docker-compose.yml` e `.dockerignore` funcionais para backend e frontend. |
| **Etapa 3.4: Parecer Técnico, Regulatório e ESG** (LGPD no chão de fábrica, EU AI Act, Cibersegurança OT/IT, ESG) | **NÃO IMPLEMENTADO** | Ausente em `docs/`. | Criar `docs/PARECER_TECNICO.md` abordando com rigor os 4 pilares regulatórios e industriais. |
| **Simulação em Malha Fechada e CLP** (Cenários de falha, malha fechada, atuação simulada com CLP) | **PARCIALMENTE IMPLEMENTADO** | Simulador gera leituras, mas o registro de comandos e atuação de malha fechada com CLP precisa ser formalizado. | Implementar camada de CLP simulado com histórico de comandos e atuação preventiva. |
| **Interface Streamlit Completa (9 páginas)** (Dashboard Geral, Tempo Real, Preditiva, OEE, Visão, EDA, Modelos IA, Simulador, Parecer) | **PARCIALMENTE IMPLEMENTADO** | Atualmente existem 3 páginas operacionais compactas (`OEE`, `Visão`, `Manutenção`). O Prompt Master exige 9 visões dedicadas. | Expandir o Streamlit para 9 módulos completos com a mesma identidade visual e contraste WCAG 2.2 já aprovados. |
| **Documentação Técnica Completa (11 documentos)** | **PARCIALMENTE IMPLEMENTADO** | Havia documentos dispersos em `reports/architecture/`. | Centralizar e padronizar toda a documentação solicitada na pasta `docs/`. |

---

## 4. PROBLEMAS CRÍTICOS IDENTIFICADOS

1. **Lacuna entre Treinamento e Requisitos de Engenharia de Dados:**
   - O modelo tabular em `models/tabular/best_model.joblib` foi treinado diretamente sobre as 9 variáveis originais do dataset. O PDF exige formalmente variáveis derivadas de processo: **Índice de Esforço Mecânico (IEM)**, médias móveis/desvios móveis de 30 min e 2 horas, e normalização por liga metálica.
   - O Recall da classe 1 (desgaste de ferramenta) no modelo anterior ficou aquém da meta estabelecida de 90%, evidenciando a necessidade dessas features derivadas.
2. **Visão Computacional Incompleta em Relação ao PDF:**
   - O código existente tratava inspeção apenas como extração de HOG + 1-NN sobre 4 imagens. O documento oficial exige explicitamente processamento analítico com OpenCV: **Canny Edge Detection + Contornos** para medição de porosidade e descontinuidade geométrica, e **Segmentação HSV + Thresholding** para isolamento de zonas críticas da HAZ térmica.
3. **Falta dos Artefatos de Conteinerização Docker:**
   - Não havia `Dockerfile` nem `docker-compose.yml`, violando o critério de avaliação de Engenharia de Software & Docker (peso de 20%).
4. **Falta do Parecer Técnico Formal:**
   - Não havia documento estruturado analisando LGPD em chão de fábrica (privacidade em câmeras), enquadramento no EU AI Act, cibersegurança OT/IT e ganhos ESG (peso de 15%).
5. **Estrutura de Navegação do Streamlit Reduzida:**
   - A interface Streamlit possuía 3 páginas, enquanto o Prompt Master estabelece 9 páginas funcionais para cobrir todo o ciclo operacional e analítico da fábrica.

---

## 5. PLANO DE CORREÇÃO, DESENVOLVIMENTO E INTEGRAÇÃO

O desenvolvimento seguirá rigorosamente a metodologia ordenada de dependências:

1. **Fase 1: Engenharia de Dados Industriais e Feature Engineering (`src/data/`)**:
   - Criar `src/data/feature_engineering.py` com cálculo do IEM, janelas móveis temporais (30 min = 6 passos, 2h = 24 passos), Z-Score condicional por liga e normalização relativa por liga metálica.
   - Criar `src/data/pipeline.py` consolidando a ingestão, tratamento e persistência do dataset enriquecido em `data/processed/dados_sensores_vulcantech_features.parquet`.
2. **Fase 2: Machine Learning Multiclasse, XGBoost, Anomalias e Explicabilidade (`src/ml/`)**:
   - Criar `src/ml/anomaly_detection.py` com `IsolationForest` para detecção de anomalias operacionais.
   - Atualizar `src/ml/train.py` para treinar e comparar Random Forest e XGBoost com SMOTE e class weighting sobre as novas features, buscando a meta de Recall >= 90%.
   - Atualizar `src/ml/evaluate.py` para gerar matriz de confusão, métricas detalhadas e importâncias de variáveis/SHAP.
3. **Fase 3: Visão Computacional Analítica OpenCV (`src/vision/`)**:
   - Implementar `src/vision/weld_inspection.py` (filtros de nitidez, conversão escala de cinza, Canny, análise de contornos, estimativa de porosidade e descontinuidades geométricas).
   - Implementar `src/vision/thermal_analysis.py` (conversão HSV, limiarização por canais H/S/V, segmentação de sobreaquecimento na solda, cálculo de percentual de área afetada HAZ).
   - Manter compatibilidade com a inferência já integrada e conectar as novas saídas analíticas à API e ao frontend.
4. **Fase 4: Módulo de Cálculo Preditivo de OEE e Malha Fechada com CLP (`src/oee/` e `src/simulation/`)**:
   - Implementar `src/oee/predictive_impact.py` calculando o impacto das previsões no OEE (penalização de Disponibilidade em risco iminente de parada e Qualidade em desvio de vazão/pressão).
   - Implementar em `src/simulation/plc_controller.py` a camada de atuação simulada do CLP (alerta preventivo, solicitação de inspeção, recomendação de manutenção, parada preventiva).
5. **Fase 5: Expansão do Backend FastAPI (`backend/`)**:
   - Adicionar rotas literais solicitadas: `/api/v1/industrial/*`, `/api/v1/anomaly/detection`, `/api/v1/vision/inspect`, `/api/v1/models/metrics`, mantendo retrocompatibilidade total com as rotas já existentes.
6. **Fase 6: Expansão do Frontend Streamlit para as 9 Páginas do Prompt Master (`frontend/`)**:
   - Página 1: Dashboard Geral (Visão executiva da fábrica, 4 células, OEE consolidado, produção e alertas)
   - Página 2: Monitoramento em Tempo Real (Telemetria ao vivo, seleção de célula, streaming de sensores)
   - Página 3: Manutenção Preditiva (Diagnóstico de falha, probabilidades, score de anomalia, recomendações)
   - Página 4: OEE e Eficiência Industrial (OEE detalhado, impacto preditivo, perdas e Pareto)
   - Página 5: Visão Computacional (Inspeção geométrica Canny + Análise termográfica HAZ em HSV lado a lado)
   - Página 6: Análise de Dados (EDA interativa com Plotly: correlações, IEM, distribuições por liga)
   - Página 7: Modelos de IA (Métricas, matriz de confusão, comparação Random Forest vs XGBoost, Recall)
   - Página 8: Simulador Industrial (Controle de cenários de falha e malha fechada com CLP simulado)
   - Página 9: Parecer Técnico (Visualização interativa das análises de LGPD, EU AI Act, Cibersegurança e ESG)
7. **Fase 7: Conteinerização Docker e Deploy (`Dockerfile`, `docker-compose.yml`)**:
   - Criar `Dockerfile` multi-stage / otimizado para o ambiente industrial Edge.
   - Criar `docker-compose.yml` orquestrando FastAPI (`:8000`) e Streamlit (`:8501`) com volumes persistentes.
8. **Fase 8: Elaboração da Documentação Técnica Completa (`docs/`)**:
   - `docs/AUDITORIA_INICIAL.md` (este documento)
   - `docs/ACOMPANHAMENTO_REQUISITOS.md`
   - `docs/ARQUITETURA.md`
   - `docs/PIPELINE_DADOS.md`
   - `docs/MODELOS_ML.md`
   - `docs/VISAO_COMPUTACIONAL.md`
   - `docs/OEE.md`
   - `docs/API.md`
   - `docs/PARECER_TECNICO.md`
   - `docs/EXECUCAO.md`
   - `README.md`
9. **Fase 9: Suíte de Testes Automatizados e Validação Final**:
   - Expandir a suíte de testes unitários e de integração (`pytest`), cobrindo 100% dos novos componentes.
   - Executar validação de ponta a ponta com a aplicação em funcionamento.

