# Lanza Myna. En el PRIMER arranque instala todo solo
# (Python, dependencias, Ollama y el modelo segun tu hardware). Cerrar esta ventana lo detiene.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- Primer arranque: si falta el entorno, instalar dependencias ---
if (-not (Test-Path ".\.venv\Scripts\python.exe") -or -not (Test-Path ".\selected_model.txt")) {
  Write-Host "Primer arranque: instalando dependencias (puede tardar varios minutos)..." -ForegroundColor Cyan
  & "$PSScriptRoot\install.ps1"
}

# --- Modelo activo (configurable luego en Ajustes) ---
if (Test-Path ".\selected_model.txt") {
  $env:TUTOR_OLLAMA_MODEL = (Get-Content ".\selected_model.txt" -Raw).Trim()
}

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "La instalacion no se completo. Reintenta abriendo de nuevo." -ForegroundColor Red
  pause; exit 1
}

$url = "http://127.0.0.1:8000"

# Abre el navegador en modo app cuando el servidor este listo
Start-Job -ArgumentList $url {
  param($url)
  for ($i = 0; $i -lt 90; $i++) {
    try { Invoke-WebRequest -UseBasicParsing "$url/api/health" -TimeoutSec 1 | Out-Null; break }
    catch { Start-Sleep -Milliseconds 500 }
  }
  $browser = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if ($browser) { Start-Process $browser "--app=$url" } else { Start-Process $url }
} | Out-Null

Write-Host "Myna en $url  (cierra esta ventana para detener)" -ForegroundColor Green
& $py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
