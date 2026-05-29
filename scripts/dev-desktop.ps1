# Desenvolvimento desktop: backend Python + Vite + Electron.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:OAE_DESKTOP = "1"
$dataDir = Join-Path $env:LOCALAPPDATA "OAE Report Generator\dev-data"
$env:OAE_DATA_DIR = $dataDir
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

Write-Host "OAE Desktop Dev" -ForegroundColor Cyan
Write-Host "  OAE_DATA_DIR = $dataDir"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""

$backendCmd = "Set-Location '$Root'; `$env:OAE_DESKTOP='1'; `$env:OAE_DATA_DIR='$dataDir'; `$env:OAE_PORT='8765'; python -m backend.api.server_desktop"
$viteCmd = "Set-Location '$Root\frontend'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
Start-Process powershell -ArgumentList "-NoExit", "-Command", $viteCmd | Out-Null

Write-Host "Aguardando backend e Vite..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

$env:ELECTRON_ENABLE_LOGGING = "1"
npm run electron:dev
