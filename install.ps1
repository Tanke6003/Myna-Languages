# Instalador de Myna para Windows.
# Detecta GPU/RAM, instala Ollama + el modelo adecuado, prepara Python y crea un acceso directo.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "===== Instalador - Myna =====" -ForegroundColor Cyan

function Refresh-Path {
  $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
              [System.Environment]::GetEnvironmentVariable('Path', 'User')
}

# --- 1) Detectar hardware (RAM, GPU y CPU: nucleos + frecuencia) ---
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$gpus = Get-CimInstance Win32_VideoController
$hasNvidia = [bool]($gpus | Where-Object { $_.Name -match 'NVIDIA' })
$hasAmd = [bool]($gpus | Where-Object { $_.Name -match 'AMD|Radeon' })
$cpu = Get-CimInstance Win32_Processor
$cores = ($cpu | Measure-Object -Property NumberOfCores -Sum).Sum
if (-not $cores) { $cores = [int]$env:NUMBER_OF_PROCESSORS }
$ghz = [math]::Round((($cpu | Measure-Object -Property MaxClockSpeed -Maximum).Maximum) / 1000, 1)
Write-Host ("Hardware: {0} GB RAM | CPU: {1} nucleos @ {2} GHz | NVIDIA: {3} | AMD/Radeon: {4}" -f `
  $ramGB, $cores, $ghz, (@('No', 'Si')[[int]$hasNvidia]), (@('No', 'Si')[[int]$hasAmd]))

# --- 2) Elegir modelo de Ollama ---
# Con GPU manda esta; sin ella, el limite real lo ponen los nucleos+GHz del CPU, acotado por la RAM.
if ($hasNvidia) {
  $model = "qwen2.5:7b"; $why = "GPU NVIDIA -> 7B (acelerado por GPU; Whisper tambien)"
} elseif ($hasAmd -and $ramGB -ge 12) {
  $model = "qwen2.5:7b"; $why = "GPU AMD/Radeon -> 7B (Ollama puede usarla; Whisper ira por CPU)"
} elseif ($cores -ge 8 -and $ramGB -ge 8) {
  $model = "qwen2.5:7b"; $why = "CPU potente ($cores nucleos) -> 7B"
} elseif ($cores -ge 6 -and $ghz -ge 3.0 -and $ramGB -ge 8) {
  $model = "qwen2.5:7b"; $why = "CPU rapido ($cores nucleos @ $ghz GHz) -> 7B"
} elseif ($cores -ge 4 -and $ramGB -ge 6) {
  $model = "qwen2.5:3b"; $why = "CPU medio ($cores nucleos) -> 3B"
} elseif ($cores -ge 2) {
  $model = "qwen2.5:1.5b"; $why = "CPU modesto ($cores nucleos @ $ghz GHz) -> 1.5B"
} else {
  $model = "qwen2.5:0.5b"; $why = "CPU muy limitado -> 0.5B"
}
Write-Host "Modelo recomendado: $model  ($why)" -ForegroundColor Yellow

# --- 3) Python 3.13 ---
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "Instalando Python 3.13..."
  winget install -e --id Python.Python.3.13 --silent --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

# --- 4) Entorno virtual + dependencias ---
if (-not (Test-Path ".\.venv")) { py -3.13 -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

# Solo NVIDIA: librerias CUDA para acelerar Whisper (en AMD no aplican; Whisper ira por CPU)
if ($hasNvidia) {
  Write-Host "GPU NVIDIA detectada: instalando CUDA (cuBLAS/cuDNN) para acelerar Whisper..."
  try { & ".\.venv\Scripts\python.exe" -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 } catch {}
}

# --- 5) Ollama ---
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "Instalando Ollama..."
  winget install -e --id Ollama.Ollama --silent --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

# Espera a que el servidor de Ollama responda antes de descargar
Write-Host "Esperando a que Ollama este listo..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
  try { $null = & ollama list 2>$null; if ($?) { $ready = $true; break } } catch {}
  Start-Sleep -Seconds 2
}
if (-not $ready) { Write-Host "Ollama no respondio; abrelo manualmente y reintenta." -ForegroundColor Yellow }

# --- 6) Descargar el modelo elegido ---
Write-Host "Descargando el modelo $model (puede tardar varios minutos)..."
ollama pull $model
# Sin BOM: Set-Content -Encoding utf8 en PS 5.1 mete BOM y rompe el nombre del modelo en Python.
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'selected_model.txt'), $model)

# --- 7) Acceso directo en el escritorio ---
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Myna.lnk")
# wscript + Myna.vbs => arranca sin ventana de terminal
$lnk.TargetPath = "wscript.exe"
$lnk.Arguments = "`"$PSScriptRoot\Myna.vbs`""
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.IconLocation = if (Test-Path "$PSScriptRoot\myna.ico") { "$PSScriptRoot\myna.ico" } else { "wscript.exe" }
$lnk.Save()

Write-Host ""
Write-Host "Listo. Abre 'Myna' en el escritorio (o ejecuta run.ps1)." -ForegroundColor Green
