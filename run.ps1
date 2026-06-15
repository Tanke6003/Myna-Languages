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

# --- Asegura que Ollama (la IA, local) este corriendo ---
# Sin esto, si el servidor de Ollama aun no levanto su puerto, el primer turno falla con
# "[WinError 10061] ... el equipo de destino denego la conexion". Si no responde, lo arrancamos
# (ollama serve, sin ventana) y esperamos a que escuche en 127.0.0.1:11434.
function Test-Ollama {
  try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null; $true }
  catch { $false }
}

if (-not (Test-Ollama)) {
  $launched = $false
  # 1) Preferimos la app de Ollama (GUI, SIN consola): arranca el servidor en segundo plano
  #    de forma 100% silenciosa y restaura el icono de la bandeja.
  $ollamaApp = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama app.exe'
  if (Test-Path $ollamaApp) {
    Start-Process -FilePath $ollamaApp
    $launched = $true
  } else {
    # 2) Fallback: 'ollama serve' en ventana oculta (app de consola).
    $ollamaExe = (Get-Command ollama -ErrorAction SilentlyContinue).Source
    if (-not $ollamaExe) {
      $cand = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
      if (Test-Path $cand) { $ollamaExe = $cand }
    }
    if ($ollamaExe) {
      Start-Process -WindowStyle Hidden -FilePath $ollamaExe -ArgumentList 'serve'
      $launched = $true
    }
  }
  if ($launched) {
    for ($i = 0; $i -lt 60; $i++) {     # hasta ~30 s a que el servidor responda
      if (Test-Ollama) { break }
      Start-Sleep -Milliseconds 500
    }
  }
}

$url = "http://127.0.0.1:8000"

# --- Evita mostrar una version vieja: si en :8000 ya corre un backend de OTRA version (p. ej.
#     actualizaste con la app abierta), lo detenemos para que arranque el de ESTA instalacion.
#     (config.APP_VERSION se fija al iniciar el proceso, asi que un backend viejo reporta lo viejo.) ---
if (Test-Path ".\VERSION") {
  $installed = (Get-Content ".\VERSION" -Raw).Trim()
  $running = $null
  try { $running = (Invoke-RestMethod "$url/api/system" -TimeoutSec 2).version } catch { }
  if ($running -and $running -ne $installed) {
    foreach ($sp in ((Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique)) {
      Stop-Process -Id $sp -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 600
  }
}

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
  # Perfil propio para la ventana de Myna: asi distinguimos SUS procesos de tu navegador normal.
  $profileDir = Join-Path $env:LOCALAPPDATA 'Myna\browser'

  # --- Icono de la barra de tareas (modo --app) ---
  # En modo --app, Chromium GENERA y CACHEA el icono de la ventana/taskbar dentro del perfil
  # (Default\Web Applications). Si alguna vez quedo cacheado el icono del navegador (Edge), se
  # queda pegado aunque la pagina ya sirva el de Myna. Borramos SOLO esa cache de iconos para
  # que se regenere desde el favicon actual en cada arranque. NO toca cookies ni localStorage
  # (onboarding, tema, etc. viven en Default\Local Storage y se conservan).
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $profileDir 'Default\Web Applications')

  Start-Process $chrome -ArgumentList "--app=$url", "--user-data-dir=$profileDir"

  # Al cerrar la ventana, detener el backend. No seguimos un PID: Chrome/Edge reparten la ventana
  # entre varios procesos (y el lanzador puede salir enseguida). Seguimos el PERFIL: esperamos a
  # que NO quede ningun proceso del navegador usando el perfil de Myna.
  $procName = [IO.Path]::GetFileNameWithoutExtension($chrome)   # chrome / msedge
  $isOpen = {
    [bool](Get-CimInstance Win32_Process -Filter "Name='$procName.exe'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -like "*$profileDir*" })
  }
  for ($i = 0; $i -lt 20 -and -not (& $isOpen); $i++) { Start-Sleep -Milliseconds 500 }  # espera a que abra
  while (& $isOpen) { Start-Sleep -Milliseconds 1000 }                                   # espera a que cierre
  Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
else {
  # Sin Chrome/Edge: no podemos saber cuando cierras la pestana del navegador por defecto,
  # asi que el backend queda en segundo plano (cierralo desde el Administrador de tareas).
  Start-Process $url
}
