# AUDITORIA GERAL DE ENGENHARIA — VULCANTECH SMART METALS S.A.

**Projeto:** VulcanTech-OEE (Manufatura Inteligente, Manutenção Preditiva, Visão Computacional e Fechamento de Malha CLP)  
**Especificação Oficial:** `docs/Projeto Integrador Avançado certoo.pdf`  
**Repositório de Referência Arquitetural:** `AeroMotion Dynamics` (`https://github.com/adrielsoares2309/Projeto_Aero.git`, commit `924fbe711a356e6bf89177bdbeb68ed8452241fd`)

---

## 1. Inspeção de 11 Dimensões da Arquitetura do Repositório

1. **Estrutura de Diretórios:** Organizada em `src/` (`data`, `ml`, `vision`, `oee`, `simulation`), `vision/` (pacote unificado de inspeção óptica e termográfica), `backend/` e `api/` (camada REST FastAPI e persistência histórica JSONL/SQLite), `frontend/` (aplicação Streamlit com 9 páginas industriais e sidebar unificada), `infra/` (scripts PowerShell de orquestração com controle por PID), `models/`, `data/`, `notebooks/` e `tests/`.
2. **Scripts Python Existentes:** Módulos de engenharia de dados (`src/data/cleaner.py`, `src/data/feature_engineering.py`, `src/data/pipeline.py`), aprendizado de máquina (`src/ml/train.py`, `src/ml/predict.py`, `src/ml/anomaly_detection.py`), visão computacional (`src/vision/weld_inspection.py`, `src/vision/thermal_analysis.py`, `vision/geometry.py`, `vision/thermal.py`, `vision/pipeline.py`), OEE (`src/oee/calculator.py`, `src/oee/monte_carlo.py`, `src/oee/predictive_impact.py`) e simulação de CLP (`src/simulation/plc_controller.py`, `simulator.py`).
3. **Notebooks Existentes:** `notebooks/01_eda_sensores_metalurgicos.ipynb` (Análise Exploratória e Diagnóstico Estatístico).
4. **Arquivos de Dados:**
   - `data/raw/telemetria_planta.csv` e `data/raw/sensores_metalurgicos.parquet` (12.000 observações de sensores nas células `CEL-201` a `CEL-204`).
   - `data/raw/ordens_producao_erp.csv` (1.200 ordens de produção com ligas `Aco_Inox_316L`, `Liga_Aluminio_7075`, `Liga_Titanio_Ti6Al4V` e `Aco_Carbono_1045`).
   - `data/raw/historico_manutencao_cmms.csv` (histórico de intervenções corretivas/preventivas e MTTR).
   - `data/raw/imagens/` (40 imagens reais de cordões de solda MIG/MAG `solda_001.png` a `solda_040.png` + 40 termogramas infravermelhos `termograma_001.png` a `termograma_040.png` + `manifesto_imagens.csv`).
   - `data/processed/analytical_base_table.parquet` (ABT processada com 12.000 linhas e 40 colunas).
5. **Modelos de Machine Learning:** Artefatos serializados em `models/` (`champion_model.joblib`, `xgboost.joblib`, `random_forest.joblib`, `extra_trees.joblib`, `gradient_boosting.joblib`, `logistic_regression.joblib`, `mlp_neural_net.joblib`, `isolation_forest.joblib`, `feature_Reference.joblib`, `evaluation_metrics.json`).
6. **Módulos de Visão Computacional:** Inspeção geométrica de cordões de solda (limiarização adaptativa, morfologia matemática, circularidade $4\pi A / P^2$, desvio de espessura) e termografia infravermelha (conversão pseudocor/escala de cinza para °C, detecção de hotspots $> 205^\circ\text{C}$, gradiente térmico $\Delta T > 45^\circ\text{C}$ e índice de risco térmico).
7. **Banco de Dados e Persistência:** SQLite via SQLAlchemy (`backend/database.py`, `backend/models.py` em `data/vulcantech.db`) aliado a log estruturado JSONL (`prediction_history.jsonl` em `api/history.py`) e estado compartilhado (`simulator_state.json`, `simulator_control.json`).
8. **API FastAPI:** Servidor principal em `backend/main.py` (com wrapper de compatibilidade em `api/main.py`), expondo `/health`, `/api/v1/predict`, `/api/v1/history`, `/api/v1/history/summary`, `/api/v1/oee/{cell_id}`, `/api/v1/vision/weld`, `/api/v1/vision/thermal`, `/api/v1/plc/command`, `/api/v1/plc/commands` e `/api/v1/telemetry/stream`.
9. **Interface Streamlit:** 9 páginas industriais em `frontend/` com tema industrial claro de alto contraste inspirado no AeroMotion Dynamics (`.streamlit/config.toml` + `frontend/styles.py` + `frontend/components/sidebar.py`).
10. **Testes Automatizados:** Suíte completa com `pytest` em `tests/` cobrindo engenharia de dados, ML supervisionado e não supervisionado, visão computacional em lote, OEE e Monte Carlo, controlador CLP, simulador com inércia física, API FastAPI e testes de UI/Sidebar via `AppTest`.
11. **Documentação:** `README.md`, `docs/PARECER_TECNICO.md`, `docs/ACOMPANHAMENTO_REQUISITOS.md`, `docs/ANALISE_REAPROVEITAMENTO_AEROMOTION.md`, `docs/AUDITORIA_GERAL.md` e `docs/MATRIZ_CONFORMIDADE_FINAL.md`.

---

## 2. Matriz de Auditoria: Requisito do PDF vs. Implementação

| Requisito do PDF | Implementação encontrada | Situação | Ação necessária |
| :--- | :--- | :--- | :--- |
| **1. Tratamento de Dados e Limpeza Contextual** (Interpolação temporal por célula, remoção de duplicatas, tratamento de outliers impossíveis vs. pré-falha) | `src/data/cleaner.py` (`remove_duplicate_timestamps`, `treat_physical_anomalies`, `interpolate_missing_by_cell`) | **Completo** | Validado por `tests/test_data_engineering.py` |
| **2. Engenharia de Atributos e Normalização por Liga** ($\text{IEM} = \frac{\text{Torque} \times \text{Vibração}}{\text{Vazão} + 1}$, janelas móveis 30m e 2h, Z-score condicional à liga) | `src/data/feature_engineering.py` (`compute_mechanical_stress_index`, `compute_rolling_windows`, `normalize_conditional_by_alloy`) | **Completo** | Validado em `data/processed/analytical_base_table.parquet` |
| **3. Análise Exploratória de Dados (EDA)** (Correlação de Pearson/Spearman, análise de ruído, separabilidade de classes e diagnóstico de degradadores) | `notebooks/01_eda_sensores_metalurgicos.ipynb` e `frontend/pages/eda.py` | **Completo** | Integrado ao notebook e à página interativa de EDA no Streamlit |
| **4. Classificação Multiclasse de Falhas** (Classes 0, 1, 2, 3; desbalanceamento SMOTE/class_weight; validação estratificada; Recall $\ge 90\%$ em falhas críticas) | `src/ml/train.py`, `src/ml/predict.py`, `api/predictor.py` (6 modelos avaliados; Recall de falhas críticas = 99,36%, F1-Macro = 97,94%) | **Completo** | Artefatos salvos em `models/` e testados em `tests/test_ml_pipeline.py` |
| **5. Detecção Não Supervisionada de Anomalias** (`IsolationForest` treinado em operação normal + score contínuo de anomalia e limiar de alerta) | `src/ml/anomaly_detection.py` (`IndustrialAnomalyDetector`) e `models/isolation_forest.joblib` | **Completo** | Integrado ao endpoint `/api/v1/predict` e página de Manutenção Preditiva |
| **6. Cálculo Determinístico e Estocástico de OEE** ($\text{Disponibilidade} \times \text{Performance} \times \text{Qualidade}$, metas World Class 85%, Monte Carlo e ganho preditivo) | `src/oee/calculator.py`, `src/oee/monte_carlo.py`, `src/oee/predictive_impact.py` | **Completo** | Validado em `tests/test_oee_and_plc.py` |
| **7. Visão Computacional — Inspeção de Solda MIG/MAG** (Porosidades circulares, descontinuidades e desvio de espessura com bounding boxes) | `src/vision/weld_inspection.py` e `vision/geometry.py` (`inspect_weld_image`, `analyze_weld_geometry`) | **Completo** | Processamento individual e em lote (`vision/pipeline.py`) sobre `data/raw/imagens/` |
| **8. Visão Computacional — Termografia Infravermelha** (Hotspots térmicos, assimetria térmica e correlação com desgaste de rolamento) | `src/vision/thermal_analysis.py` e `vision/thermal.py` (`analyze_thermogram`, `analyze_thermal_distribution`) | **Completo** | Validado em `tests/test_vision_pipeline.py` |
| **9. Fechamento de Malha e Simulação de CLP** (Regras automáticas para `REDUZIR_AVANCO_CNC`, `RECALIBRAR_ CORRENTE_SOLDA`, `PARADA_SEGURANCA_IMEDIATA`) | `src/simulation/plc_controller.py` e `simulator.py` (com `SimulatorLock`, inércia física e ruído AR(1)) | **Completo** | Validado em `tests/test_simulator_advanced.py` e `tests/test_oee_and_plc.py` |
| **10. Backend FastAPI e Persistência** (Endpoints de inferência, visão, OEE, histórico JSONL/SQLite e comandos CLP) | `backend/main.py`, `api/main.py`, `api/history.py`, `api/schemas.py` | **Completo** | Validado em `tests/test_api_and_vision.py` e `tests/test_api_history.py` |
| **11. Interface Executiva e Operacional Streamlit com Sidebar Funcional** (9 páginas industriais, sidebar branca `#FFFFFF` com texto azul-marinho `#102A43`, navegação nativa `st.radio`, filtros globais e controle do simulador) | `.streamlit/config.toml`, `frontend/styles.py`, `frontend/components/sidebar.py`, `frontend/app.py` e `frontend/pages/*.py` | **Corrigido e Validado** | Corrigido bug de `st.navigation` que ignorava retorno da sidebar; validado via `AppTest` em `tests/test_sidebar_and_ui.py` |

