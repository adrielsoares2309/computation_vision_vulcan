# Orquestração de Serviços de Infraestrutura VulcanTech

Scripts PowerShell padronizados para inicialização e controle individual ou integrado dos serviços:

| Script | Finalidade | Portas / Logs |
|---|---|---|
| `start_api.ps1` | Inicia o backend FastAPI com Uvicorn em background | Porta 8000 / `api.log` / `api.pid` |
| `start_simulator.ps1` | Inicia o motor autônomo de telemetria multicélula com inércia física | `simulator.log` / `simulator.pid` |
| `start_streamlit.ps1` | Inicia o dashboard MES/SCADA Streamlit em background | Porta 8501 / `streamlit.log` / `streamlit.pid` |
| `start_stack.ps1` | Inicializa a stack completa (API + Simulador + Streamlit) | Orquestração sequencial |
| `stop_services.ps1` | Encerra todos os processos salvos nos arquivos `.pid` e libera locks | Limpeza graciosa |

Também é possível utilizar o script unificado na raiz:
```powershell
.\iniciar_aplicacao.ps1
```

