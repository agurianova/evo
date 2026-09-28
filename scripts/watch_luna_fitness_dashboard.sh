#!/usr/bin/env bash
# Refresh fitness PNGs + dashboard every 60s.
set -euo pipefail
REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
INTERVAL="${1:-60}"
while true; do
  python "$REPO/scripts/refresh_luna_fitness_dashboard.py" || true
  sleep "$INTERVAL"
done
