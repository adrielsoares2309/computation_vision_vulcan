[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RootDir = Split-Path -Parent $PSScriptRoot
$ApiHost = if ($env:API_HOST) { $env:API_HOST } else { '127.0.0.1' }
$ApiPort = if ($env:API_PORT) { [int]$env:API_PORT } else { 8000 }
$ApiUrl = "http://${ApiHost}:$ApiPort"
$DashboardPort = if ($env:STREAMLIT_PORT) { [int]$env:STREAMLIT_PORT } else { 8501 }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VulcanTech Smart Metals S.A. - Inicializando Stack        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    Write-Host "[1/3] Iniciando backend FastAPI..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'start_api.ps1') -ListenHost $ApiHost -Port $ApiPort

    Write-Host "[2/3] Iniciando simulador industrial autônomo..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'start_simulator.ps1') -ApiUrl $ApiUrl

    Write-Host "[3/3] Iniciando dashboard Streamlit..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'start_streamlit.ps1') -Port $DashboardPort

} catch {
    Write-Error "Inicialização da stack interrompida: $($_.Exception.Message)"
    throw
}

Write-Output ''
Write-Host "Stack Industrial Ativa:" -ForegroundColor Green
Write-Host "  -> Dashboard Streamlit : http://127.0.0.1:$DashboardPort" -ForegroundColor Cyan
Write-Host "  -> API Swagger Docs    : $ApiUrl/docs" -ForegroundColor Cyan
Write-Host "  -> Verificação Saúde   : $ApiUrl/health" -ForegroundColor Cyan
Write-Host "  -> Parar serviços      : .\infra\stop_services.ps1" -ForegroundColor Yellow

