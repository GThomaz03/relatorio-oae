# Smoke test do backend desktop (health + layout AppData).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$dataDir = Join-Path $env:TEMP "oae-smoke-$(Get-Random)"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$env:OAE_DATA_DIR = $dataDir
$env:OAE_PORT = "8765"
$env:OAE_DESKTOP = "1"

$proc = Start-Process python -ArgumentList "-m", "backend.api.server_desktop" -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 8
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 10
    if ($health.status -ne "ok") {
        throw "Health retornou status inesperado"
    }
    if (-not (Test-Path (Join-Path $dataDir "rules\descriptions.yaml"))) {
        throw "Seed de rules nao criado em OAE_DATA_DIR"
    }
    Write-Host "Smoke test backend: OK" -ForegroundColor Green
} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
}
