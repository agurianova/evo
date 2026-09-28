#!/usr/bin/env bash
# Launch script for experiments/hotpotqa/generalization
# Design: n=4 cold-start runs, held-out validation (fitness=held_F1), 25 gens
# G1/G2: Qwen3-235B vLLM | G3/G4: Gemini-3.1-Pro
#
# BINDING pre-launch checks (must pass before running):
#   1. Prompt review signed off in 03_plan.md — DONE (2026-03-14)
#   2. Split bias check — run baseline on train[0:700] vs train[700:1000], halt if gap >5pp
#   3. Redis DBs 0-3 empty — verified clean
#   4. Verify thinking mode on all 4 chain server endpoints
#
# Usage:
#   bash experiments/hotpotqa/generalization/04_launch.sh

set -euo pipefail

PYTHON=/home/jovyan/envs/evo_fast/bin/python
export GIGAEVO_PYTHON=$PYTHON

# Export OPENAI_API_KEY so Hydra can resolve ${oc.env:OPENAI_API_KEY} in gemini31_pro.yaml
# Use python-dotenv to safely parse .env (avoids quoting/comment issues with bash source)
OPENAI_API_KEY=$(/home/jovyan/envs/evo_fast/bin/python -c \
  "from dotenv import dotenv_values; print(dotenv_values('.env').get('OPENAI_API_KEY',''))")
export OPENAI_API_KEY

# no_proxy: chain servers + mutation LLM servers + localhost
export no_proxy="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.225.51.251"
export NO_PROXY="$no_proxy"

# Shared Hydra overrides — keep as an array so each item is its own arg
COMMON_OVERRIDES=(
  pipeline=hotpotqa_asi
  prompts=generalization
  problem.name=chains/hotpotqa/static_holdout_f1
  num_parents=1
  max_elites_per_generation=8
  max_mutations_per_generation=8
  max_generations=25
  stage_timeout=6000
  dag_timeout=9000
)

# G1 — Qwen3-235B vLLM mutation, chain server A:8001 (default HOTPOTQA_CHAIN_URL)
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 PYTHONPATH=. $PYTHON run.py \
  "${COMMON_OVERRIDES[@]}" \
  llm_base_url=http://10.226.72.211:8777/v1 \
  redis.db=0 \
  tag=gen-1 \
  > experiments/hotpotqa/generalization/run_G1.log 2>&1 &
PID_G1=$!
echo "G1 launched: PID=$PID_G1 (DB=0, mutation=10.226.72.211:8777, chain=10.226.17.25:8001)"

# G2 — Qwen3-235B vLLM mutation, chain server A:8000
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8000/v1 PYTHONPATH=. $PYTHON run.py \
  "${COMMON_OVERRIDES[@]}" \
  llm_base_url=http://10.225.51.251:8777/v1 \
  redis.db=1 \
  tag=gen-2 \
  > experiments/hotpotqa/generalization/run_G2.log 2>&1 &
PID_G2=$!
echo "G2 launched: PID=$PID_G2 (DB=1, mutation=10.225.51.251:8777, chain=10.226.17.25:8000)"

# G3 — Gemini-3.1-Pro mutation (OpenRouter), chain server B:8001
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8001/v1 PYTHONPATH=. $PYTHON run.py \
  "${COMMON_OVERRIDES[@]}" \
  llm=gemini31_pro \
  redis.db=2 \
  tag=gen-3 \
  > experiments/hotpotqa/generalization/run_G3.log 2>&1 &
PID_G3=$!
echo "G3 launched: PID=$PID_G3 (DB=2, mutation=gemini31_pro/OpenRouter, chain=10.225.185.235:8001)"

# G4 — Gemini-3.1-Pro mutation (OpenRouter), chain server B:8000
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8000/v1 PYTHONPATH=. $PYTHON run.py \
  "${COMMON_OVERRIDES[@]}" \
  llm=gemini31_pro \
  redis.db=3 \
  tag=gen-4 \
  > experiments/hotpotqa/generalization/run_G4.log 2>&1 &
PID_G4=$!
echo "G4 launched: PID=$PID_G4 (DB=3, mutation=gemini31_pro/OpenRouter, chain=10.225.185.235:8000)"

echo ""
echo "All 4 runs launched. PIDs: G1=$PID_G1 G2=$PID_G2 G3=$PID_G3 G4=$PID_G4"
echo "Monitor: bash experiments/hotpotqa/generalization/run_status.sh"
