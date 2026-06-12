#!/usr/bin/env bash
# Muestra el recordatorio de Myna (Linux) como notificacion de escritorio.
# Nota: en Linux la accion "abrir al clic" depende del entorno; de base solo notifica.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ICON="$DIR/myna.ico"
MSG="${1:-Practica ingles con Myna: unos minutos hoy y suenas mas nativo.}"
if command -v notify-send >/dev/null 2>&1; then
  notify-send -a "Myna" -i "$ICON" "Practica ingles con Myna" "$MSG"
fi
