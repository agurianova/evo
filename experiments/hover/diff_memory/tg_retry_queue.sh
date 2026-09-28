#!/usr/bin/env bash
# Retry-deliver queued Telegram messages (one file per message, FIFO by name)
# until each sends or the deadline passes. Queue dir: tg_queue/*.txt
set -u
EXP_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$EXP_DIR/../../.." && pwd)"
QUEUE="$EXP_DIR/tg_queue"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
export HTTPS_PROXY="${HTTPS_PROXY:-$(grep -m1 '^SQUID_PROXY=' "$REPO/.env" | cut -d= -f2-)}"
DEADLINE=$((SECONDS + 4 * 3600))

cd "$REPO"
while [ "$SECONDS" -lt "$DEADLINE" ]; do
  found=0
  for f in "$QUEUE"/*.txt; do
    [ -e "$f" ] || continue
    found=1
    if "$PYTHON" -c '
import sys
from tools.telegram_notify import notify
from pathlib import Path
sys.exit(0 if notify(Path(sys.argv[1]).read_text(), parse_mode=None) else 1)
' "$f"; then
      echo "delivered: $(basename "$f")"
      mv "$f" "$f.sent"
    else
      echo "send failed, retrying in 300s"
      break
    fi
  done
  [ "$found" -eq 0 ] && { echo "queue empty, exiting"; exit 0; }
  sleep 300
done
echo "deadline reached with undelivered messages"
