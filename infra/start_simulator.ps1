[CmdletBinding()]
param(
    [string]$ApiUrl,
    [double]$IntervalSeconds = 5.0,
    [string]$Regime = "Producao_Normal"
)

$ErrorActionPreference = 'Stop'
$RootDir = Split-Path -Parent $PSScriptRoot
$ApiUrl = if ($ApiUrl) { $ApiUrl } elseif ($env:VULCANTECH_API_URL) { $env:VULCANTECH_API_URL } else { 'http://127.0.0.1:8000' }
$LogFile = Join-Path $PSScriptRoot 'simulator.log'
$ErrorLogFile = Join-Path $PSScriptRoot 'simulator-error.log'
$PidFile = Join-Path $PSScriptRoot 'simulator.pid'

$Python = Join-Path $RootDir 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { $Python = 'python' }

# Checa se o simulador já está rodando
if (Test-Path -LiteralPath $PidFile) {
    $ExistingPidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $ExistingPid = 0
    if ([int]::TryParse($ExistingPidText, [ref]$ExistingPid)) {
        $ExistingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ExistingPid" -ErrorAction SilentlyContinue
        if ($ExistingProcess) {
            Write-Output "Simulador VulcanTech já está em execução (PID $ExistingPid)."
            return
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
}

$Arguments = @('simulator.py', '--api-url', $ApiUrl, '--intervalo', "$IntervalSeconds", '--regime', $Regime)
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $RootDir -RedirectStandardOutput $LogFile -RedirectStandardError $ErrorLogFile -WindowStyle Hidden -PassThru
$Process.Id | Set-Content -LiteralPath $PidFile -NoNewline

Start-Sleep -Milliseconds 800
Write-Output "Simulador VulcanTech iniciado em segundo plano (PID $($Process.Id)). Log: $LogFile"

