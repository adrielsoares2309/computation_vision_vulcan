[CmdletBinding()]
param(
    [string]$ListenHost,
    [int]$Port
)

$ErrorActionPreference = 'Stop'
$RootDir = Split-Path -Parent $PSScriptRoot
$ListenHost = if ($ListenHost) { $ListenHost } elseif ($env:API_HOST) { $env:API_HOST } else { '127.0.0.1' }
$Port = if ($PSBoundParameters.ContainsKey('Port')) { $Port } elseif ($env:API_PORT) { [int]$env:API_PORT } else { 8000 }
$AppModule = if ($env:API_MODULE) { $env:API_MODULE } else { 'backend.main:app' }
$LogFile = Join-Path $PSScriptRoot 'api.log'
$ErrorLogFile = Join-Path $PSScriptRoot 'api-error.log'
$PidFile = Join-Path $PSScriptRoot 'api.pid'
$HealthHost = $ListenHost
if ($HealthHost -eq '0.0.0.0') { $HealthHost = '127.0.0.1' }
if ($HealthHost -eq '::') { $HealthHost = '[::1]' }
elseif ($HealthHost.Contains(':') -and -not $HealthHost.StartsWith('[')) { $HealthHost = "[$HealthHost]" }
$Url = "http://${HealthHost}:$Port"
$Python = Join-Path $RootDir 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { $Python = 'python' }

if ($Port -lt 1 -or $Port -gt 65535) { throw "Port deve estar entre 1 e 65535: $Port" }

# Se outra instância já responde, não iniciar um segundo processo.
try {
    $Response = Invoke-WebRequest -Uri "$Url/health" -TimeoutSec 2 -UseBasicParsing
    if ($Response.StatusCode -eq 200) {
        Write-Output "API VulcanTech disponível em: $Url/docs"
        return
    }
} catch { }

if (Test-Path -LiteralPath $PidFile) {
    $ExistingPidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $ExistingPid = 0
    if ([int]::TryParse($ExistingPidText, [ref]$ExistingPid)) {
        $ExistingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ExistingPid" -ErrorAction SilentlyContinue
        if ($ExistingProcess) {
            $CommandLine = [string]$ExistingProcess.CommandLine
            if ($CommandLine -match '(?i)uvicorn' -and $CommandLine.Contains($AppModule)) {
                throw "A API VulcanTech (PID $ExistingPid) parece estar em execução, mas /health não respondeu em $Url. Consulte: $LogFile"
            }
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
}

$Arguments = @('-m', 'uvicorn', $AppModule, '--host', $ListenHost, '--port', "$Port")
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $RootDir -RedirectStandardOutput $LogFile -RedirectStandardError $ErrorLogFile -WindowStyle Hidden -PassThru
$Process.Id | Set-Content -LiteralPath $PidFile -NoNewline

for ($Attempt = 1; $Attempt -le 25; $Attempt++) {
    try {
        $Response = Invoke-WebRequest -Uri "$Url/health" -TimeoutSec 2 -UseBasicParsing
        if ($Response.StatusCode -eq 200) {
            Write-Output "API VulcanTech iniciada com sucesso (PID $($Process.Id)). Documentação Swagger: $Url/docs"
            return
        }
    } catch { }
    Start-Sleep -Milliseconds 600
}

throw "A API VulcanTech não respondeu a tempo em $Url/health. Consulte os logs em $LogFile e $ErrorLogFile."

