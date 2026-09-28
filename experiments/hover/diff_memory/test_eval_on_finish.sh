#!/usr/bin/env bash
# When the ALL-IN pair in latest_allin.env finishes cleanly, MMR-rank its
# top-10 (mmr_top10.py, paired-bootstrap duels) and evaluate each arm's FINAL
# top-1 plus the MMR winner on the HoVer TEST split with the hard metric
# (discrete coverage; user directives 2026-07-12) and Telegram the results.
# Pair identity is frozen at spawn — latest_allin.env gets rewritten.
#   setsid ./test_eval_on_finish.sh >> logs/test_eval_on_finish_$TS.log 2>&1 &
set -uo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/hover/diff_memory"

# shellcheck disable=SC1090
source "$EXP_DIR/latest_allin.env"
WAIT_TS="$TS"
WAIT_ROOT="$RUN_ROOT"
MEM_PID=$(awk '$1=="MEM_R1"{print $2}' "$PIDS_FILE")
NOMEM_PID=$(awk '$1=="NOMEM_R1"{print $2}' "$PIDS_FILE")
WD_LOG="$EXP_DIR/logs/watchdog_allin_${WAIT_TS}.log"

export HOVER_CHAIN_URL HOVER_CHAIN_MODEL
export NO_PROXY="10.232.24.68,localhost,127.0.0.1${NO_PROXY:+,$NO_PROXY}"
export HTTPS_PROXY="${HTTPS_PROXY:-$(grep -m1 '^SQUID_PROXY=' "$PROJ/.env" | cut -d= -f2-)}"

tg() {
  cd "$PROJ" && "$PYTHON" -c '
import sys
from tools.telegram_notify import notify
notify(sys.stdin.read(), parse_mode=None)
' <<< "$1"
}

echo "test-eval-queue: waiting on TS=$WAIT_TS MEM=$MEM_PID NOMEM=$NOMEM_PID"

while kill -0 "$MEM_PID" 2>/dev/null || kill -0 "$NOMEM_PID" 2>/dev/null; do
  sleep 300
done
# Let the pair-1 watchdog finish its final sweep before hitting the backends.
while [ -n "$(lsof -t "$WD_LOG" 2>/dev/null)" ]; do
  sleep 60
done

if [ ! -d "$WAIT_ROOT" ]; then
  tg "🧪 TEST eval SKIPPED: first replica TS=$WAIT_TS did not finish cleanly (run root aborted/renamed)."
  exit 1
fi

top1_file() {
  local arm="$1" tid
  tid=$(cd "$PROJ" && gigaevo -r "$WAIT_ROOT/${arm}/storage:${arm}" top -n 1 2>/dev/null \
    | grep -oE '"ID": "[^"]+"' | head -1 | cut -d'"' -f4)
  ls "$WAIT_ROOT/${arm}/storage"/*/programs/"${tid}"*.json 2>/dev/null | head -1
}

MEM_FILE=$(top1_file MEM_R1)
NOMEM_FILE=$(top1_file NOMEM_R1)
if [ -z "$MEM_FILE" ] || [ -z "$NOMEM_FILE" ]; then
  tg "🧪 TEST eval FAILED: could not locate top-1 program files for TS=$WAIT_TS (MEM='$MEM_FILE' NOMEM='$NOMEM_FILE')."
  exit 1
fi

MMR_OUT=$(cd "$PROJ" && "$PYTHON" "$EXP_DIR/mmr_top10.py" "$WAIT_ROOT" --n 10 2>&1)
echo "$MMR_OUT"
MMR_FILE=$(grep '^MMR winner file: ' <<< "$MMR_OUT" | cut -d' ' -f4-)

SPECS=("MEM_R1_final_top1:$MEM_FILE" "NOMEM_R1_final_top1:$NOMEM_FILE")
if [ -n "$MMR_FILE" ] && [ "$MMR_FILE" != "$MEM_FILE" ] && [ "$MMR_FILE" != "$NOMEM_FILE" ]; then
  SPECS+=("MMR_winner:$MMR_FILE")
fi

OUT=$(cd "$PROJ" && "$PYTHON" "$EXP_DIR/eval_test_hard.py" "${SPECS[@]}" --k 5 2>&1 | tail -21)
tg "🧪 TEST-split HARD-metric eval — pair TS=$WAIT_TS final winners + MMR pick (300 test claims, K=5). Hard = 1 only if ALL gold articles retrieved; in-run fitness is the softer fractional metric, so hard numbers sit lower by construction.

MMR top-10 (paired-bootstrap duels on the shared 300-claim val set):
$(grep -E '^(rk| *[0-9]+ )' <<< "$MMR_OUT")

$OUT

Full records: experiments/hover/diff_memory/test_eval_results.jsonl + mmr_results.jsonl"
echo "test-eval-queue: done at $(date '+%F %T')"
