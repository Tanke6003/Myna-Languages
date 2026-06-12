#!/usr/bin/env bash
# Instalador de Myna para Linux.
# Detecta GPU/RAM, instala Ollama + el modelo adecuado y prepara Python.
set -e
cd "$(dirname "$0")"
echo "===== Instalador - Myna (Linux) ====="

# --- 1) Hardware (RAM, GPU y CPU: nucleos + frecuencia) ---
RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')
[ -z "$RAM_GB" ] && RAM_GB=8
if command -v nvidia-smi >/dev/null 2>&1; then HAS_NVIDIA=1; else HAS_NVIDIA=0; fi
if lspci 2>/dev/null | grep -iE 'vga|3d|display' | grep -iq 'amd\|radeon'; then HAS_AMD=1; else HAS_AMD=0; fi
CORES=$(awk -F: '/^cpu cores/{print $2; exit}' /proc/cpuinfo 2>/dev/null | tr -d ' ')
[ -z "$CORES" ] && CORES=$(nproc 2>/dev/null || echo 2)
GHZ=$(awk -F: '/cpu MHz/{print $2; exit}' /proc/cpuinfo 2>/dev/null | awk '{printf "%.0f", $1}')
[ -z "$GHZ" ] && GHZ=0
echo "RAM: ${RAM_GB} GB | CPU: ${CORES} nucleos (~${GHZ} MHz) | NVIDIA: $HAS_NVIDIA | AMD: $HAS_AMD"

# --- 2) Modelo segun hardware (sin GPU, manda el CPU: nucleos + GHz) ---
if [ "$HAS_NVIDIA" = "1" ]; then MODEL="qwen2.5:7b"
elif [ "$HAS_AMD" = "1" ] && [ "$RAM_GB" -ge 12 ]; then MODEL="qwen2.5:7b"
elif [ "$CORES" -ge 8 ] && [ "$RAM_GB" -ge 8 ]; then MODEL="qwen2.5:7b"
elif [ "$CORES" -ge 6 ] && [ "$GHZ" -ge 3000 ] && [ "$RAM_GB" -ge 8 ]; then MODEL="qwen2.5:7b"
elif [ "$CORES" -ge 4 ] && [ "$RAM_GB" -ge 6 ]; then MODEL="qwen2.5:3b"
elif [ "$CORES" -ge 2 ]; then MODEL="qwen2.5:1.5b"
else MODEL="qwen2.5:0.5b"; fi
echo "Modelo elegido: $MODEL"

# --- 3) Python venv + dependencias ---
PY=$(command -v python3.13 || command -v python3)
"$PY" -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

# Solo NVIDIA: librerias CUDA para acelerar Whisper (en AMD no aplican; Whisper ira por CPU)
if [ "$HAS_NVIDIA" = "1" ]; then
  echo "GPU NVIDIA detectada: instalando CUDA (cuBLAS/cuDNN) para acelerar Whisper..."
  ./.venv/bin/python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 || true
fi

# --- 4) Ollama ---
if ! command -v ollama >/dev/null 2>&1; then
  echo "Instalando Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Espera a que responda
for i in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 2; done

# --- 5) Descargar el modelo ---
echo "Descargando $MODEL (puede tardar)..."
ollama pull "$MODEL"
echo "$MODEL" > selected_model.txt

echo ""
echo "Listo. Arranca con:  ./run.sh"
