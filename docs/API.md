# Catálogo da API RESTful VulcanTech

A API foi desenvolvida em **FastAPI**, oferecendo documentação interativa OpenAPI/Swagger em `/docs` e ReDoc em `/redoc`.

Base URL: `http://localhost:8000` (ou prefixo `/api/v1`).

---

## 1. Rotas de Diagnóstico e Saúde

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Verificação imediata de vivacidade do processo HTTP |
| `GET` | `/api/v1/health` | Verificação de vivacidade da API v1 |
| `GET` | `/api/v1/ready` | Verificação de prontidão de banco SQLite, dataset e modelos de ML |
| `GET` | `/api/v1/system/status` | Resumo consolidado de telemetria e estado de serviços |

---

## 2. Monitoramento Industrial & SCADA

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/v1/industrial/status` | Visão SCADA em tempo real das 4 células (`CEL-201` a `CEL-204`), níveis de segurança e OEE global |
| `GET` | `/api/v1/industrial/metrics` | Indicadores de produção, MTBF/MTTR e perdas operacionais |
| `GET` | `/api/v1/sensors/latest` | Última leitura de sensores registrada por equipamento |
| `GET` | `/api/v1/sensors/history` | Série histórica de leituras de sensores |
| `POST` | `/api/v1/sensors/readings` | Ingestão de nova leitura de telemetria |

---

## 3. Inteligência Artificial & Manutenção Preditiva

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/v1/prediction` | Inferência contemporânea de falhas com recomendação determinística de CLP |
| `POST` | `/api/v1/maintenance/predict` | Classificação de falha com probabilidades por classe |
| `POST` | `/api/v1/maintenance/predict-batch` | Inferência em lote para múltiplos registros |
| `POST` | `/api/v1/anomaly/detection` | Detecção não supervisionada via Isolation Forest (escore 0 a 1) |
| `GET` | `/api/v1/models/metrics` | Métricas comparativas de teste e validação de todos os algoritmos treinados |
| `GET` | `/api/v1/maintenance/metadata` | Metadados do modelo ativo, features esperadas e limitações |

---

## 4. Visão Computacional

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/v1/vision/inspect` | Inspeção geométrica via OpenCV (Canny, contornos, largura, porosidade e imagem anotada) |
| `POST` | `/api/v1/vision/thermal` | Análise termográfica via espaço de cor HSV (Hotspots, área da ZAC/HAZ e imagem anotada) |
| `POST` | `/api/v1/vision/predict` | Classificação supervisionada de imagem de solda via descritores HOG/KNN |
| `GET` | `/api/v1/vision/history` | Histórico de laudos de inspeção persistidos no SQLite |
| `GET` | `/api/v1/vision/summary` | Estatísticas acumuladas de peças aprovadas e reprovadas |

---

## 5. Eficiência Operacional (OEE)

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/v1/oee/current` | Indicadores consolidados de OEE atual |
| `GET` | `/api/v1/oee/summary` | Resumo analítico com filtros de turno, célula e período |
| `GET` | `/api/v1/oee/history` | Série temporal de lotes de OEE |
| `POST` | `/api/v1/oee/calculate` | Cálculo avulso de OEE informando tempos e contagens físicas |
| `POST` | `/api/v1/oee/impact` | Simulação de degradação preditiva no OEE e cálculo de perdas financeiras |
| `POST` | `/api/v1/oee/events` | Registro de novo lote de produção/parada |

---

## 6. Simulação e CLP em Malha Fechada

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/v1/simulation/status` | Estado da simulação contínua (ativa/parada, modo, ciclos) |
| `POST` | `/api/v1/simulation/start` | Inicia o simulador em segundo plano |
| `POST` | `/api/v1/simulation/stop` | Interrompe o simulador em segundo plano |
| `POST` | `/api/v1/simulation/mode` | Altera o modo da simulação (`NORMAL`, `DESGASTE`, `REFRIGERACAO`, `TRINCA`, `MISTO`) |
| `POST` | `/api/v1/simulation/step` | Executa N ciclos de simulação sob demanda |
| `GET` | `/api/v1/simulation/plc/history` | Histórico dos comandos de segurança emitidos pelo CLP simulado |
| `POST` | `/api/v1/simulation/plc/evaluate` | Avalia uma leitura de sensores e retorna a ação determinística do CLP |

