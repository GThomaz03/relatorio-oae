# Pipeline completo: frontend + backend + Electron.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> OAE: build desktop completo" -ForegroundColor Cyan

Write-Host "`n[1/4] Frontend (Vite)..." -ForegroundColor Cyan
Push-Location frontend
npm run build
Pop-Location

Write-Host "`n[2/4] Backend (PyInstaller)..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "build-backend.ps1")

Write-Host "`n[3/4] Electron (TypeScript)..." -ForegroundColor Cyan
npm run electron:compile

Write-Host "`n[4/4] Pronto para electron-builder (npm run desktop:dist)" -ForegroundColor Green
