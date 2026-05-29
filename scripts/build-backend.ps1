# Empacota o backend Python com PyInstaller (modo onedir).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> OAE: build backend (PyInstaller onedir)" -ForegroundColor Cyan

$templatePath = Join-Path $Root "backend\templates\report_template.docx"
if (-not (Test-Path $templatePath)) {
    throw "Template Word ausente em backend\templates\report_template.docx. Copie o template RSP para esse caminho antes do build."
}

$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "Instalando PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller
}

$outDir = Join-Path $Root "resources\backend"
$workDir = Join-Path $Root "build\pyinstaller"
if (Test-Path $outDir) {
    Remove-Item -Recurse -Force $outDir
}

pyinstaller pyinstaller/oae-backend.spec `
    --noconfirm `
    --distpath $outDir `
    --workpath $workDir `
    --clean

$exePath = Join-Path $outDir "oae-backend\oae-backend.exe"
if (-not (Test-Path $exePath)) {
    throw "Build falhou: $exePath nao encontrado"
}

Write-Host "Backend empacotado em: $exePath" -ForegroundColor Green
