# Lanza Myna. Normalmente lo invoca Myna.vbs en una ventana OCULTA (sin terminal).
# En el PRIMER arranque abre una ventana VISIBLE solo para mostrar la instalacion
# (Python, dependencias, Ollama y el modelo segun el hardware).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- Primer arranque: instala en una ventana visible (con progreso) y espera a que termine ---
if (-not (Test-Path ".\.venv\Scripts\python.exe") -or -not (Test-Path ".\selected_model.txt")) {
  Start-Process powershell -Wait -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'install.ps1'))
}

# --- Modelo activo (configurable luego en Ajustes) ---
if (Test-Path ".\selected_model.txt") {
  $env:TUTOR_OLLAMA_MODEL = (Get-Content ".\selected_model.txt" -Raw).Trim()
}

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { exit 1 }   # instalacion incompleta; sin ventana que mostrar

$url = "http://127.0.0.1:8000"

# --- Arranca el servidor OCULTO (proceso aparte para poder detenerlo al cerrar la app) ---
$server = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory $PSScriptRoot `
  -FilePath $py -ArgumentList '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'

# --- Espera a que el servidor responda ---
for ($i = 0; $i -lt 120; $i++) {
  try { Invoke-WebRequest -UseBasicParsing "$url/api/health" -TimeoutSec 1 | Out-Null; break }
  catch { Start-Sleep -Milliseconds 500 }
}

# --- Abre la app en modo ventana; al cerrarla se detiene el servidor ---
$chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chrome) {
  # Perfil propio: la ventana es un proceso independiente, asi sabemos cuando el usuario la cierra.
  $profileDir = Join-Path $env:LOCALAPPDATA 'Myna\browser'
  $browser = Start-Process -PassThru $chrome -ArgumentList "--app=$url", "--user-data-dir=$profileDir"
  try { Wait-Process -Id $browser.Id } catch {}
  Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
else {
  # Sin Chrome/Edge: abre el navegador por defecto y deja el servidor corriendo en segundo plano.
  Start-Process $url
}
