# Contratos da API (`/api/v1`) — VulcanTech Smart Metals S.A.

Todos os endpoints são servidos sob o prefixo `/api/v1` (documentação interativa Swagger UI disponível em `/docs` e ReDoc em `/redoc`).

## Padrão de Erro Global

Qualquer erro de validação, recurso ausente ou indisponibilidade de artefato retorna o envelope padronizado (`ErrorResponse`):

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Erro de validação nos dados enviados para a requisição.",
  "details": { "errors": [...] },
  "timestamp": "2026-10-29T15:30:00Z"
}
```

---

## 1. Saúde e Prontidão (`backend/routes/health.py`)

### `GET /api/v1/health`
Verifica se o processo FastAPI está ativo.
- **Status**: `200 OK`
- **Response (`HealthResponse`)**:
```json
{
  "status": "ok",
  "service": "VulcanTech Smart Metals API",
  "version": "1.0.0",
  "timestamp": "2026-10-29T15:30:00Z"
}
```

### `GET /api/v1/ready`
Verifica conectividade com o banco SQLite, existência do dataset histórico e carregamento dos artefatos de ML e Visão.
- **Status**: `200 OK`
- **Response (`ReadinessResponse`)**:
```json
{
  "ready": true,
  "database_ok": true,
  "tabular_model_ok": true,
  "vision_visual_model_ok": true,
  "vision_thermal_model_ok": true,
  "historical_dataset_ok": true,
  "details": {
    "database_path": ".../database/vulcantech.db",
    "sensor_readings_count": 12,
    "production_events_count": 8
  },
  "timestamp": "2026-10-29T15:30:00Z"
}
```

---

## 2. OEE e Produção (`backend/routes/oee.py`)

### `POST /api/v1/oee/events`
Registra um evento/turno de produção e retorna o OEE individual e acumulado para a origem.
- **Status**: `201 Created`
- **Request (`ProductionEventCreate`)**:
```json
{
  "cell_id": "CELULA_01",
  "planned_time_min": 480.0,
  "downtime_min": 30.0,
  "ideal_cycle_time_sec": 30.0,
  "total_units": 850,
  "rejected_units": 15,
  "stop_reason": "Troca de inserto",
  "data_source": "api"
}
```
- **Regras de Validação (`422 Unprocessable Content`)**:
  - `planned_time_min > 0`
  - `0 <= downtime_min <= planned_time_min`
  - `ideal_cycle_time_sec > 0`
  - `0 <= rejected_units <= total_units`

### `GET /api/v1/oee/summary`
Retorna o resumo ponderado de OEE, série histórica de eventos e Pareto de motivos de parada.
- **Query Params**: `data_source` (`all`, `simulated`, `api`, `historical`), `cell_id` (opcional), `limit` (1 a 500, padrão 50).
- **Status**: `200 OK`
- **Comportamento para `data_source=historical`**: Retorna `available=false` com explicação de que o dataset histórico contém apenas leituras de sensores.

---

## 3. Manutenção Preditiva / Condição de Ativos (`backend/routes/maintenance.py`)

### `POST /api/v1/maintenance/readings`
Valida, higieniza, persiste uma leitura de sensores e executa inferência contemporânea de falha com `models/tabular/best_model.joblib`.
- **Status**: `201 Created`
- **Request (`SensorReadingCreate`)**:
```json
{
  "id_celula": "CELULA_01",
  "liga_metalica": "Aco_Inox_316L",
  "temperatura_fuso_c": 92.4,
  "vibracao_triaxial_rms_mms": 4.8,
  "torque_fuso_nm": 195.0,
  "vazao_refrigerante_lmin": 14.5,
  "corrente_estator_amp": 29.0,
  "pressao_hidraulica_bar": 140.0,
  "nivel_ruido_db": 81.0,
  "data_source": "api"
}
```
- **Response (`MaintenancePredictionResponse`)**:
  - Inclui `predicted_class` (`0` a `3`), `predicted_label`, `failure_probability`, `class_probabilities`, `risk_level` (`BAIXO`, `MODERADO`, `ALTO`, `CRITICO`), `cleaning_applied`, `sentinel_detected`, `cleaned_features` e `scope_notice`.

### `GET /api/v1/maintenance/summary`
Retorna estatísticas da frota, distribuição de classes previstas, alertas ativos, leituras recentes e importância das variáveis do modelo.
- **Query Params**: `data_source` (`all`, `simulated`, `api`, `historical`), `limit` (1 a 200, padrão 30).

### `GET /api/v1/maintenance/model-info`
Retorna metadados de treinamento, métricas de validação e coeficientes de importância de variáveis extraídos de `models/tabular/metrics.json` e `best_model.joblib`.

---

## 4. Visão Computacional (`backend/routes/vision.py`)

### `POST /api/v1/vision/predict`
Recebe upload `multipart/form-data` de imagem (`file`), valida MIME (`image/png`, `image/jpeg`, `image/webp`) e tamanho máximo (10 MB), executa inferência no modelo correspondente (`modality`: `visual` ou `termica`) e persiste o resultado no SQLite.
- **Status**: `200 OK` (ou `413 Content Too Large`, `415 Unsupported Media Type`, `422 Unprocessable Content`).
- **Response (`VisionPredictionResponse`)**:
  - Inclui `predicted_class` (`NORMAL` ou `ANOMALIA`), `confidence`, `probabilities`, `experimental: true`, `validated_for_industrial_use: false` e `experimental_warning`.

### `GET /api/v1/vision/history`
Lista as inspeções de visão computacional persistidas no SQLite, filtráveis por `data_source` e `modality`.

---

## 5. Simulação Controlada (`backend/routes/simulation.py`)

### `POST /api/v1/simulation/step`
Gera `count` ciclos sintéticos (leituras de sensores + eventos de produção), executa a inferência tabular em cada leitura e persiste tudo com `data_source="simulated"`.
- **Request (`SimulationStepRequest`)**: `{"mode": "NORMAL" | "DEGRADACAO" | "FALHA" | "MISTO", "count": 1..50, "cell_id": null}`

### `POST /api/v1/simulation/reset`
Remove do SQLite **exclusivamente** os registros com `data_source='simulated'`, preservando dados enviados via `api`.

### `GET /api/v1/simulation/status`
Retorna a contagem de registros no SQLite agrupados por tabela (`sensor_readings`, `failure_predictions`, `production_events`, `vision_predictions`) e por `data_source`.

