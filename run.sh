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
