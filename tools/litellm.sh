#!/usr/bin/env bash
# tools/litellm.sh — Start a LiteLLM proxy that load-balances across all
# backend LLM servers defined in experiments/infrastructure.yaml.
#
# Usage:
#   bash tools/litellm.sh              # foreground (Ctrl-C to stop)
#   bash tools/litellm.sh --background # daemonize with nohup
#   bash tools/litellm.sh --stop       # kill running litellm proxy
#   bash tools/litellm.sh --status     # check if proxy is running
#
# Requires: litellm conda env (set LITELLM_PYTHON / LITELLM_BIN to override defaults)
#           PyYAML (for parsing infrastructure.yaml)

set -euo pipefail

PROJ="$(cd "$(dirname "$0")/.." && pwd)"
INFRA_YAML="$PROJ/experiments/infrastructure.yaml"
LITELLM_PYTHON="${LITELLM_PYTHON:-/home/jovyan/.mlspace/envs/litellm/bin/python}"
LITELLM_BIN="${LITELLM_BIN:-/home/jovyan/.mlspace/envs/litellm/bin/litellm}"
LITELLM_CONFIG="$PROJ/tools/.litellm_config.yaml"
LITELLM_LOG="$PROJ/tools/.litellm.log"
LITELLM_PID="$PROJ/tools/.litellm.pid"
PORT=4000

# --- Helper: parse infrastructure.yaml and generate litellm config ---
#
# Design notes (see `tools/litellm.sh` header comment for context):
#
# RELIABILITY POLICY: scientific experiments — no dropped requests.
# The proxy queues and retries; it does NOT fail fast on capacity.
# Timeouts below are safety valves for genuinely hung backends, set
# well above any legitimate completion time.
#
# - Route by simple-shuffle (stateless random spread). Moved off least-busy
#   2026-07-04: its in-process in-flight counter drifts under abort/timeout
#   load, starving idle backends — full history in router_settings below.
#   (latency-based-routing was tried 2026-04-22 and regressed: it funnels
#   traffic to the 2 deployments with lowest warmup p50 until they tip into
#   saturation while peers sit at 0%.)
# - Cap per-deployment concurrency to protect vLLM from KV-cache preemption.
#   Cap sized for ~35% KV-cache at avg request size; aggregate cap large
#   enough that typical bursts do not queue long.
# - Generous timeouts (chain 3600s, mutation 7200s). Chain finishes in 60-130s
#   normally; mutation thinking traces up to ~30 min. Timeout only fires on
#   truly stuck backends — never on a legitimate slow generation.
# - num_retries=3. Covers transient 5xx / bouncing backend / one preemption
#   without hammering a degraded backend.
generate_config() {
    "$LITELLM_PYTHON" - "$INFRA_YAML" "$LITELLM_CONFIG" <<'PYEOF'
import os
import sys

import yaml

infra_path, out_path = sys.argv[1], sys.argv[2]

with open(infra_path) as f:
    infra = yaml.safe_load(f)

proxy_cfg = infra.get("litellm_proxy", {})
chain_alias = proxy_cfg.get("alias_chain", "Qwen/Qwen3-8B")
mutation_alias = proxy_cfg.get("alias_mutation", "Qwen3-235B-A22B-Thinking-2507")
instruct_alias = proxy_cfg.get("alias_instruct", "Qwen/Qwen3-235B-A22B-Instruct-2507")
glm_alias = proxy_cfg.get("alias_glm", "glm-5.2")

# Per-deployment concurrency + timeout. Tune these if vLLM capacity changes.
#
# Capacity math (probed from /metrics on 2026-04-20):
#   Chain   : num_gpu_blocks=26829, block_size=16 → 429k KV tokens; max_model_len=32768
#             Worst case (all full context) fits ~13 seqs. Observed ~14.6% of
#             requests are long-gen (>=10k tokens) and stay resident in KV for
#             minutes — enough to tip instances into a preemption feedback loop
#             (100% KV, 100+ preemptions/min, TTFT p99 >10 min) while peers sit idle.
#   Mutation: num_gpu_blocks=16946 → 271k KV tokens; max_model_len=160000
#             Full context fits just ~1.7 seqs. 8 concurrent thinking-mode runs at
#             ~20k tokens each = 160k (59% of cache). Mild preemption possible.
#
# LiteLLM 1.82.6 streaming-semaphore bug (router.py:2148 and siblings):
#   `max_parallel_requests` releases its semaphore at TTFT, not at stream
#   completion. For chain workload (TTFT ~0.3s, gen 30-130s) the effective
#   concurrency cap is inflated ~gen_time/TTFT (100-400×), so it does
#   essentially nothing under streaming load. Confirmed 2026-04-22: with
#   max_parallel_requests=40 per chain, 9/11 chains pinned at 96-99.9% KV
#   with 500+ queued requests.
#   Workaround: use `rpm` (requests-per-minute, enforced by a time-window
#   counter independent of stream duration). At per-deployment rpm=40,
#   aggregate is 9 × 40 = 360 rpm ≈ 6 req/s — well above observed
#   steady-state ~2 req/s chain load and below the burst-to-preemption
#   threshold (~20 concurrent long-gens per instance). Mutation keeps
#   max_parallel_requests since its short/uniform gen times make the bug
#   irrelevant there.
CHAIN_RPM = 40              # per-deployment rate cap
CHAIN_TIMEOUT_S = 3600      # 1h; chain 4k-token gen is 60-130s, so ~30x headroom
MUTATION_CONCURRENCY = 8    # per-deployment cap
MUTATION_TIMEOUT_S = 7200   # 2h; 235B thinking traces ~30 min, so ~4x headroom

models = []

# Chain servers (Qwen3-8B single-GPU instances)
chain = infra["chain_servers"]
chain_model = chain["model"]
chain_endpoints = []
for ep in chain["endpoints"]:
    if ep.get("status", "active") != "active":
        continue
    port = ep.get("port", chain.get("port", 8000))
    # Per-endpoint override: some vLLM instances are launched without
    # --served-model-name, so they advertise the HF cache path as the
    # model id. `served_model_name` lets us keep a unified client alias
    # while sending the backend the name it actually recognizes.
    served = ep.get("served_model_name", chain_model)
    chain_endpoints.append({
        "model_name": chain_alias,
        "litellm_params": {
            "model": f"openai/{served}",
            "api_base": f"http://{ep['host']}:{port}/v1",
            "api_key": "None",
            "rpm": CHAIN_RPM,
            "timeout": CHAIN_TIMEOUT_S,
        },
    })
models.extend(chain_endpoints)

# Mutation servers (Qwen3-235B, one instance per host)
mut = infra["mutation_servers"]
mut_model = mut["model"]
mut_port = mut.get("port", 8000)
for ep in mut["endpoints"]:
    if ep.get("status", "active") != "active":
        continue
    port = ep.get("port", mut_port)
    models.append({
        "model_name": mutation_alias,
        "litellm_params": {
            "model": f"openai/{mut_model}",
            "api_base": f"http://{ep['host']}:{port}/v1",
            "api_key": "None",
            "max_parallel_requests": MUTATION_CONCURRENCY,
            "timeout": MUTATION_TIMEOUT_S,
        },
    })

# Instruct servers (Qwen3-235B Instruct, dedicated alias). Optional section —
# absent on deployments that don't run it. Kept separate from the Thinking
# mutation pool: same size, but no reasoning traces, so it gets its own alias.
instruct = infra.get("instruct_servers")
instruct_count = 0
instruct_concurrency = MUTATION_CONCURRENCY
if instruct:
    ins_model = instruct["model"]
    ins_port = instruct.get("port", 8000)
    instruct_concurrency = int(
        instruct.get("max_parallel", MUTATION_CONCURRENCY)
    )
    for ep in instruct["endpoints"]:
        if ep.get("status", "active") != "active":
            continue
        port = ep.get("port", ins_port)
        served = ep.get("served_model_name", ins_model)
        models.append({
            "model_name": instruct_alias,
            "litellm_params": {
                "model": f"openai/{served}",
                "api_base": f"http://{ep['host']}:{port}/v1",
                "api_key": "None",
                "max_parallel_requests": instruct_concurrency,
                "timeout": MUTATION_TIMEOUT_S,
            },
        })
        instruct_count += 1

# GLM servers (GLM-5.2, dedicated alias). Optional section — absent on
# deployments that don't run it. Served via sglang; same OpenAI-compatible
# API, so it reuses the large-model concurrency/timeout caps.
glm = infra.get("glm_servers")
glm_count = 0
if glm:
    glm_model = glm["model"]
    glm_port = glm.get("port", 8000)
    for ep in glm["endpoints"]:
        if ep.get("status", "active") != "active":
            continue
        port = ep.get("port", glm_port)
        served = ep.get("served_model_name", glm_model)
        models.append({
            "model_name": glm_alias,
            "litellm_params": {
                "model": f"openai/{served}",
                "api_base": f"http://{ep['host']}:{port}/v1",
                "api_key": "None",
                "max_parallel_requests": MUTATION_CONCURRENCY,
                "timeout": MUTATION_TIMEOUT_S,
            },
        })
        glm_count += 1

config = {
    "model_list": models,
    "general_settings": {
        "master_key": os.environ.get("LITELLM_MASTER_KEY", "sk-gigaevo"),
    },
    "litellm_settings": {
        "drop_params": True,
        # Retries on transient failures protect scientific reliability:
        # a 5xx, a momentarily-bouncing backend, or a vLLM preemption
        # should NOT surface as a drop to the experiment. Three retries
        # can pick fresh deployments so one correlated flap cannot drop
        # a request while healthy peers remain.
        "num_retries": 3,
        "request_timeout": MUTATION_TIMEOUT_S,  # upper-bound fallback (2h)
        # Prometheus /metrics: per-deployment routed-request counters
        # (litellm_deployment_success_responses{api_base}) are the proxy-side
        # ground truth for how traffic is actually spread across backends —
        # distinguishes a litellm routing skew from an external consumer
        # hitting a subset of backends directly.
        "callbacks": ["prometheus"],
    },
    "router_settings": {
        # Stateless random spread across all deployments. Moved off
        # least-busy 2026-07-04: its in-process in-flight counter drifts
        # under abort/timeout-heavy load (client-aborted and retried
        # requests miss their decrement), leaving idle backends reading
        # phantom-high so the router starves them — observed 3 of 8 Qwen3-8B
        # backends saturated while 5 sat at 0 in-flight. simple-shuffle has
        # no counter to drift; the per-deployment rpm + max_parallel_requests
        # caps are the overload guard.
        #
        # latency-based-routing was tried 2026-04-22 and regressed badly:
        # it locked onto the 2 deployments with lowest observed p50 at
        # warmup (chain-2 at 99.9% KV / 34 waiting, chain-9 at 99.4% KV /
        # 153 waiting) while the other 8 chains sat at 0% — funnel routing
        # into saturation because "fastest" stays fastest in the sample
        # until it tips, and by then the queue is already catastrophic.
        "routing_strategy": "simple-shuffle",
        "num_retries": 3,
        "timeout": MUTATION_TIMEOUT_S,
        # Circuit breaker: take a backend out of rotation for 30s after
        # 5 consecutive failures. A loose threshold keeps capacity online
        # through transient flaps; a short cooldown recovers fast.
        # Cooldown isolates a bad backend, it does NOT drop user requests —
        # in-flight and queued requests re-route to healthy peers.
        "allowed_fails": 5,
        "cooldown_time": 30,
    },
}

with open(out_path, "w") as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print(f"Generated {out_path}")
print(f"  Chain model alias:    {chain_alias} ({len(chain_endpoints)} endpoints,"
      f" rpm={CHAIN_RPM}, timeout={CHAIN_TIMEOUT_S}s)")
print(f"  Mutation model alias: {mutation_alias} "
      f"({len(models) - len(chain_endpoints) - instruct_count - glm_count} endpoints,"
      f" max_parallel_requests={MUTATION_CONCURRENCY}, timeout={MUTATION_TIMEOUT_S}s)")
if instruct_count:
    print(f"  Instruct model alias: {instruct_alias} "
          f"({instruct_count} endpoints,"
          f" max_parallel_requests={instruct_concurrency}, timeout={MUTATION_TIMEOUT_S}s)")
if glm_count:
    print(f"  GLM model alias:      {glm_alias} "
          f"({glm_count} endpoints,"
          f" max_parallel_requests={MUTATION_CONCURRENCY}, timeout={MUTATION_TIMEOUT_S}s)")
print(f"  Routing strategy:     simple-shuffle")
print(f"  num_retries:          3")
print(f"  Prometheus /metrics:  enabled (per-deployment routing counters)")
PYEOF
}

# --- Commands ---

do_stop() {
    if [ -f "$LITELLM_PID" ]; then
        pid=$(cat "$LITELLM_PID")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping litellm proxy (PID $pid)..."
            kill "$pid"
            rm -f "$LITELLM_PID"
            echo "Stopped."
        else
            echo "PID $pid not running. Cleaning up stale pidfile."
            rm -f "$LITELLM_PID"
        fi
    else
        echo "No pidfile found. Checking for running litellm processes..."
        pkill -f "litellm --config" && echo "Killed." || echo "No litellm proxy running."
    fi
}

do_status() {
    if [ -f "$LITELLM_PID" ]; then
        pid=$(cat "$LITELLM_PID")
        if kill -0 "$pid" 2>/dev/null; then
            echo "LiteLLM proxy running (PID $pid) on port $PORT"
            curl -s "http://localhost:$PORT/health" 2>/dev/null && echo "" || echo "  (health check failed — may still be starting)"
            return 0
        else
            echo "PID $pid not running (stale pidfile)"
            rm -f "$LITELLM_PID"
            return 1
        fi
    else
        echo "No litellm proxy running."
        return 1
    fi
}

do_start() {
    local background="${1:-false}"

    # Check if already running
    if [ -f "$LITELLM_PID" ] && kill -0 "$(cat "$LITELLM_PID")" 2>/dev/null; then
        echo "LiteLLM proxy already running (PID $(cat "$LITELLM_PID")). Use --stop first."
        exit 1
    fi

    # Set NO_PROXY for backend access
    no_proxy_ips=$("$LITELLM_PYTHON" -c "
import yaml
with open('$INFRA_YAML') as f:
    infra = yaml.safe_load(f)
print(','.join(infra.get('no_proxy_hosts', [])))
")
    export NO_PROXY="$no_proxy_ips"
    export no_proxy="$no_proxy_ips"

    # Generate config from infrastructure.yaml
    echo "--- Generating LiteLLM config from $INFRA_YAML ---"
    generate_config
    echo ""

    if [ "$background" = "true" ]; then
        echo "--- Starting LiteLLM proxy (background, port $PORT) ---"
        nohup "$LITELLM_BIN" \
            --config "$LITELLM_CONFIG" \
            --port "$PORT" \
            --host 0.0.0.0 \
            > "$LITELLM_LOG" 2>&1 &
        echo $! > "$LITELLM_PID"
        echo "PID: $(cat "$LITELLM_PID")"
        echo "Log: $LITELLM_LOG"
        echo ""
        echo "Waiting for proxy to be ready..."
        for i in $(seq 1 30); do
            if curl -s "http://localhost:$PORT/health" >/dev/null 2>&1; then
                echo "LiteLLM proxy ready on port $PORT"
                echo ""
                echo "Use in experiments:"
                echo "  Chain:    http://localhost:$PORT/v1  model=$("$LITELLM_PYTHON" -c "import yaml; print(yaml.safe_load(open('$INFRA_YAML'))['litellm_proxy']['alias_chain'])")"
                echo "  Mutation: http://localhost:$PORT/v1  model=$("$LITELLM_PYTHON" -c "import yaml; print(yaml.safe_load(open('$INFRA_YAML'))['litellm_proxy']['alias_mutation'])")"
                echo "  Instruct: http://localhost:$PORT/v1  model=$("$LITELLM_PYTHON" -c "import yaml; print(yaml.safe_load(open('$INFRA_YAML'))['litellm_proxy'].get('alias_instruct',''))")"
                return 0
            fi
            sleep 2
        done
        echo "WARNING: proxy did not become healthy within 60s. Check $LITELLM_LOG"
    else
        echo "--- Starting LiteLLM proxy (foreground, port $PORT) ---"
        echo "Press Ctrl-C to stop."
        echo ""
        exec "$LITELLM_BIN" \
            --config "$LITELLM_CONFIG" \
            --port "$PORT" \
            --host 0.0.0.0
    fi
}

# --- Main ---
case "${1:-}" in
    --stop)
        do_stop
        ;;
    --status)
        do_status
        ;;
    --background)
        do_start true
        ;;
    ""|--foreground)
        do_start false
        ;;
    *)
        echo "Usage: bash tools/litellm.sh [--background|--foreground|--stop|--status]"
        exit 1
        ;;
esac
