<#
.SYNOPSIS
    Script de inicializacao completa do ecossistema VulcanTech Smart Metals S.A.
.DESCRIPTION
    Inicializa o banco de dados SQLite, inicia o backend FastAPI (Uvicorn) na porta 8000,
    aguarda a verificacao de saude (/api/v1/health) e inicia o dashboard Streamlit na porta 8501.
#>

param(
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [int]$StreamlitPort = 8501,
    [switch]$SeedSimulatedData,
    [switch]$BackgroundOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Error "Ambiente virtual nao encontrado em '$PythonExe'. Crie ou restaure a pasta venv antes de iniciar."
    exit 1
}

$env:API_HOST = $ApiHost
$env:API_PORT = "$ApiPort"
$env:API_BASE_URL = "http://${ApiHost}:${ApiPort}"
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///database/vulcantech.db"
}
$env:FRONTEND_ORIGINS = "http://localhost:${StreamlitPort},http://127.0.0.1:${StreamlitPort}"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VulcanTech Smart Metals S.A. - Inicializador do Sistema   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Raiz do projeto : $ProjectRoot"
Write-Host "API FastAPI     : $($env:API_BASE_URL) (Docs: $($env:API_BASE_URL)/docs)"
Write-Host "Streamlit UI    : http://localhost:${StreamlitPort}"
Write-Host "Banco de Dados  : $($env:DATABASE_URL)"
Write-Host "------------------------------------------------------------"

# 1. Inicializar schema do banco SQLite e verificar artefatos de dados e modelos
Write-Host "[1/4] Verificando banco de dados SQLite e artefatos de IA..." -ForegroundColor Yellow
& $PythonExe -c "from database.db import init_db; p = init_db(); print('  -> Banco SQLite pronto em:', p)"

$FeaturesParquet = Join-Path $ProjectRoot "data\processed\dados_sensores_vulcantech_features.parquet"
if (-not (Test-Path $FeaturesParquet)) {
    Write-Host "  -> Dataset de features nao encontrado. Executando pipeline de dados e engenharia de features..." -ForegroundColor Cyan
    & $PythonExe -m src.data.pipeline
} else {
    Write-Host "  -> Dataset de features operacionais validado." -ForegroundColor Green
}

$BestModel = Join-Path $ProjectRoot "models\tabular\best_model.joblib"
$AnomalyModel = Join-Path $ProjectRoot "models\tabular\anomaly_detector.joblib"
if ((-not (Test-Path $BestModel)) -or (-not (Test-Path $AnomalyModel))) {
    Write-Host "  -> Modelos de IA nao encontrados. Treinando classificadores (Random Forest, XGBoost, Isolation Forest)..." -ForegroundColor Cyan
    & $PythonExe -m src.ml.train
} else {
    Write-Host "  -> Modelos supervisionados e detector de anomalias validados." -ForegroundColor Green
}

# 2. Verificar se ja existe processo na porta da API e iniciar o backend FastAPI
Write-Host "[2/4] Iniciando servidor FastAPI (Uvicorn)..." -ForegroundColor Yellow
$ApiProcess = $null
$HealthUrl = "http://${ApiHost}:${ApiPort}/health"

$ApiAlreadyUp = $false
try {
    $resp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2
    if ($resp.status -eq "ok") {
        $ApiAlreadyUp = $true
        Write-Host "API FastAPI ja esta ativa em $($env:API_BASE_URL)." -ForegroundColor Green
    }
} catch {
    $ApiAlreadyUp = $false
}

if (-not $ApiAlreadyUp) {
    $ApiProcess = Start-Process -FilePath $PythonExe `
        -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", $ApiHost, "--port", "$ApiPort" `
        -WorkingDirectory $ProjectRoot `
        -PassThru `
        -WindowStyle Hidden

    $MaxRetries = 25
    $Ready = $false
    for ($i = 1; $i -le $MaxRetries; $i++) {
        Start-Sleep -Milliseconds 600
        try {
            $resp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2
            if ($resp.status -eq "ok") {
                $Ready = $true
                break
            }
        } catch {
            # aguarda inicializacao
        }
    }

    if (-not $Ready) {
        if ($ApiProcess -and -not $ApiProcess.HasExited) {
            Stop-Process -Id $ApiProcess.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Error "Nao foi possivel confirmar a inicializacao da API em $HealthUrl."
        exit 1
    }
    Write-Host "API FastAPI iniciada com sucesso (PID: $($ApiProcess.Id))." -ForegroundColor Green
}

if ($SeedSimulatedData) {
    Write-Host "[3/4] Gerando lote inicial demonstrativo identificado como 'simulated'..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod -Uri "http://${ApiHost}:${ApiPort}/api/v1/simulation/step" `
            -Method Post `
            -ContentType "application/json" `
            -Body '{"mode":"MISTO","count":4}' | Out-Null
        Write-Host "  -> Lote de telemetria inicial gerado com sucesso." -ForegroundColor Green
    } catch {
        Write-Warning "Nao foi possivel gerar lote simulado inicial: $_"
    }
} else {
    Write-Host "[3/4] Populacao automatica de dados simulados ignorada (use -SeedSimulatedData para ativar)." -ForegroundColor DarkGray
}

# 4. Iniciar o Frontend Streamlit
Write-Host "[4/4] Iniciando interface Streamlit na porta $StreamlitPort..." -ForegroundColor Yellow
Write-Host "  -> Modulos industriais disponiveis (9 paginas):" -ForegroundColor Cyan
Write-Host "     1. Dashboard Geral (Cockpit SCADA)"
Write-Host "     2. Monitoramento em Tempo Real (IEM & Sensores)"
Write-Host "     3. Manutencao Preditiva (Multiclasse & Anomalias)"
Write-Host "     4. OEE e Eficiencia Industrial (Impacto Preditivo & Financeiro)"
Write-Host "     5. Visao Computacional (OpenCV Canny & Termografia HSV)"
Write-Host "     6. Analise de Dados (EDA por Liga Metalica)"
Write-Host "     7. Modelos de IA (Benchmark & Matriz de Confusao)"
Write-Host "     8. Simulador Industrial (Injecao de Falhas & CLP)"
Write-Host "     9. Parecer Tecnico (LGPD, EU AI Act, IEC 62443, ESG)"
Write-Host "------------------------------------------------------------" -ForegroundColor Cyan

if ($BackgroundOnly) {
    $StProcess = Start-Process -FilePath $PythonExe `
        -ArgumentList "-m", "streamlit", "run", "frontend/app.py", "--server.port", "$StreamlitPort", "--server.headless", "true" `
        -WorkingDirectory $ProjectRoot `
        -PassThru `
        -WindowStyle Hidden
    Write-Host "Streamlit iniciado em background (PID: $($StProcess.Id))." -ForegroundColor Green
    Write-Host "Acesse o dashboard em: http://localhost:${StreamlitPort}" -ForegroundColor Green
    exit 0
}

try {
    & $PythonExe -m streamlit run "frontend/app.py" --server.port "$StreamlitPort"
} finally {
    if ($ApiProcess -and -not $ApiProcess.HasExited) {
        Write-Host "Encerrando servidor FastAPI (PID: $($ApiProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $ApiProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
