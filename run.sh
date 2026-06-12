#!/usr/bin/env bash
# Arranca Myna (Linux): API + frontend, y abre el navegador.
set -e
cd "$(dirname "$0")"

if [ ! -x ./.venv/bin/python ]; then
  echo "Falta el entorno. Ejecuta primero ./install.sh"
  exit 1
fi

# Modelo elegido por el instalador (se puede cambiar luego en la pestaña Ajustes)
[ -f selected_model.txt ] && export TUTOR_OLLAMA_MODEL="$(cat selected_model.txt)"

URL="http://127.0.0.1:8000"

# Abre el navegador (modo app si hay Chrome/Chromium) cuando el servidor responda
(
  for i in $(seq 1 60); do
    curl -s "$URL/api/health" >/dev/null 2>&1 && break
    sleep 0.5
  done
  if command -v google-chrome >/dev/null 2>&1; then google-chrome --app="$URL" >/dev/null 2>&1 &
  elif command -v chromium >/dev/null 2>&1; then chromium --app="$URL" >/dev/null 2>&1 &
  elif command -v chromium-browser >/dev/null 2>&1; then chromium-browser --app="$URL" >/dev/null 2>&1 &
  else xdg-open "$URL" >/dev/null 2>&1 & fi
) &

echo "Myna en $URL  (Ctrl+C para detener)"
exec ./.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
