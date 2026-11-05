[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'
$PidNames = @('streamlit', 'simulator', 'api')

Write-Host "Encerrando serviços industriais VulcanTech..." -ForegroundColor Yellow

foreach ($Name in $PidNames) {
    $PidFile = Join-Path $PSScriptRoot "$Name.pid"
    if (Test-Path -LiteralPath $PidFile) {
        $PidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
        $PidNum = 0
        if ([int]::TryParse($PidText, [ref]$PidNum)) {
            $Proc = Get-Process -Id $PidNum -ErrorAction SilentlyContinue
            if ($Proc) {
                Write-Host "  -> Encerrando $Name (PID $PidNum)..." -ForegroundColor DarkGray
                Stop-Process -Id $PidNum -Force -ErrorAction SilentlyContinue
            }
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
}

# Limpa locks e estado do simulador
$LockFile = Join-Path $PSScriptRoot "..\data\runtime\simulator.lock"
if (Test-Path -LiteralPath $LockFile) {
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
}

Write-Host "Todos os serviços VulcanTech foram finalizados com sucesso." -ForegroundColor Green

