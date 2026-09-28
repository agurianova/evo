#!/usr/bin/env bash
# Localhost HTTP CONNECT proxy in front of the lab egress proxy.
#
# Credentials stay in python_code_evolution/scripts/proxy.env (mode 600).
# This wrapper only sources that file and starts scripts/http_proxy.py on
# 127.0.0.1. Point clients at http://127.0.0.1:18080.
#
#   bash scripts/run_http_proxy.sh            # foreground
#   bash scripts/run_http_proxy.sh --background
#   bash scripts/run_http_proxy.sh --stop
#   bash scripts/run_http_proxy.sh --status

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
BIND="${BIND:-127.0.0.1}"
PORT="${PORT:-18080}"
PID_FILE="$REPO/tools/.local_http_proxy.pid"
LOG_FILE="$REPO/tools/.local_http_proxy.log"
PY="${PYTHON:-python3}"

load_upstream() {
  if [[ -n "${HTTPS_PROXY:-}" ]]; then
    return 0
  fi
  if [[ -f "$PCE/scripts/proxy.env" ]]; then
    # shellcheck source=/dev/null
    source "$PCE/scripts/proxy.env"
  fi
  if [[ -z "${HTTPS_PROXY:-}" ]]; then
    echo "HTTPS_PROXY is not set and $PCE/scripts/proxy.env is missing." >&2
    exit 4
  fi
  export HTTPS_PROXY HTTP_PROXY="${HTTP_PROXY:-$HTTPS_PROXY}"
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(cat "$PID_FILE")"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

cmd="${1:-}"
case "$cmd" in
  --stop)
    if ! is_running; then
      echo "local proxy is not running"
      rm -f "$PID_FILE"
      exit 0
    fi
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "local proxy stopped"
    exit 0
    ;;
  --status)
    if is_running; then
      echo "local proxy running pid=$(cat "$PID_FILE") http://$BIND:$PORT"
      exit 0
    fi
    echo "local proxy is not running"
    exit 1
    ;;
  --background)
    if is_running; then
      echo "local proxy already running pid=$(cat "$PID_FILE") http://$BIND:$PORT"
      exit 0
    fi
    load_upstream
    mkdir -p "$(dirname "$PID_FILE")"
    nohup "$PY" "$REPO/scripts/http_proxy.py" --bind "$BIND" --port "$PORT" --upstream "$HTTPS_PROXY" \
      >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    sleep 0.3
    if ! is_running; then
      echo "local proxy failed to start; see $LOG_FILE" >&2
      exit 5
    fi
    echo "local proxy http://$BIND:$PORT pid=$(cat "$PID_FILE") (upstream URL not printed)"
    echo "export HTTP_PROXY=http://$BIND:$PORT HTTPS_PROXY=http://$BIND:$PORT"
    echo "export NO_PROXY=localhost,127.0.0.1,::1,10.0.0.0/8"
    exit 0
    ;;
  ""|--foreground)
    load_upstream
    exec "$PY" "$REPO/scripts/http_proxy.py" --bind "$BIND" --port "$PORT" --upstream "$HTTPS_PROXY"
    ;;
  *)
    echo "usage: $0 [--foreground|--background|--stop|--status]" >&2
    exit 2
    ;;
esac
