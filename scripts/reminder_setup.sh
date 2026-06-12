#!/usr/bin/env bash
# Activa o desactiva el recordatorio diario de Myna (Linux, systemd --user).
#   reminder_setup.sh enable 19:00
#   reminder_setup.sh disable
set -e
ACTION="${1:-enable}"
TIME="${2:-19:00}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNITDIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNITDIR"

if [ "$ACTION" = "disable" ]; then
  systemctl --user disable --now myna-reminder.timer 2>/dev/null || true
  echo disabled
  exit 0
fi

# Valida HH:MM (si no, 19:00)
case "$TIME" in
  [0-2][0-9]:[0-5][0-9]|[0-9]:[0-5][0-9]) : ;;
  *) TIME="19:00" ;;
esac

cat > "$UNITDIR/myna-reminder.service" <<EOF
[Unit]
Description=Recordatorio de Myna
[Service]
Type=oneshot
ExecStart=/usr/bin/env bash "$DIR/scripts/reminder.sh"
EOF

cat > "$UNITDIR/myna-reminder.timer" <<EOF
[Unit]
Description=Recordatorio diario de Myna
[Timer]
OnCalendar=*-*-* ${TIME}:00
Persistent=true
[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now myna-reminder.timer 2>/dev/null || true
echo "enabled $TIME"
