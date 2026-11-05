# ANÁLISE COMPARATIVA E MATRIZ DE REAPROVEITAMENTO: AEROMOTION DYNAMICS → VULCANTECH-OEE

## 1. Identificação do Repositório de Referência

- **Repositório:** `https://github.com/adrielsoares2309/Projeto_Aero.git`
- **Branch:** `main`
- **Commit de Referência:** `924fbe711a356e6bf89177bdbeb68ed8452241fd`
- **Mensagem do Commit:** `Documentação e acabamento (Thu Oct 29 08:00:41 2026 -0300)`
- **Diretório Local de Inspeção:** `_referencia_aero/` (isolado, somente leitura)

---

## 2. Auditoria Comparativa de Arquitetura

| Dimensão | AeroMotion Dynamics (Referência) | VulcanTech-OEE (Projeto Industrial Alvo) | Decisão de Engenharia |
|---|---|---|---|
| **Domínio Físico** | Turbinas aeronáuticas / aerogeradores (`TURB-101` a `104`) | Células CNC de usinagem e soldagem de metais nobres (`CEL-201` a `204`) | Adaptar variáveis ao domínio de manufatura e conformação |
| **Variáveis dos Sensores** | Rotação, vibração, temp. mancal, pressão de óleo, acústica, corrente | Rotação, temp. fuso, vibração triaxial RMS, torque fuso, vazão refrigerante, corrente estator, pressão hidráulica, ruído | Substituir features aeroespaciais pelas grandezas térmicas/mecânicas de corte da VulcanTech |
| **Modos Operacionais** | `Cruzeiro`, `Carga_Media`, `Carga_Alta` | Ligas Metálicas (`Aco_Carbono_316L`, `Aluminio_7075`, `Liga_Titanio_Ti6Al4V`) + Regimes de Corte | Mapear regimes para Ligas e severidade de usinagem |
| **Classes de Falha** | 0: Normal, 1: Desgaste Rolamento, 2: Desbalanceamento Rotor, 3: Cavitação/Superaquecimento | 0: Normal, 1: Desgaste de Ferramenta, 2: Falha de Refrigeração, 3: Desalinhamento / Trinca | Manter multiclasse do VulcanTech com meta de Recall >= 90% |
| **Cálculo de OEE** | Não possui (foco estrito em telemetria e falhas) | Completo: Disponibilidade × Performance × Qualidade + Penalidades Financeiras | Desenvolver OEE com impacto preditivo e ROI preventivo conforme Requisitos |
| **Visão Computacional** | Pás e rotores (Canny/contornos) + Termografia de turbina (HSV) | Cordão de solda (Canny, largura de cordão, porosidade ISO 5817) + Termografia ZAC/HAZ (°C e isotermas) | Reaproveitar classes base (`GeometryConfig`, `ThermalConfig`, pipeline de processamento em lote) aplicando aos cordões de solda |
| **Simulador** | Motor contínuo com lock de arquivo (`SimulatorLock`), AR(1), controle de transição e heartbeat | Motor com CLP determinístico (Níveis 0 a 4) e injeção de falhas | Integrar arquitetura de processo do AeroMotion (`SimulatorLock`, controle JSON, heartbeat) ao CLP da VulcanTech |
| **Persistência SQLite** | `PredictionHistory` com migração automática e WAL mode | SQLAlchemy ORM + SQLite (`database/vulcantech.db`) | Harmonizar persistência em camada unificada de histórico de predições e eventos |
| **Frontend Streamlit** | Interface clara, cards, Lucide SVG, Plotly alto contraste | Cockpit MES com 9 módulos industriais, Dark Navy Sidebar, WCAG 2.2 | Aproveitar componentes visuais, ícones SVG e gráficos Plotly de alto contraste |
| **Infraestrutura** | Scripts modulares em `infra/` (`start_api.ps1`, `start_simulator.ps1`, etc.) | Script raiz `iniciar_aplicacao.ps1` + Dockerfile + docker-compose | Implementar pasta `infra/` modular compatível, preservando o inicializador principal |

---

## 3. Matriz Detalhada de Reaproveitamento

| Componente AeroMotion | Aplicação no VulcanTech | Ação | Arquivos Envolvidos | Funcionalidades Reaproveitadas / Adaptadas | Testes Associados |
|---|---|---|---|---|---|
| **Simulador Industrial (`simulator.py`)** | Simulador de Processos e CLP das Células | **Adaptar e Integrar** | `simulator.py`, `src/simulation/` | `SimulatorLock` (msvcrt/fcntl), controle atômico via JSON (`simulator_control.json`, `simulator_state.json`), inércia física, ruído AR(1), envio para API | `tests/test_simulator.py`, `tests/test_oee_predictive_plc.py` |
| **Infraestrutura (`infra/`)** | Scripts de orquestração de serviços | **Adaptar** | `infra/*.ps1`, `iniciar_aplicacao.ps1` | `start_api.ps1`, `start_simulator.ps1`, `start_streamlit.ps1`, `start_stack.ps1`, `stop_services.ps1`, controle por PID | `tests/test_imports.py` |
| **Persistência (`api/history.py`)** | Histórico SQLite de telemetria e predições | **Reaproveitar e Adaptar** | `api/history.py`, `database/db.py` | `PredictionHistory` com schema aditivo, migração sem perda de dados, indexação por célula e timestamp | `tests/test_api.py`, `tests/test_industrial_routes.py` |
| **Pipeline Visual (`vision/`)** | Inspeção geométrica e térmica de solda | **Reaproveitar e Adaptar** | `vision/geometry.py`, `vision/thermal.py`, `vision/pipeline.py`, `src/vision/` | `GeometryConfig`, `ThermalConfig`, descoberta em lote (`discover_images`), `process_batch`, geração de máscaras e artefatos em memória | `tests/test_vision.py`, `tests/test_vision_advanced.py` |
| **Componentes Visuais (`frontend/components.py`, `icons.py`)** | Elementos visuais e ícones do Streamlit | **Reaproveitar** | `frontend/components/`, `frontend/components/icons.py` | Catálogo completo de ícones Lucide em SVG vetorial (zero emojis), badges de status, cards de probabilidade | `tests/test_frontend_client.py` |
| **Gráficos Plotly (`frontend/charts.py`)** | Visualizações de telemetria e OEE | **Adaptar** | `frontend/charts.py`, `frontend/components/charts.py` | Template Plotly de alto contraste (`plot_bg="#FFFFFF"`, eixos nítidos `mirror=True`), anotações de transição de regime | `tests/test_frontend_client.py` |
| **Machine Learning (`api/predictor.py`)** | Serviço de inferência em tempo real | **Adaptar** | `api/predictor.py`, `src/ml/predict.py` | Buffer de rolling temporal por equipamento/célula, cálculo incremental de janelas estatísticas | `tests/test_ml.py` |
| **Testes Automatizados (`tests/`)** | Cobertura de testes unitários e de integração | **Adaptar e Expandir** | `tests/` | Padrões de teste sintético com mock de imagem, validação de transição do simulador e verificação de contratos | Suíte de testes pytest |

---

## 4. Regras de Preservação e Não Regressão

1. **Requisitos Oficiais da VulcanTech prevalecem:**
   - As fórmulas industriais (IEM: $(Torque \times Vibracao) / (Vazao + 1)$, Z-scores condicionais à liga metálica) continuam como base matemática primária.
   - Os 9 módulos de página do Streamlit continuam mantidos e operacionais.
   - O Recall de falhas industriais (classes 1, 2 e 3) permanece validado com taxa $\ge 90\%$.
2. **Imagens Reais da VulcanTech:**
   - As imagens oficiais de soldagem e termografia (`solda_aprovada.png`, `solda_reprovada.png`, `termica_solda_aprovada.png`, `termica_solda_reprovada.png`) permanecem as referências de teste e inspeção.
3. **Compatibilidade dos Inicializadores:**
   - O inicializador unificado `iniciar_aplicacao.ps1` continua funcional e ganha suporte aos scripts modulares em `infra/`.

