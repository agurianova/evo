#!/usr/bin/env bash
# Independent best-of-N (no evolution engine): 100 terra SEARCH/REPLACE
# patches of python_patch_seed.py, scored with ImmRep25 r0 validate.py
# (same fitness as final terra runs).
#
# Usage:
#   ./scripts/launch_pmhctcr_final_terra_expert_on_bon.sh
#   MAX_MUTANTS=100 RUN_NAME=... ./scripts/launch_pmhctcr_final_terra_expert_on_bon.sh

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
RUN_NAME="${RUN_NAME:-pmhctcr_final_terra_expert_on_bon_m100_r1}"
RUN_DIR="$REPO/outputs/$RUN_NAME"

export PATH="/home/jovyan/.local/bin:$PATH"
unset OPENAI_API_KEY OPENAI_BASE_URL OPENAI_API_BASE AZURE_OPENAI_API_KEY
unset OPENROUTER_API_KEY ANTHROPIC_API_KEY

if [[ -z "${HTTPS_PROXY:-}" && -f "$PCE/scripts/proxy.env" ]]; then
  # shellcheck source=/dev/null
  source "$PCE/scripts/proxy.env"
fi
if [[ -z "${HTTPS_PROXY:-}" ]]; then
  echo "HTTPS_PROXY is not set and $PCE/scripts/proxy.env is missing." >&2
  exit 4
fi
export HTTPS_PROXY HTTP_PROXY="${HTTP_PROXY:-$HTTPS_PROXY}"
export https_proxy="$HTTPS_PROXY" http_proxy="$HTTP_PROXY"
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1,10.0.0.0/8}"
export no_proxy="$NO_PROXY"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] preflight: checking gpt-5.6-terra ..."
preflight_out="$(printf 'Reply with exactly: PREFLIGHT_OK\n' \
  | timeout 180 codex exec --model gpt-5.6-terra \
      -c 'forced_login_method="chatgpt"' \
      --sandbox read-only --ephemeral --skip-git-repo-check 2>&1 || true)"
if [[ "$preflight_out" != *PREFLIGHT_OK* ]]; then
  echo "$preflight_out" | tail -8 >&2
  echo "preflight FAILED" >&2
  exit 5
fi
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] preflight: terra reachable"

mkdir -p "$RUN_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $RUN_NAME n=$MAX_MUTANTS independent-BoN (no evo engine) expert=on"

cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PMHCTCR_SPLIT="${PMHCTCR_SPLIT:-r0}"
export PMHCTCR_DATA="${PMHCTCR_DATA:-$REPO/pmhctcr_data}"
export PYTHONPATH="$REPO:${PYTHONPATH:-}"

python "$REPO/scripts/run_pmhctcr_independent_bon.py" \
  --run-dir "$RUN_DIR" \
  --run-name "$RUN_NAME" \
  -n "$MAX_MUTANTS" \
  --validator-timeout 900 \
  --request-timeout 180 \
  --expert-on \
  2>&1 | tee -a "$RUN_DIR/launch.out"
