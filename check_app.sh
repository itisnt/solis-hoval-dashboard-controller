#!/bin/bash
# Starts app.py if it is not running or does not answer HTTP. Meant to be run from cron every 15 minutes.

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/root/.pyenv/versions/hmi-env/bin/python"
APP="$APP_DIR/app.py"
LOG="$APP_DIR/app.log"
HEALTH_URL="http://127.0.0.1:5000/api/status"

log() {
    echo "$(date '+%F %T') $*" >> "$LOG"
}

is_running() {
    pgrep -af -- "$PYTHON $APP" | grep -qF -- "$PYTHON $APP"
}

is_healthy() {
    curl -fsS --max-time 10 -o /dev/null "$HEALTH_URL"
}

if is_running && is_healthy; then
    exit 0
fi

if is_running; then
    log "app.py antwortet nicht auf $HEALTH_URL, Prozess wird beendet"
    pkill -f -- "$PYTHON $APP"
    sleep 5
fi

cd "$APP_DIR" || exit 1
setsid nohup "$PYTHON" "$APP" >> "$LOG" 2>&1 < /dev/null &
log "app.py gestartet (PID $!)"
