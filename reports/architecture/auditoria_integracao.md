# Auditoria de Arquitetura, Integração e Interface Industrial — VulcanTech Smart Metals S.A.

## 1. Estrutura Auditada do Repositório

A inspeção completa do repositório confirmou os seguintes módulos e artefatos:

```text
VulcanTech Smart Metals S.A/
├── backend/
│   ├── config.py
│   ├── dependencies.py
│   ├── main.py
│   ├── routes/
│   │   ├── health.py
│   │   ├── oee.py
│   │   ├── predictive_maintenance.py
│   │   ├── sensors.py
│   │   ├── simulation.py
│   │   └── vision.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── health.py
│   │   ├── oee.py
│   │   ├── predictive_maintenance.py
│   │   ├── sensors.py
│   │   ├── simulation.py
│   │   └── vision.py
│   └── services/
│       ├── ml_service.py
│       ├── oee_service.py
│       ├── sensor_service.py
│       ├── simulation_service.py
│       └── vision_service.py
├── database/
│   ├── db.py
│   ├── repositories.py
│   ├── schema.sql
│   └── vulcantech.db
├── data/
│   ├── processed/
│   │   ├── dados_sensores_vulcantech_tratados.csv
│   │   ├── dados_sensores_vulcantech_tratados.parquet
│   │   └── vision/labels.csv
│   └── raw/
│       ├── dados_sensores_vulcantech.csv
│       └── imagens/
│           ├── solda_aprovada.png
│           ├── solda_reprovada.png
│           ├── termica_solda_aprovada.png
│           └── termica_solda_reprovada.png
├── frontend/
│   ├── app.py
│   ├── styles.py
│   ├── components/
│   │   ├── charts.py
│   │   ├── header.py
│   │   ├── icons.py
│   │   ├── kpi_card.py
│   │   └── sidebar.py
│   ├── pages/
│   │   ├── oee.py
│   │   ├── predictive_maintenance.py
│   │   └── vision.py
│   └── services/
│       ├── api_client.py
│       ├── ml_service.py
│       ├── oee_service.py
│       └── vision_service.py
├── models/
│   ├── tabular/
│   │   ├── best_model.joblib
│   │   ├── extra_trees.joblib
│   │   ├── gradient_boosting.joblib
│   │   ├── logistic_regression.joblib
│   │   ├── model_metadata.json
│   │   └── random_forest.joblib
│   └── vision/
│       ├── class_mapping.json
│       ├── model_metadata.json
│       ├── termica_model.joblib
│       └── visual_model.joblib
├── src/
│   ├── data/
│   │   ├── cleaner.py
│   │   ├── loader.py
│   │   ├── pipeline.py
│   │   └── validator.py
│   ├── ml/
│   │   ├── evaluate.py
│   │   ├── predict.py
│   │   └── train.py
│   ├── oee/
│   │   ├── availability.py
│   │   ├── calculator.py
│   │   ├── performance.py
│   │   └── quality.py
│   ├── simulation/
│   │   ├── event_generator.py
│   │   ├── fault_generator.py
│   │   └── sensor_simulator.py
│   └── vision/
│       ├── dataset.py
│       ├── evaluate.py
│       ├── predict.py
│       ├── preprocessing.py
│       └── train.py
├── tests/
│   ├── test_api.py
│   ├── test_frontend_client.py
│   ├── test_ml.py
│   ├── test_oee.py
│   └── test_vision.py
├── iniciar_aplicacao.ps1
├── requirements.txt
└── README.md
```

---

## 2. Diagnóstico dos Módulos Existentes

### 2.1. Domínio, Dados e Modelos (`src/` e `models/`)
- **Engenharia de Dados (`src/data/`)**: Valida as 9 variáveis obrigatórias do dataset (`id_celula`, `liga_metalica`, `temperatura_fuso_c`, `vibracao_triaxial_rms_mms`, `torque_fuso_nm`, `vazao_refrigerante_lmin`, `corrente_estator_amp`, `pressao_hidraulica_bar`, `nivel_ruido_db`) e trata os códigos sentinela documentados (`999.9` em temperatura, `-99.0` em vibração, `-1.0` em pressão).
- **Machine Learning Tabular (`src/ml/` e `models/tabular/best_model.joblib`)**: Modelo `LogisticRegression` multiclasse (`0: Normal`, `1: Desgaste de ferramenta`, `2: Falha de refrigeração`, `3: Desalinhamento / trinca`). Realiza classificação **contemporânea** da condição operacional associada à leitura atual (não prevê tempo restante de vida útil / RUL).
- **Visão Computacional (`src/vision/` e `models/vision/{visual,termica}_model.joblib`)**: Descritores `hog_rgb_hist_v1` + `KNeighborsClassifier(n_neighbors=1)` treinados sobre 4 imagens semente (`data/raw/imagens/`). Marcados como `experimental: true` e `validated_for_industrial_use: false`.
- **OEE (`src/oee/`)**: Calcula Disponibilidade, Performance, Qualidade e OEE por somas físicas ponderadas. Como o dataset histórico (`dados_sensores_vulcantech_tratados.parquet`) contém apenas leituras de sensores e não possui registros de produção/paradas, a fonte `historical` retorna explicitamente `available=False` (`N/D`), enquanto as fontes `simulated`, `api` e `all` calculam os indicadores a partir dos lotes persistidos em `production_events` no SQLite.

### 2.2. Backend FastAPI (`backend/`) e Persistência (`database/`)
- A API FastAPI está estruturada sob `/api/v1` com routers para `/health`, `/ready`, `/system/status`, `/oee/*`, `/vision/*`, `/maintenance/*`, `/sensors/*` e `/simulation/*`.
- O banco SQLite (`database/vulcantech.db`) separa a origem de todos os registros via coluna `data_source` (`historical`, `simulated`, `api`).
- **Oportunidades de evolução identificadas no Backend/Serviços**:
  1. Na página **OEE**, é importante expor e visualizar também a **Produção por período** (unidades boas vs. refugadas por lote/período), além da evolução temporal do OEE, comparação entre Disponibilidade/Performance/Qualidade, histórico de paradas e tabela de eventos operacionais.
  2. Na página **Visão Computacional**, suportar explicitamente os três estados visuais solicitados (`APROVADA`, `REPROVADA` e `INDETERMINADA` — por exemplo, quando não há inspeção ativa ou quando a diferença entre escores das classes é inconclusiva/empate técnico), com ícones e rótulos além da cor.
  3. Na página **Manutenção Preditiva**, integrar os endpoints já disponíveis no backend que ainda não estavam conectados na tela:
     - `GET /api/v1/maintenance/equipment` (estado consolidado dos equipamentos monitorados `CEL-201` a `CEL-204`, com filtro por `data_source`).
     - `GET /api/v1/sensors/latest` (últimas leituras reais/simuladas/históricas dos sensores por equipamento).
     - Filtro de origem dos dados (`historical`, `simulated`, `api`, `all`) integrado ao cabeçalho de filtros da manutenção preditiva para diferenciar claramente dados históricos, simulados e operacionais (`api`).

---

## 3. Problemas Identificados na Interface Atual (`frontend/`) e Auditoria WCAG 2.2

A inspeção detalhada de `frontend/styles.py`, `frontend/components/` e `frontend/pages/` revelou problemas visuais e de acessibilidade (WCAG 2.2) que impedem a interface de parecer um software industrial comercial (padrão TOTVS / MES / SCADA):

1. **Falha crítica de contraste em botão primário no estado `:hover` (`frontend/styles.py` linha 29)**:
   - A regra `div[data-testid="stButton"]>button:hover{border-color:var(--vt-blue);color:var(--vt-blue)}` aplica texto azul (`#155EEF`) sobre fundo azul (`#155EEF`) quando o usuário passa o mouse sobre um botão `type="primary"`, resultando em **contraste 1,00:1** (texto invisível).
2. **Falhas de contraste WCAG 2.2 AA (< 4,5:1 para texto normal)**:
   - `--vt-subtle: #94A3B8` sobre o fundo da sidebar (`#F8FAFC`) possui contraste de apenas **2,44:1** (usado no título do menu `MÓDULOS`).
   - `--vt-muted: #64748B` sobre superfícies cinza-claras (`#F5F7FA` / `#F8FAFC`) possui contraste de **4,37:1** (abaixo do mínimo de 4,5:1 da WCAG 2.2 AA).
   - `--vt-yellow: #B7791F` sobre fundo branco (`#FFFFFF`) possui contraste de **3,62:1** (abaixo de 4,5:1 para texto normal).
3. **Baixa densidade operacional e excesso de textos explicativos**:
   - Na página **OEE**, os 6 KPIs estão divididos em 2 linhas de 3 cards grandes (`126px` de altura) em vez de uma faixa horizontal compacta de 6 indicadores objetivos em linha única (`st.columns(6)`). Além disso, há textos longos de "Ação recomendada" e todos os gráficos são empilhados verticalmente sem organização por abas operacionais.
   - Na página **Visão Computacional**, um alerta amarelo extenso (`st.warning`) e um `st.expander` de limitações ocupam o topo da tela antes mesmo de o usuário realizar qualquer inspeção, contrariando a diretriz de não apresentar informações técnicas extensas antes da inspeção.
   - Na página **Manutenção Preditiva**, há uma caixa `st.info` permanente com parágrafo explicativo longo no meio da área de trabalho, além de faltar a visão direta do **Estado dos Equipamentos Monitorados** e das **Últimas Leituras dos Sensores**.
   - Ausência de uma camada centralizada de **Design Tokens** estruturada (`DESIGN_TOKENS`) com verificação programática de contraste WCAG 2.2.

---

## 4. Plano de Implementação e Refinamento

1. **Design System Industrial (Estilo TOTVS / MES / SCADA) e Tokens WCAG 2.2 (`frontend/styles.py`)**:
   - Criar dicionário centralizado `DESIGN_TOKENS` com paleta corporativa de alto contraste (todos os pares texto/fundo validados matematicamente com razão $\ge 4,5:1$ para texto normal e $\ge 3,0:1$ para elementos gráficos/bordas de foco).
   - Corrigir estados `:hover`, `:focus-visible`, `:active` e `:disabled` dos botões primários e secundários.
   - Reduzir paddings excessivos, compactar cabeçalhos, KPIs, filtros e tabelas, e padronizar badges semânticos com ícone + rótulo textual (`APROVADA`, `REPROVADA`, `INDETERMINADA`, `NORMAL`, `ALERTA`, `CRÍTICO`, `N/D`).
2. **Componentes Reutilizáveis (`frontend/components/`)**:
   - Atualizar `sidebar.py` com identidade industrial compacta, `streamlit-option-menu` com contrastes validados ($\ge 4,5:1$), telemetria de status concisa e controle de simulação rápida.
   - Atualizar `header.py` para cabeçalho operacional discreto em linha única com breadcrumb/módulo, badge de contexto e botão compacto de atualização.
   - Atualizar `kpi_card.py` para suportar linha única de 6 KPIs densos com borda lateral de status, ícone SVG e hierarquia tipográfica clara.
   - Atualizar `charts.py` com tema Plotly industrial de alto contraste, grades discretas e alturas balanceadas.
3. **Evolução das 3 Páginas Operacionais (`frontend/pages/`) e Serviços (`frontend/services/`)**:
   - **OEE (`oee.py`)**: Barra compacta de filtros + simulação integrada; 6 KPIs na mesma linha (`OEE`, `Disponibilidade`, `Performance`, `Qualidade`, `Produção Total`, `Tempo de Parada`); abas operacionais para (1) Evolução Temporal e Produção por Período, (2) Disponibilidade × Performance × Qualidade por Equipamento, e (3) Histórico de Paradas e Eventos Operacionais.
   - **Visão Computacional (`vision.py`)**: Layout de bancada de inspeção industrial (seleção/upload de imagem ou amostra do repositório, seleção de modalidade óptica/térmica, botão `Executar inspeção`, visualização lado a lado com badge `APROVADA` / `REPROVADA` / `INDETERMINADA`, gráfico de escores, metadados concisos do modelo após a inspeção e tabela compacta de histórico).
   - **Manutenção Preditiva (`predictive_maintenance.py`)**: Barra de filtros (incluindo origem dos dados `historical`, `simulated`, `api`, `all`, equipamento, sensor e período); KPIs objetivos em linha única; painel de **Estado dos Equipamentos Monitorados** (`CEL-201` a `CEL-204`); abas operacionais para (1) Monitoramento de Sensores e Últimas Leituras, (2) Alertas Ativos e Histórico de Alertas, e (3) Diagnóstico de Leitura via API.
4. **Validação Automatizada e Auditoria Visual (`tests/` e `reports/architecture/validacao_integracao.md`)**:
   - Adicionar testes automatizados de contraste WCAG 2.2 e integração de endpoints, executar `pytest` completo, inspecionar a aplicação em execução e documentar a matriz real de contrastes verificados.
