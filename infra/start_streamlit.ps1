[CmdletBinding()]
param(
    [string]$ListenHost = '127.0.0.1',
    [int]$Port = 8501
)

$ErrorActionPreference = 'Stop'
$RootDir = Split-Path -Parent $PSScriptRoot
$Port = if ($PSBoundParameters.ContainsKey('Port')) { $Port } elseif ($env:STREAMLIT_PORT) { [int]$env:STREAMLIT_PORT } else { 8501 }
$LogFile = Join-Path $PSScriptRoot 'streamlit.log'
$ErrorLogFile = Join-Path $PSScriptRoot 'streamlit-error.log'
$PidFile = Join-Path $PSScriptRoot 'streamlit.pid'

$Python = Join-Path $RootDir 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { $Python = 'python' }

if (Test-Path -LiteralPath $PidFile) {
    $ExistingPidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $ExistingPid = 0
    if ([int]::TryParse($ExistingPidText, [ref]$ExistingPid)) {
        $ExistingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ExistingPid" -ErrorAction SilentlyContinue
        if ($ExistingProcess) {
            Write-Output "Dashboard Streamlit VulcanTech já está em execução em http://127.0.0.1:$Port (PID $ExistingPid)."
            return
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
}

$Arguments = @('-m', 'streamlit', 'run', 'frontend/app.py', '--server.port', "$Port", '--server.headless', 'true')
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $RootDir -RedirectStandardOutput $LogFile -RedirectStandardError $ErrorLogFile -WindowStyle Hidden -PassThru
$Process.Id | Set-Content -LiteralPath $PidFile -NoNewline

Start-Sleep -Milliseconds 1200
Write-Output "Dashboard Streamlit VulcanTech iniciado com sucesso (PID $($Process.Id)). Acesse: http://127.0.0.1:$Port"

