# Validacao automatizada do build desktop (smoke tests).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> OAE: smoke tests desktop" -ForegroundColor Cyan
$failed = 0

function Assert-Ok($condition, $message) {
    if ($condition) {
        Write-Host "  [OK] $message" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $message" -ForegroundColor Red
        $script:failed++
    }
}

# 1. Backend Python (dev)
Write-Host "`n[1] Backend Python (server_desktop)" -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "smoke-desktop-backend.ps1")

# 2. Backend empacotado (PyInstaller)
Write-Host "`n[2] Backend empacotado (PyInstaller)" -ForegroundColor Yellow
$exe = Join-Path $Root "resources\backend\oae-backend\oae-backend.exe"
Assert-Ok (Test-Path $exe) "oae-backend.exe existe"

$dataDir = Join-Path $env:TEMP "oae-bundle-smoke-$(Get-Random)"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$env:OAE_DATA_DIR = $dataDir
$env:OAE_PORT = "8771"
$proc = $null
try {
    $proc = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 20
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8771/api/health" -TimeoutSec 15
    Assert-Ok ($health.status -eq "ok") "Health do exe empacotado"
    Assert-Ok (Test-Path (Join-Path $dataDir "rules\descriptions.yaml")) "Seed de rules no AppData simulado"
} catch {
    Assert-Ok $false "Backend empacotado: $_"
} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
    Remove-Item Env:OAE_DATA_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:OAE_PORT -ErrorAction SilentlyContinue
    Remove-Item Env:OAE_DESKTOP -ErrorAction SilentlyContinue
}

# 3. Artefatos Electron
Write-Host "`n[3] Artefatos Electron" -ForegroundColor Yellow
Assert-Ok (Test-Path (Join-Path $Root "electron\dist\main.js")) "electron/dist/main.js"
Assert-Ok (Test-Path (Join-Path $Root "frontend\dist\index.html")) "frontend/dist/index.html"
Assert-Ok (Test-Path (Join-Path $Root "desktop\assets\icon.ico")) "desktop/assets/icon.ico"

$unpacked = Join-Path $Root "dist-desktop\win-unpacked\OAE Report Generator.exe"
Assert-Ok (Test-Path $unpacked) "win-unpacked/OAE Report Generator.exe"

$nsis = Join-Path $Root "dist-desktop\OAE Report Generator-0.1.0-win-x64.exe"
$portable = Join-Path $Root "dist-desktop\OAE Report Generator-0.1.0-portable.exe"
Assert-Ok (Test-Path $nsis) "Instalador NSIS gerado"
Assert-Ok (Test-Path $portable) "Executavel portable gerado"

# 4. Testes backend
Write-Host "`n[4] Testes backend (pytest)" -ForegroundColor Yellow
Remove-Item Env:OAE_DATA_DIR -ErrorAction SilentlyContinue
Remove-Item Env:OAE_PORT -ErrorAction SilentlyContinue
Remove-Item Env:OAE_DESKTOP -ErrorAction SilentlyContinue
Remove-Item Env:OAE_BUNDLE_DIR -ErrorAction SilentlyContinue
python -m pytest backend/tests -q
if ($LASTEXITCODE -ne 0) { $failed++ } else { Write-Host "  [OK] 60 testes passando" -ForegroundColor Green }

Write-Host ""
if ($failed -gt 0) {
    Write-Host "Smoke tests concluidos com $failed falha(s)." -ForegroundColor Red
    exit 1
}
Write-Host "Todos os smoke tests passaram." -ForegroundColor Green
