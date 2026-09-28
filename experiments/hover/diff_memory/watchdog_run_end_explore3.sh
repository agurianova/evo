#!/usr/bin/env bash
# Run-end watchdog for the explore3 memory pair (TS=20260710_145836,
# memory.reader.max_cards=3 + memory.probe_policy.max_probe_cards_per_decision=3;
# relaunch — the 11:58 attempt had an inert treatment and was aborted).
# Waits for both run PIDs to exit, then runs the memory-behavior analyzer,
# pulls final best fitness, evaluates expected-behavior verdicts, and sends
# the health report to Telegram.

set -uo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/hover/diff_memory"
TS="20260710_145836"
PIDS_FILE="$EXP_DIR/pids_explore3_$TS.txt"
REPORT="$EXP_DIR/memory_health_report_explore3_$TS.txt"

export HTTPS_PROXY="${HTTPS_PROXY:-$(grep -m1 '^SQUID_PROXY=' "$PROJ/.env" | cut -d= -f2-)}"

alive() { kill -0 "$1" 2>/dev/null; }

R1_PID=$(awk '$1=="R1"{print $2}' "$PIDS_FILE")
R2_PID=$(awk '$1=="R2"{print $2}' "$PIDS_FILE")
R1_OUT=$(awk '$1=="R1"{print $4}' "$PIDS_FILE")
R2_OUT=$(awk '$1=="R2"{print $4}' "$PIDS_FILE")

echo "watchdog: waiting on R1=$R1_PID R2=$R2_PID"
while alive "$R1_PID" || alive "$R2_PID"; do
  sleep 300
done
echo "watchdog: both runs exited at $(date '+%F %T')"
sleep 60  # let final writer sweep + log flush settle

{
  echo "EXPLORE3 MEMORY PAIR (max_cards=3) — RUN-END HEALTH REPORT ($TS)"
  echo "generated: $(date '+%F %T')"
  echo
  echo "--- final best fitness (explore3 runs) ---"
  cd "$PROJ" || exit 1
  gigaevo -r "$R1_OUT/storage:MEM_R1" top -n 3 2>&1
  gigaevo -r "$R2_OUT/storage:MEM_R2" top -n 3 2>&1
  echo "max_cards=1 memory pair (2026-07-10): 0.8322 / 0.8011"
  echo "no-memory pair (2026-07-09): 0.8089 / 0.8078"
  echo
  echo "--- memory behavior analysis ---"
  "$PYTHON" "$EXP_DIR/analyze_memory_behavior.py" \
    "R1:$EXP_DIR/logs/explore3_R1_$TS.log:$PROJ/SHARE_HOVER_DIFF_MEMORY_EXPLORE3_R1_$TS" \
    "R2:$EXP_DIR/logs/explore3_R2_$TS.log:$PROJ/SHARE_HOVER_DIFF_MEMORY_EXPLORE3_R2_$TS" 2>&1
} > "$REPORT"

cd "$PROJ" && "$PYTHON" - "$REPORT" <<'EOF'
import json
import re
import sys

report_path = sys.argv[1]
text = open(report_path).read()

verdicts = {}
m = re.search(r"=== VERDICTS \(JSON\) ===\n(\{.*\})", text, re.S)
if m:
    verdicts = json.loads(m.group(1))

lines = ["Explore3 runs FINISHED (3 cards per mutation) - automated health check", ""]
fits = []
for lbl in ("MEM_R1", "MEM_R2"):
    m_fit = re.search(rf'{lbl}".*?"Fitness": ([0-9.]+)', text, re.S)
    fits.append(f"{float(m_fit.group(1)):.4f}" if m_fit else "?")
lines.append(f"Best fitness: R1 {fits[0]} / R2 {fits[1]} "
             "(1-card memory pair got 0.8322 / 0.8011; no-memory 0.8089 / 0.8078)")
lines.append("")

for label, v in verdicts.items():
    frac = v.get("auction_fraction_of_candidates", 0)
    mx = v.get("max_card", {})
    checks = []
    if 0.30 <= frac <= 0.40:
        checks.append(f"auction picks cards at {frac:.0%} of chances - exactly the tuned rate")
    elif 0.10 <= frac <= 0.70:
        checks.append(f"auction picks cards at {frac:.0%} of chances - tuned target was 30-40%, "
                      "drifted but not broken (dial: ev_floor_quantile)")
    else:
        checks.append(f"auction rate {frac:.0%} is OUT of the safe band - needs ev_floor_quantile retune")
    if mx.get("count", 0) > 60:
        checks.append(f"one card was injected {mx['count']}x - dominance problem, "
                      "next fix is w_nov > 0 (novelty pressure), not auction retuning")
    else:
        checks.append(f"no card dominates (most-used card: {mx.get('count', 0)}x, limit 60x)")
    checks.append("reputation learned from real outcomes: " + ("YES" if v.get("reputation_learned") else "NO - investigate"))
    checks.append("cold-card probe lane active: " + ("YES" if v.get("probe_lane_active") else "NO - investigate"))
    checks.append("zombie cards (stuck in probe forever): " + ("none" if v.get("no_zombies") else "FOUND - investigate"))
    checks.append("counterfactual no-card baseline collected: " + ("YES" if v.get("no_card_evidence_accumulating") else "NO"))
    checks.append(f"cards in bank at end: {v.get('cards_written', '?')}")
    lines.append(f"{label}:")
    lines.extend(f"  - {c}" for c in checks)
    lines.append("")

lines.append("Full report attached. Three-way comparison (3-card vs 1-card vs no-memory) + PDF to follow.")
msg = "\n".join(lines)

from tools.telegram_notify import notify, send_document
notify(msg, parse_mode="")
send_document(report_path, caption="Explore3 run-end memory health report", parse_mode=None)
EOF
echo "watchdog: report sent ($REPORT)"
