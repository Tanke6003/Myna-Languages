#!/usr/bin/env bash
# Arranca Myna (Linux): API + frontend, abre el navegador en modo app y, al CERRAR la ventana,
# detiene tambien la API. Ctrl+C en la terminal tambien la detiene.
set -e
cd "$(dirname "$0")"

if [ ! -x ./.venv/bin/python ]; then
  echo "Falta el entorno. Ejecuta primero ./install.sh"
  exit 1
fi

# Modelo elegido por el instalador (se puede cambiar luego en la pestana Ajustes)
[ -f selected_model.txt ] && export TUTOR_OLLAMA_MODEL="$(cat selected_model.txt)"

# --- GPU AMD RDNA2 (RX 6000 / Navi 2x = gfx103x): no esta en la lista oficial de ROCm de Ollama.
# Con HSA_OVERRIDE_GFX_VERSION=10.3.0 Ollama puede usarla (requiere ROCm instalado en el sistema).
# Exportamos ANTES de arrancar 'ollama serve' para que el servidor lo herede. RX 7000 va nativa.
if [ -z "${HSA_OVERRIDE_GFX_VERSION:-}" ] && command -v lspci >/dev/null 2>&1; then
  if lspci | grep -Eiq 'Radeon RX 6[0-9]{3}|Navi 2[0-9]'; then
    export HSA_OVERRIDE_GFX_VERSION=10.3.0
  fi
fi

# --- Asegura que Ollama (la IA, local) este corriendo ---
# Si su API no responde, lo arrancamos en segundo plano y esperamos a que escuche. Evita el
# fallo de conexion ("connection refused") en el primer turno cuando Ollama aun no esta listo.
if ! curl -s http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  if command -v ollama >/dev/null 2>&1; then
    nohup ollama serve >/dev/null 2>&1 &
    for i in $(seq 1 60); do
      curl -s http://127.0.0.1:11434/api/version >/dev/null 2>&1 && break
      sleep 0.5
    done
  fi
fi

URL="http://127.0.0.1:8000"

# --- Evita mostrar una version vieja: si en :8000 corre un backend de OTRA version, lo paramos ---
if [ -f VERSION ]; then
  INSTALLED="$(tr -d '[:space:]' < VERSION)"
  RUNNING="$(curl -s http://127.0.0.1:8000/api/system 2>/dev/null | grep -o '"version"[^,}]*' | head -1 | grep -o '[0-9][0-9.]*')"
  if [ -n "$RUNNING" ] && [ "$RUNNING" != "$INSTALLED" ]; then
    pkill -f 'uvicorn backend.main:app' 2>/dev/null || true
    sleep 0.5
  fi
fi

# --- Arranca la API en segundo plano (para poder detenerla al cerrar la ventana) ---
./.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
# Pase lo que pase (Ctrl+C, cierre de ventana, error), no dejar la API colgada.
cleanup() { kill "$SERVER_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

# --- Espera a que la API responda ---
for i in $(seq 1 120); do
  curl -s "$URL/api/health" >/dev/null 2>&1 && break
  sleep 0.5
done

echo "Myna en $URL"

# --- Abre la app en modo ventana con un perfil propio (asi sabemos cuando la cierras) ---
PROFILE="${XDG_DATA_HOME:-$HOME/.local/share}/Myna/browser"
BROWSER=""
for b in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge microsoft-edge-stable; do
  if command -v "$b" >/dev/null 2>&1; then BROWSER="$b"; break; fi
done

if [ -n "$BROWSER" ]; then
  "$BROWSER" --app="$URL" --user-data-dir="$PROFILE" >/dev/null 2>&1 &
  # No seguimos un PID: Chromium reparte la ventana entre varios procesos (y el lanzador puede
  # salir enseguida). Seguimos el PERFIL: esperamos a que abra (hasta ~10 s) y luego a que NO
  # quede ningun proceso del navegador usando el perfil de Myna.
  for i in $(seq 1 20); do
    pgrep -f "user-data-dir=$PROFILE" >/dev/null 2>&1 && break
    sleep 0.5
  done
  while pgrep -f "user-data-dir=$PROFILE" >/dev/null 2>&1; do
    sleep 1
  done
  # La ventana se cerro -> el trap EXIT detiene la API.
else
  # Sin Chrome/Chromium/Edge: abrimos el navegador por defecto. No se puede saber cuando cierras
  # la pestana, asi que mantenemos la API en primer plano (Ctrl+C para detener).
  xdg-open "$URL" >/dev/null 2>&1 &
  wait "$SERVER_PID" || true
fi
