# Guia de Execução e Deploy — VulcanTech-OEE

Este guia descreve os procedimentos para execução local (Windows/PowerShell) e conteinerizada (Docker Compose).

---

## 1. Pré-Requisitos

- **Python:** 3.11 ou superior (virtualenv configurado em `venv/`)
- **Docker:** Docker Desktop ou Docker Engine com Docker Compose (opcional para deploy conteinerizado)
- **PowerShell:** PowerShell 5.1 ou PowerShell 7+

---

## 2. Execução Local Completa via PowerShell

O repositório inclui o script automatizado `iniciar_aplicacao.ps1`, que executa:
1. Validação do ambiente virtual Python (`venv\Scripts\python.exe`).
2. Inicialização e migração do banco SQLite (`database/vulcantech.db`).
3. Inicialização em background da API FastAPI (Uvicorn) na porta **8000**.
4. Teste de vivacidade e espera ativa de prontidão (`http://127.0.0.1:8000/api/v1/health`).
5. Inicialização da interface industrial Streamlit na porta **8501**.

### Comando de Execução:
```powershell
.\iniciar_aplicacao.ps1
```

### Parâmetros Opcionais:
```powershell
# Iniciar com lote inicial demonstrativo de simulação:
.\iniciar_aplicacao.ps1 -SeedSimulatedData

# Iniciar apenas a API em segundo plano (sem abrir Streamlit no terminal):
.\iniciar_aplicacao.ps1 -BackgroundOnly
```

---

## 3. Execução Conteinerizada via Docker Compose

Para subir toda a aplicação em contêineres Linux isolados:

### Construir e Iniciar os Serviços:
```bash
docker-compose up --build -d
```

### Acessos:
- **Backend FastAPI:** `http://localhost:8000`
- **Documentação Swagger:** `http://localhost:8000/docs`
- **Frontend Streamlit (Cockpit SCADA):** `http://localhost:8501`

### Verificar Logs dos Contêineres:
```bash
docker-compose logs -f
```

### Encerrar os Serviços:
```bash
docker-compose down
```

---

## 4. Execução Manual dos Componentes

Caso prefira rodar os componentes separadamente em terminais distintos:

### Terminal 1 — Pipeline de Dados & Treinamento dos Modelos:
```powershell
.\venv\Scripts\python.exe -m src.data.pipeline
.\venv\Scripts\python.exe -m src.ml.train
```

### Terminal 2 — Backend FastAPI:
```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 3 — Frontend Streamlit:
```powershell
.\venv\Scripts\python.exe -m streamlit run frontend/app.py --server.port 8501
```

---

## 5. Execução dos Testes Automatizados

O projeto conta com suíte completa de testes unitários e de integração (`pytest`):
```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v
```
Todos os 53 testes cobrem pipeline de dados, sanitização, features industriais, modelos de ML, visão computacional, OEE e rotas da API.

