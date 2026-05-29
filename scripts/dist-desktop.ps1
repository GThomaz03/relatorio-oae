# Gera instalador NSIS + portable (sem assinatura de codigo).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& (Join-Path $PSScriptRoot "build-desktop.ps1")

$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
npx electron-builder --win --config electron-builder.yml
