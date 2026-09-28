#!/usr/bin/env python3
"""Automated diagnostic script for GigaEvo experiment runs.

Checks process health, engine metrics, LLM connectivity, Redis state,
and log patterns. Produces a structured report with severity tags.

Usage:
    # Auto-discover all runs from experiment.yaml:
    PYTHONPATH=. python .claude/skills/experiment-diagnose/scripts/diagnose.py --experiment hover/dynamic-topology

    # Single run (manual):
    PYTHONPATH=. python .claude/skills/experiment-diagnose/scripts/diagnose.py \
        --db 9 --prefix chains/hover/static [--log run_F1.log] [--chain-url http://...] [--mutation-url http://...]

Exit codes: 0 = healthy, 1 = issues found, 2 = critical issues
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

# Resolve repo root so `gigaevo.*` imports work when this script runs
# directly (without PYTHONPATH=.). The auto-discover path below repeats
# this via sys.path.insert, but snapshot reads happen in the single-run
# path too, so we need the path unconditionally. Path layout:
# <repo>/.claude/skills/experiment-diagnose/scripts/diagnose.py — so we
# climb 5 parents to reach <repo>.
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT))

from gigaevo.evolution.engine.snapshot import (  # noqa: E402
    ENGINE_SNAPSHOT_KEY,
    EngineSnapshot,
)


def _metric_val(raw_list, default=0):
    """Extract numeric value from Redis metrics JSON, handling null values."""
    if not raw_list:
        return default
    v = json.loads(raw_list[0])["v"]
    return v if v is not None else default


def _read_engine_snapshot(r, prefix: str) -> EngineSnapshot | None:
    """Read ``engine:snapshot`` JSON blob from ``{prefix}:run_state``.

    Returns ``None`` when the snapshot is absent or the JSON is corrupt
    (with a WARNING print on corruption). Sync twin of
    :func:`gigaevo.evolution.engine.snapshot.load_engine_snapshot`. We
    duplicate the three-liner here rather than import from
    ``gigaevo.monitoring.redis_queries`` to avoid pulling RunSpec /
    RunSnapshot / CANONICAL_EVENTS transitively into a diagnostics
    script.
    """
    raw = r.hget(f"{prefix}:run_state", ENGINE_SNAPSHOT_KEY)
    if raw is None:
        return None
    try:
        return EngineSnapshot.model_validate_json(raw)
    except Exception as exc:
        print(
            f"WARNING: engine:snapshot JSON corrupt for prefix={prefix!r} "
            f"({exc}); treating as missing",
            file=sys.stderr,
        )
        return None


# ---------------------------------------------------------------------------
# Result collection
# ---------------------------------------------------------------------------
class Finding:
    def __init__(
        self, severity: str, layer: str, title: str, detail: str, fix: str = ""
    ):
        self.severity = severity  # CRITICAL, MAJOR, MINOR, INFO
        self.layer = layer
        self.title = title
        self.detail = detail
        self.fix = fix

    def __str__(self):
        tag = {"CRITICAL": "!!!", "MAJOR": "!!", "MINOR": "!", "INFO": "."}[
            self.severity
        ]
        fix_str = f"\n         Fix: {self.fix}" if self.fix else ""
        return (
            f"  [{tag}] {self.severity}: {self.title}\n         {self.detail}{fix_str}"
        )


findings: list[Finding] = []


def add(severity, layer, title, detail, fix=""):
    findings.append(Finding(severity, layer, title, detail, fix))


def ok(layer, title, detail=""):
    findings.append(Finding("INFO", layer, title, detail or "OK"))


# ---------------------------------------------------------------------------
# Check 1: Process health
# ---------------------------------------------------------------------------
def check_process(
    pid: int | None, label: str, r=None, prefix: str = "", max_gen: int | None = None
):
    if pid is None:
        add(
            "MINOR",
            "Process",
            f"{label}: No PID provided",
            "Cannot check process health",
        )
        return

    try:
        os.kill(pid, 0)
        ok("Process", f"{label}: PID {pid} alive")
    except OSError:
        # Check if the run completed normally (engine set completion_reason)
        completed = False
        gen = 0
        if r is not None and prefix:
            snap = _read_engine_snapshot(r, prefix)
            if snap is not None:
                gen = snap.programs_processed
                completed = snap.completion_reason is not None
        if completed:
            ok(
                "Process",
                f"{label}: PID {pid} exited (run complete at {gen}/{max_gen or '?'} programs)",
            )
        else:
            add(
                "CRITICAL",
                "Process",
                f"{label}: PID {pid} is DEAD",
                "Process is not running. Check log for traceback at end of file.",
                "Relaunch the run after fixing root cause",
            )


# ---------------------------------------------------------------------------
# Check 2: Iteration progress
# ---------------------------------------------------------------------------
def check_iteration_progress(
    r, prefix: str, max_gen: int | None, log_path: str | None = None
):
    snap = _read_engine_snapshot(r, prefix)
    gen = snap.programs_processed if snap is not None else 0

    if snap is not None and snap.completion_reason is not None:
        ok(
            "Engine",
            f"Progress {gen}/{max_gen or '?'} — COMPLETE ({snap.completion_reason})",
        )
        return gen

    if gen == 0:
        # Determine process age from log file creation time (or mtime if no log)
        # to avoid false alarms on freshly launched runs
        process_age_min = None
        if log_path and os.path.exists(log_path):
            try:
                # Use the earlier of ctime/mtime as proxy for process start
                stat = os.stat(log_path)
                start_time = min(stat.st_ctime, stat.st_mtime)
                process_age_min = (time.time() - start_time) / 60
            except OSError:
                pass

        if process_age_min is not None and process_age_min < 15:
            ok(
                "Engine",
                f"Iteration 0/{max_gen or '?'} — process started {process_age_min:.0f}min ago (initializing)",
            )
        else:
            age_str = (
                f" (process running {process_age_min:.0f}min)"
                if process_age_min is not None
                else ""
            )
            add(
                "MAJOR",
                "Engine",
                f"Iteration count is 0{age_str}",
                "Engine has not completed any iterations. Possible causes: "
                "process hung at init, Redis connection failed, "
                "or all mutations failing.",
                "Check log for startup errors. Verify Redis connectivity.",
            )
    else:
        ok("Engine", f"Iteration {gen}/{max_gen or '?'}")

    return gen


# ---------------------------------------------------------------------------
# Check 3: Iteration rate (stall detection)
# ---------------------------------------------------------------------------
def check_iteration_rate(r, prefix: str, gen: int, max_gen: int | None = None):
    # Skip stall detection for completed runs
    snap = _read_engine_snapshot(r, prefix)
    if snap is not None and snap.completion_reason is not None:
        ok(
            "Engine",
            f"Iteration rate check skipped (run complete at {gen}/{max_gen or '?'})",
        )
        return
    # Check if there's recent activity via metrics timestamps
    iter_mean = r.lrange(
        f"{prefix}:metrics:history:program_metrics:valid_iter_fitness_mean", -2, -1
    )
    if len(iter_mean) >= 2:
        try:
            t1 = json.loads(iter_mean[0])["t"]
            t2 = json.loads(iter_mean[1])["t"]
            gap = t2 - t1
            age = time.time() - t2
            if age > 7200:  # 2 hours since last metric update
                add(
                    "CRITICAL",
                    "Engine",
                    "Run appears STALLED",
                    f"Last metric update was {age / 3600:.1f}h ago (iter {gen}). "
                    f"Previous iter gap was {gap / 60:.0f}min.",
                    "Check if process is alive. Check Redis and LLM server connectivity.",
                )
            elif age > 3600:
                add(
                    "MAJOR",
                    "Engine",
                    "Run may be stalling",
                    f"Last metric update was {age / 60:.0f}min ago. "
                    f"Previous iter gap was {gap / 60:.0f}min.",
                    "Monitor — may be a slow iteration or server issue.",
                )
            else:
                ok(
                    "Engine",
                    f"Last activity {age / 60:.0f}min ago, iter gap ~{gap / 60:.0f}min",
                )
        except (json.JSONDecodeError, KeyError):
            add(
                "MINOR",
                "Engine",
                "Cannot parse metric timestamps",
                "Metric data may be corrupted",
            )
    elif gen > 0:
        add(
            "MINOR",
            "Engine",
            "Insufficient metric history for rate check",
            f"Only {len(iter_mean)} metric entries found",
        )
    # gen=0 already flagged in check_iteration_progress


# ---------------------------------------------------------------------------
# Check 4: Invalidity rate
# ---------------------------------------------------------------------------
def check_invalidity(r, prefix: str, gen: int):
    valid_count_raw = r.lrange(
        f"{prefix}:metrics:history:program_metrics:programs_valid_count", -1, -1
    )
    invalid_count_raw = r.lrange(
        f"{prefix}:metrics:history:program_metrics:programs_invalid_count", -1, -1
    )

    if not valid_count_raw and not invalid_count_raw:
        if gen > 0:
            add(
                "MINOR",
                "Engine",
                "No validity metrics found",
                "Cannot assess invalidity rate",
            )
        return

    vc = _metric_val(valid_count_raw)
    ic = _metric_val(invalid_count_raw)
    total = vc + ic
    if total == 0:
        return

    rate = ic / total
    if rate > 0.90 and gen >= 3:
        add(
            "CRITICAL",
            "Engine",
            f"Invalidity rate {rate:.0%} ({int(ic)}/{int(total)})",
            "Over 90% of programs are invalid. The run is essentially not evolving.",
            "Check: validate.py return type matches pipeline, LLM generating parseable code, "
            "stage_timeout adequate for eval function",
        )
    elif rate > 0.75 and gen >= 3:
        add(
            "MAJOR",
            "Engine",
            f"Invalidity rate {rate:.0%} ({int(ic)}/{int(total)})",
            "High invalidity — most mutations are not producing viable programs.",
            "Check mutation prompts, LLM model quality, and eval timeout",
        )
    elif rate > 0.50:
        add(
            "MINOR",
            "Engine",
            f"Invalidity rate {rate:.0%} ({int(ic)}/{int(total)})",
            "Moderate invalidity. May be acceptable depending on problem difficulty.",
        )
    else:
        ok("Engine", f"Invalidity rate {rate:.0%} ({int(ic)}/{int(total)})")


# ---------------------------------------------------------------------------
# Check 5: Fitness trajectory
# ---------------------------------------------------------------------------
def check_fitness(r, prefix: str, gen: int):
    frontier = r.lrange(
        f"{prefix}:metrics:history:program_metrics:valid_frontier_fitness", 0, -1
    )
    if not frontier:
        if gen > 0:
            add(
                "MINOR",
                "Engine",
                "No frontier fitness data",
                "Cannot assess fitness trajectory",
            )
        return

    values = []
    for entry in frontier:
        try:
            d = json.loads(entry)
            values.append((d.get("s", 0), d["v"]))
        except (json.JSONDecodeError, KeyError):
            continue

    if not values:
        return

    values.sort(key=lambda x: x[0])
    best = max(v for _, v in values)
    latest = values[-1][1]

    ok("Engine", f"Frontier fitness: best={best:.4f}, latest={latest:.4f}")

    # Check for stagnation: no improvement in last 5 entries
    if len(values) >= 5:
        last_5 = [v for _, v in values[-5:]]
        if max(last_5) == min(last_5):
            add(
                "MINOR",
                "Engine",
                "Fitness stagnation detected",
                f"No fitness improvement in last {len(last_5)} frontier updates "
                f"(all at {last_5[0]:.4f}).",
                "May be at fitness ceiling, or mutations not diverse enough.",
            )


# ---------------------------------------------------------------------------
# Check 6: Rejection rates
# ---------------------------------------------------------------------------
def check_rejections(r, prefix: str, gen: int):
    rejected_val = r.lrange(
        f"{prefix}:metrics:history:evolution_engine:rejected_validation", -1, -1
    )
    rejected_strat = r.lrange(
        f"{prefix}:metrics:history:evolution_engine:rejected_strategy", -1, -1
    )

    if not rejected_val and not rejected_strat:
        return

    rv = _metric_val(rejected_val)
    rs = _metric_val(rejected_strat)

    # Compare with valid count
    valid_raw = r.lrange(
        f"{prefix}:metrics:history:program_metrics:programs_valid_count", -1, -1
    )
    vc = _metric_val(valid_raw, default=1)

    if vc > 0 and rv / max(vc, 1) > 0.9:
        add(
            "MAJOR",
            "Engine",
            f"Validation rejection rate very high ({int(rv)} rejected vs {int(vc)} valid)",
            "Almost all programs rejected by acceptor. Check validate.py return type, "
            "required metric keys, and pipeline configuration.",
            "Verify pipeline matches validate.py (tuple return = feedback pipeline, dict = standard)",
        )

    if rs > 10 and rs > rv:
        add(
            "MINOR",
            "Engine",
            f"Strategy rejection high ({int(rs)} rejected)",
            "Programs pass validation but strategy rejects them. "
            "May need to lower significant_change config.",
        )


# ---------------------------------------------------------------------------
# Check 7: LLM server connectivity
# ---------------------------------------------------------------------------
def check_server(url: str, label: str, api_key: str = "None"):
    if not url:
        return

    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
    # Add server host to NO_PROXY
    try:
        host = url.split("//")[1].split("/")[0].split(":")[0]
        current = os.environ.get("NO_PROXY", "")
        if host not in current:
            os.environ["NO_PROXY"] = f"{current},{host}" if current else host
            os.environ["no_proxy"] = os.environ["NO_PROXY"]
    except (IndexError, ValueError):
        pass

    # Check /v1/models endpoint
    # URL may already contain /v1 (e.g. http://host:port/v1)
    base_url = url.rstrip("/")
    models_url = (
        f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
    )
    actual_model = None
    try:
        req = Request(models_url, headers={"Authorization": f"Bearer {api_key}"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            models = [d["id"] for d in data.get("data", [])]
            ok("Server", f"{label} ({url}): reachable, models={models}")
            if models:
                actual_model = models[0]
    except Exception as e:
        add(
            "CRITICAL",
            "Server",
            f"{label} ({url}): UNREACHABLE",
            f"Error: {e}",
            "Check server status, verify IP and port, check NO_PROXY settings",
        )
        return

    # Check thinking mode with a test prompt (skip if no model discovered)
    if not actual_model:
        return
    try:
        chat_url = (
            f"{base_url}/chat/completions"
            if base_url.endswith("/v1")
            else f"{base_url}/v1/chat/completions"
        )
        payload = json.dumps(
            {
                "model": actual_model,
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 50,
            }
        ).encode()
        req = Request(
            chat_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            message = data.get("choices", [{}])[0].get("message", {})
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
            if reasoning or "<think>" in content:
                ok(
                    "Server",
                    f"{label}: thinking mode active (reasoning_content={len(reasoning)} chars)",
                )
            elif "think" in str(data).lower():
                ok("Server", f"{label}: thinking mode likely active")
            else:
                add(
                    "MINOR",
                    "Server",
                    f"{label}: thinking mode may not be active",
                    "No reasoning_content or <think> tag in response. May affect mutation quality.",
                )
    except Exception as e:
        add(
            "MINOR",
            "Server",
            f"{label}: chat completions test failed: {e}",
            "Server reachable but chat endpoint may have issues",
        )


# ---------------------------------------------------------------------------
# Check 8: Redis health
# ---------------------------------------------------------------------------
def check_redis(r, db: int):
    try:
        r.ping()
        ok("Redis", f"DB {db}: connected and responsive")
    except Exception as e:
        add(
            "CRITICAL",
            "Redis",
            f"DB {db}: connection failed",
            f"Error: {e}",
            "Check redis-cli ping, check Redis server status",
        )
        return

    # Check DB size
    size = r.dbsize()
    if size == 0:
        add(
            "CRITICAL",
            "Redis",
            f"DB {db}: EMPTY (0 keys)",
            "Database has no data. Run may not have started, or wrong DB number.",
            "Verify the correct DB number for this run",
        )
    elif size < 10:
        add(
            "MAJOR",
            "Redis",
            f"DB {db}: very few keys ({size})",
            "Database has minimal data. Run may have just started or failed early.",
        )
    else:
        ok("Redis", f"DB {db}: {size} keys")


# ---------------------------------------------------------------------------
# Check 9: Log analysis
# ---------------------------------------------------------------------------
def check_log(log_path: str, run_complete: bool = False):
    if not log_path or not os.path.exists(log_path):
        add(
            "MINOR",
            "Log",
            "Log file not found or not specified",
            f"Path: {log_path or '(none)'}",
            "Provide --log <path> for log analysis",
        )
        return

    try:
        # Read last 500 lines
        with open(log_path) as f:
            lines = f.readlines()

        total_lines = len(lines)
        tail = lines[-500:] if len(lines) > 500 else lines
        tail_text = "".join(tail)

        ok("Log", f"{log_path}: {total_lines} lines")

        # Check for crashes (traceback at end of file)
        last_50 = "".join(lines[-50:]) if len(lines) >= 50 else "".join(lines)
        if "Traceback (most recent call last)" in last_50:
            # Extract the last traceback
            tb_start = last_50.rfind("Traceback (most recent call last)")
            tb_text = last_50[tb_start:][:500]
            add(
                "CRITICAL",
                "Log",
                "Traceback at end of log — process likely crashed",
                f"Last traceback:\n{tb_text}",
                "Fix the error and relaunch",
            )

        # Count error patterns
        patterns = {
            "step() timed out": ("MAJOR", "Engine step timeout"),
            "step() failed": ("MAJOR", "Engine step failure"),
            "TIMED OUT after": ("MINOR", "Stage timeout"),
            "DEADLOCK": ("CRITICAL", "DAG deadlock"),
            "STALLED": ("MAJOR", "DAG stall"),
            "Structured LLM call failed": ("MAJOR", "LLM call failure"),
            "Failed to extract code": ("MINOR", "Empty LLM response"),
            "ConnectionError": ("MAJOR", "Connection error"),
            "StorageError": ("MAJOR", "Redis storage error"),
            "rejected by acceptor": ("MINOR", "Acceptor rejection"),
            "SecurityViolationError": ("MINOR", "Security violation"),
            "SyntaxError": ("MINOR", "Syntax error in generated code"),
            "TimeoutError": ("MINOR", "Timeout"),
            "RateLimitError": ("MAJOR", "LLM rate limiting"),
            "OOM": ("CRITICAL", "Out of memory"),
            "Killed": ("CRITICAL", "Process killed"),
        }

        for pattern, (severity, desc) in patterns.items():
            count = tail_text.count(pattern)
            if count > 0:
                # Escalate if very frequent
                if count > 50 and severity == "MINOR":
                    severity = "MAJOR"
                if count > 100 and severity == "MAJOR":
                    severity = "CRITICAL"
                add(
                    severity,
                    "Log",
                    f"{desc}: {count} occurrences in last {len(tail)} lines",
                    f"Pattern: '{pattern}'",
                )

        # Check for no recent output (process may be hung)
        if total_lines > 0:
            # Try to extract timestamp from last line
            last_line = lines[-1].strip()
            if not last_line and len(lines) > 1:
                last_line = lines[-2].strip()

            # Check file modification time (skip for completed runs)
            mtime = os.path.getmtime(log_path)
            age = time.time() - mtime
            if run_complete:
                ok(
                    "Log",
                    f"Log file last modified {age / 60:.0f}min ago (run complete)",
                )
            elif age > 3600:
                add(
                    "MAJOR",
                    "Log",
                    f"Log file not updated for {age / 3600:.1f}h",
                    f"Last modified: {time.ctime(mtime)}",
                    "Process may be hung or dead. Check PID.",
                )
            elif age > 1800:
                add(
                    "MINOR",
                    "Log",
                    f"Log file not updated for {age / 60:.0f}min",
                    f"Last modified: {time.ctime(mtime)}",
                )

    except Exception as e:
        add("MINOR", "Log", f"Error reading log: {e}", str(e))


# ---------------------------------------------------------------------------
# Check 10: DAG runner metrics
# ---------------------------------------------------------------------------
def check_dag_metrics(r, prefix: str):
    # Check for DAG timeout/error metrics
    timeout_key = f"{prefix}:metrics:history:dag_runner:dag_timeouts"
    error_key = f"{prefix}:metrics:history:dag_runner:dag_errors"

    timeouts = r.lrange(timeout_key, -1, -1)
    errors = r.lrange(error_key, -1, -1)

    if timeouts:
        try:
            tv = json.loads(timeouts[0]).get("v")
            if tv is not None and tv > 0:
                add(
                    "MAJOR",
                    "DAG",
                    f"DAG timeouts: {int(tv)}",
                    "Programs are exceeding dag_timeout. Their evaluations are being discarded.",
                    "Increase dag_timeout or reduce problem complexity",
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    if errors:
        try:
            ev = json.loads(errors[0]).get("v")
            if ev is not None and ev > 0:
                add(
                    "MAJOR",
                    "DAG",
                    f"DAG errors: {int(ev)}",
                    "DAG executions failing with exceptions.",
                    "Check logs for DAG error tracebacks",
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Check stage-level failures
    stage_keys = r.keys(
        f"{prefix}:metrics:history:dag_runner:dag:internals:*:stage_failure"
    )
    for sk in stage_keys:
        stage_name = sk.decode().split(":")[-2]
        failures = r.lrange(sk, -1, -1)
        if failures:
            try:
                fv = json.loads(failures[0]).get("v")
                if fv is not None and fv > 5:
                    add(
                        "MINOR",
                        "DAG",
                        f"Stage '{stage_name}' has {int(fv)} failures",
                        "Check if this stage has systematic issues",
                    )
            except (json.JSONDecodeError, KeyError):
                pass


# ---------------------------------------------------------------------------
# Check 11: Config coherence (Hydra composition + task match)
# ---------------------------------------------------------------------------

# Known pipeline <-> problem mappings.  Key = pipeline name, value = list of
# allowed problem prefixes (substring match on problem_name / prefix).
PIPELINE_TASK_MAP = {
    "hotpotqa_asi": ["hotpotqa"],
    "hotpotqa_colbert": ["hotpotqa"],
    "hotpotqa_reflective": ["hotpotqa"],
    "hover_feedback": ["hover"],
    "standard": None,  # Any task
    "with_context": None,  # Any task
    "auto": None,  # Any task
    "cma_opt": None,
    "optuna_opt": None,
}

# Pipeline <-> validate.py return type.
# True  = must return tuple (metrics, failures)
# False = must return dict
PIPELINE_TUPLE_RETURN = {
    "hotpotqa_asi": True,
    "hotpotqa_colbert": True,
    "hotpotqa_reflective": True,
    "hover_feedback": True,
    "standard": False,
    "with_context": False,
    "auto": False,
    "cma_opt": False,
    "optuna_opt": False,
}

# Known formatter <-> pipeline.  If the pipeline specifies one of these
# PipelineBuilder _target_ paths, the formatter is task-locked.
BUILDER_TASK_MAP = {
    "problems.chains.hotpotqa.static_a.pipeline.ASIPipelineBuilder": "hotpotqa",
    "problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder": "hotpotqa",
    "problems.chains.hover.static.pipeline.HoVerFeedbackPipelineBuilder": "hover",
}


def check_config_coherence(
    cfg_file: str | None,
    pipeline: str | None,
    problem_dir: str | None,
    prefix: str | None,
    has_experiment: bool = False,
):
    """Cross-check Hydra-composed config for task-specific mismatches."""

    # ------------------------------------------------------------------
    # A) Static checks (no cfg file needed)
    # ------------------------------------------------------------------

    # A1: Pipeline <-> task prefix mismatch
    if pipeline and prefix:
        allowed = PIPELINE_TASK_MAP.get(pipeline)
        if allowed is not None:
            if not any(tok in prefix for tok in allowed):
                add(
                    "CRITICAL",
                    "Config",
                    f"Pipeline '{pipeline}' is for {allowed} but prefix is '{prefix}'",
                    "The pipeline's formatter and acceptor stages are task-locked. "
                    "Using them with a different task's validate.py will crash or silently corrupt metrics.",
                    "Use the correct pipeline for this task (check config/pipeline/*.yaml)",
                )

    # A2: Validate.py return type vs pipeline
    if pipeline and problem_dir:
        validate_path = Path(problem_dir) / "validate.py"
        if validate_path.exists():
            try:
                source = validate_path.read_text()
                has_tuple_return = bool(
                    re.search(r"return\s+\(?\s*metrics\s*,\s*failures", source)
                    or re.search(r"return\s+metrics\s*,\s*\[", source)
                    or re.search(r"-> tuple", source)
                )
                expects_tuple = PIPELINE_TUPLE_RETURN.get(pipeline)
                if expects_tuple is True and not has_tuple_return:
                    add(
                        "MAJOR",
                        "Config",
                        f"Pipeline '{pipeline}' expects tuple return but validate.py may return dict",
                        "If validate.py returns only a dict, the feedback formatter will receive None "
                        "as failures and produce empty feedback.",
                        "Check validate.py return statement; should be (metrics, failures_list)",
                    )
                elif expects_tuple is False and has_tuple_return:
                    add(
                        "CRITICAL",
                        "Config",
                        f"Pipeline '{pipeline}' expects dict return but validate.py returns tuple",
                        "standard pipeline calls repr() on the full return — repr-contamination bug (PR #67).",
                        "Use a feedback pipeline (hover_feedback / hotpotqa_asi) for tuple-returning validate.py",
                    )
            except Exception:
                pass  # Can't read validate.py — not fatal for diagnostics

    # A3: Check formatter.py exists if feedback pipeline
    if (
        pipeline
        and problem_dir
        and pipeline in ("hover_feedback", "hotpotqa_asi", "hotpotqa_colbert")
    ):
        formatter_path = Path(problem_dir) / "formatter.py"
        if not formatter_path.exists():
            add(
                "CRITICAL",
                "Config",
                f"Feedback pipeline '{pipeline}' requires formatter.py but not found at {formatter_path}",
                "The custom PipelineBuilder references a formatter class that must live in the problem dir.",
                "Create formatter.py with the appropriate FormatterStage subclass",
            )
        else:
            ok("Config", f"formatter.py found at {problem_dir}")

    # A4: Check pipeline builder _target_ is importable
    if pipeline:
        pipeline_yaml_path = Path("config/pipeline") / f"{pipeline}.yaml"
        if pipeline_yaml_path.exists():
            try:
                import yaml

                with open(pipeline_yaml_path) as _f:
                    pipeline_cfg = yaml.safe_load(_f)
                # Extract _target_ from pipeline_builder block
                builder_target = None
                pb = pipeline_cfg.get("pipeline_builder", {})
                if isinstance(pb, dict):
                    builder_target = pb.get("_target_")
                if builder_target:
                    # Try to import the module containing the class
                    module_path = builder_target.rsplit(".", 1)[0]
                    try:
                        __import__(module_path)
                        ok(
                            "Config",
                            f"Pipeline '{pipeline}' builder '{builder_target}' is importable",
                        )
                    except ImportError as _ie:
                        add(
                            "MAJOR",
                            "Config",
                            f"Pipeline '{pipeline}' builder not importable: {builder_target}",
                            f"ImportError: {_ie}",
                            "Check that the module exists and is on PYTHONPATH",
                        )
            except Exception:
                pass  # Can't parse pipeline YAML — not fatal

    # ------------------------------------------------------------------
    # B) Hydra cfg file analysis (if provided)
    # ------------------------------------------------------------------
    if not cfg_file:
        if not has_experiment:
            # Only warn when no experiment.yaml treatment_checks are available
            add(
                "MINOR",
                "Config",
                "No --cfg-file provided",
                "Cannot verify Hydra composition. Provide cfg_run_<label>.txt for deeper checks.",
                "Run: python run.py <overrides> --cfg job > cfg_run_<label>.txt 2>&1",
            )
        return

    cfg_path = Path(cfg_file)
    if not cfg_path.exists():
        add(
            "MINOR",
            "Config",
            f"Config file not found: {cfg_file}",
            "File may not have been saved at launch time.",
        )
        return

    try:
        cfg_text = cfg_path.read_text()
    except Exception as e:
        add("MINOR", "Config", f"Cannot read config file: {e}", "")
        return

    ok("Config", f"Hydra config loaded from {cfg_file} ({len(cfg_text)} chars)")

    # B1: Check pipeline_builder._target_ matches task
    builder_targets = re.findall(r"_target_:\s*(\S+Pipeline\S*)", cfg_text)
    for bt in builder_targets:
        expected_task = BUILDER_TASK_MAP.get(bt)
        if expected_task and prefix and expected_task not in prefix:
            add(
                "CRITICAL",
                "Config",
                f"PipelineBuilder '{bt}' is for '{expected_task}' but run prefix is '{prefix}'",
                "The Hydra config composed a pipeline builder for a different task. "
                "This means formatter, acceptor chain, and DAG stages are all wrong for this problem.",
                "Fix the pipeline= override or problem.name= override",
            )

    # B2: Check prompts_dir in resolved config
    prompts_match = re.search(r"prompts_dir:\s*(\S+)", cfg_text)
    if prompts_match:
        prompts_dir_val = prompts_match.group(1)
        if prompts_dir_val == "null" or prompts_dir_val == "None":
            ok("Config", "prompts_dir=null (using package default prompts)")
        elif prompts_dir_val.startswith("${"):
            ok(
                "Config",
                f"prompts_dir={prompts_dir_val} (Hydra interpolation — resolved at runtime)",
            )
        elif prompts_dir_val != "???":
            # Check if prompts_dir exists
            pd = Path(prompts_dir_val)
            if not pd.exists():
                add(
                    "CRITICAL",
                    "Config",
                    f"prompts_dir path does not exist: {prompts_dir_val}",
                    "Prompt loading will fail at runtime.",
                    "Check prompts= override or the Hydra config group",
                )
            else:
                # Check for task mismatch in prompts_dir
                if prefix:
                    # E.g., prompts/hotpotqa used with hover prefix
                    task_dirs = ["hotpotqa", "hover", "gsm8k", "aime", "ifbench"]
                    for td in task_dirs:
                        if td in prompts_dir_val and td not in prefix:
                            add(
                                "MAJOR",
                                "Config",
                                f"prompts_dir '{prompts_dir_val}' is for '{td}' but prefix is '{prefix}'",
                                "Task-specific prompts designed for one benchmark may confuse the LLM "
                                "when used with a different task.",
                                "Use prompts=default or the correct task-specific prompts config",
                            )
                            break
                    else:
                        ok("Config", f"prompts_dir={prompts_dir_val}")
    else:
        add(
            "MINOR",
            "Config",
            "prompts_dir not found in config",
            "May be using defaults. Check if this is intentional.",
        )

    # B3: Check model_name consistency
    model_matches = re.findall(r"model_name:\s*(\S+)", cfg_text)
    if model_matches:
        ok("Config", f"Model(s) in config: {', '.join(set(model_matches))}")

    # B4: Check redis.db matches --db
    db_match = re.search(r"redis:\s*\n\s*db:\s*(\d+)", cfg_text)
    if not db_match:
        db_match = re.search(r"db:\s*(\d+)", cfg_text)
    if db_match:
        cfg_db = int(db_match.group(1))
        if cfg_db != int(str(prefix).split("@")[0] if "@" in str(prefix) else "0"):
            # Just informational — the --db arg is authoritative
            ok("Config", f"Redis DB in config: {cfg_db}")

    # B5: Check stage_timeout and dag_timeout
    stage_to = re.search(r"stage_timeout:\s*(\d+)", cfg_text)
    dag_to = re.search(r"dag_timeout:\s*(\d+)", cfg_text)
    if stage_to:
        st = int(stage_to.group(1))
        if st > 5000:
            add(
                "MINOR",
                "Config",
                f"stage_timeout={st}s is very high",
                "Programs that fail will waste up to this much time per stage.",
                "Consider 1000-3000s for most problems",
            )
        elif st < 60:
            add(
                "MINOR",
                "Config",
                f"stage_timeout={st}s may be too low",
                "Complex eval functions may legitimately need more time.",
            )
        else:
            ok("Config", f"stage_timeout={st}s")
    if dag_to:
        dt = int(dag_to.group(1))
        ok("Config", f"dag_timeout={dt}s")

    # B6: Check mutation_mode
    mm_match = re.search(r"mutation_mode:\s*(\S+)", cfg_text)
    if mm_match:
        ok("Config", f"mutation_mode={mm_match.group(1)}")

    # B7: Check problem.dir resolved correctly
    pd_match = re.search(r"problem:\s*\n\s*(?:.*\n)*?\s*dir:\s*(\S+)", cfg_text)
    if pd_match:
        resolved_dir = pd_match.group(1)
        if resolved_dir.startswith("${"):
            ok(
                "Config",
                f"problem.dir={resolved_dir} (Hydra interpolation — resolved at runtime)",
            )
        elif not Path(resolved_dir).exists():
            add(
                "CRITICAL",
                "Config",
                f"problem.dir does not exist: {resolved_dir}",
                "Hydra resolved an invalid problem directory.",
                "Check problem.name= override",
            )
        else:
            ok("Config", f"problem.dir={resolved_dir}")


# ---------------------------------------------------------------------------
# Check 12: Override verification (general — works for ANY experiment)
# ---------------------------------------------------------------------------
def _is_hydra_config_group(key: str) -> bool:
    """Check if a non-dotted key is a Hydra config group (has a directory under config/)."""
    # Strip leading '+' or '~' (Hydra append/delete syntax)
    clean_key = key.lstrip("+~")
    config_dir = Path("config") / clean_key
    return config_dir.is_dir()


def check_overrides_in_config(cfg_file: str | None, extra_overrides: list[str] | None):
    """Verify that extra_overrides from experiment.yaml appear in resolved Hydra cfg.

    For each override like 'prompt_fetcher.prompt_prefix=prompt_evolution_hover',
    extract the leaf key ('prompt_prefix') and value ('prompt_evolution_hover'),
    then check that key: value appears in the cfg dump.

    Non-dotted overrides are classified as either:
    - Config group selectors (if config/<key>/ directory exists) — verified by
      checking the group section exists in the cfg dump
    - Leaf key overrides (if no config group directory) — verified by checking
      key: value in the cfg dump, same as dotted overrides

    This is a general check — it works for ANY experiment with extra_overrides.
    """
    if not extra_overrides or not cfg_file:
        return

    cfg_path = Path(cfg_file)
    if not cfg_path.exists():
        add(
            "MINOR",
            "Config",
            "Cannot verify overrides: cfg file not found",
            f"Expected {cfg_file}",
            "Generate cfg dump with: python run.py [overrides] --cfg job",
        )
        return

    cfg_text = cfg_path.read_text()

    for override in extra_overrides:
        # Parse key=value (skip --cfg, --help, etc.)
        if "=" not in override:
            continue

        key, value = override.split("=", 1)

        # Config group selectors (e.g. 'prompt_fetcher=coevolved') have a
        # directory under config/. They resolve to _target_ classes in the cfg
        # dump, not the literal value. We verify the group section exists.
        #
        # Non-dotted overrides WITHOUT a config group directory (e.g.
        # 'max_mutants=8') are plain leaf-key overrides — verify
        # them the same way as dotted overrides.
        if "." not in key and _is_hydra_config_group(key):
            clean_key = key.lstrip("+~")
            group_pattern = rf"^{re.escape(clean_key)}:\s*$"
            if re.search(group_pattern, cfg_text, re.MULTILINE):
                ok(
                    "Config",
                    f"Override verified (config group): {override} "
                    f"('{clean_key}' section present in cfg)",
                )
            else:
                add(
                    "MAJOR",
                    "Config",
                    f"Config group override may not be applied: {override}",
                    f"No '{clean_key}:' section found in cfg dump. "
                    f"The config group '{value}' may not have been selected.",
                    f"Check that config/{clean_key}/{value}.yaml exists",
                )
            continue

        # Leaf key override (dotted like 'prompt_fetcher.prompt_prefix=X'
        # or plain like 'max_mutants=8')
        leaf_key = key.rsplit(".", 1)[-1]

        # Search for leaf_key: value in YAML cfg dump
        patterns = [
            rf"{re.escape(leaf_key)}:\s*{re.escape(value)}\b",
            rf"{re.escape(leaf_key)}:\s*'{re.escape(value)}'",
            rf'{re.escape(leaf_key)}:\s*"{re.escape(value)}"',
        ]

        found = any(re.search(p, cfg_text) for p in patterns)

        if found:
            ok("Config", f"Override verified: {override}")
        else:
            # Check if the key exists at all (different value vs missing entirely)
            key_match = re.search(rf"{re.escape(leaf_key)}:\s*(\S+)", cfg_text)
            if key_match:
                actual_value = key_match.group(1).strip("'\"")
                add(
                    "CRITICAL",
                    "Config",
                    f"Override NOT applied: {override}",
                    f"Cfg dump shows {leaf_key}: {actual_value} "
                    f"(expected {value}). The override was ignored by Hydra.",
                    f"Check that the override key '{key}' is valid in the "
                    f"Hydra config schema",
                )
            else:
                add(
                    "CRITICAL",
                    "Config",
                    f"Override key missing from config: {override}",
                    f"Key '{leaf_key}' not found in cfg dump at all. "
                    f"The Hydra config group may not recognize this key.",
                    f"Verify the config group for '{key}' exists and accepts "
                    f"this parameter",
                )


# ---------------------------------------------------------------------------
# Check 13: Declarative treatment verification
# ---------------------------------------------------------------------------
def check_treatment_declarative(
    run_label: str,
    run_db: int,
    run_prefix: str,
    gen: int,
    log_path: str | None,
    treatment_checks: list[dict],
    runs_by_label: dict,
):
    """Execute declarative treatment checks from experiment.yaml.

    Each check is a dict with: name, type, severity, after_gen, and
    type-specific fields. Supported types:

    - redis_key_pattern: Check KEYS pattern has >= min_count matches
    - redis_key_count:   Check HLEN of a hash key
    - log_pattern_absent: Check pattern does NOT appear in log after after_gen
    - log_pattern_present: Check pattern DOES appear in log
    - fitness_uniformity: Check frontier fitness isn't stuck at one value
    """
    import redis as redis_lib

    if not treatment_checks:
        return

    for check in treatment_checks:
        name = check.get("name", "unnamed")
        check_type = check.get("type")
        severity = check.get("severity", "MAJOR")
        after_gen = check.get("after_gen", 0)
        rationale = check.get("rationale", "")

        # Determine which run this check applies to
        check_label = check.get("run_ref", run_label)
        if check_label != run_label:
            continue  # This check is for a different run

        if gen < after_gen:
            continue  # Too early to check

        # Resolve DB — check may reference another run's DB
        db_ref = check.get("db_ref")
        if db_ref and db_ref != run_label:
            ref_run = runs_by_label.get(db_ref)
            if not ref_run:
                continue
            check_db = ref_run["db"]
            check_prefix = ref_run["prefix"]
        else:
            check_db = run_db
            check_prefix = run_prefix

        r = redis_lib.Redis(host="localhost", port=6379, db=check_db)

        # Resolve {prefix} placeholder in patterns
        pattern = check.get("pattern", "")
        pattern = pattern.replace("{prefix}", check_prefix)

        if check_type == "redis_key_pattern":
            min_count = check.get("min_count", 1)
            keys = r.keys(pattern)
            if len(keys) < min_count:
                add(
                    severity,
                    "Treatment",
                    name,
                    f"Expected >= {min_count} keys matching '{pattern}' "
                    f"in DB {check_db}, found {len(keys)}. {rationale}",
                )
            else:
                ok(
                    "Treatment",
                    f"{name}: {len(keys)} keys match '{pattern}' in DB {check_db}",
                )

        elif check_type == "redis_key_count":
            key = check.get("key", "").replace("{prefix}", check_prefix)
            min_count = check.get("min_count", 1)
            count = r.hlen(key)
            if count < min_count:
                add(
                    severity,
                    "Treatment",
                    name,
                    f"Expected HLEN('{key}') >= {min_count} in DB {check_db}, "
                    f"got {count}. {rationale}",
                )
            else:
                ok("Treatment", f"{name}: HLEN('{key}') = {count} in DB {check_db}")

        elif check_type == "log_pattern_absent":
            if not log_path or not os.path.exists(log_path):
                continue
            try:
                log_text = Path(log_path).read_text()
                # Pattern may be pipe-separated alternatives
                parts = [p.strip() for p in pattern.split("|")]
                total = sum(log_text.count(p) for p in parts)
                if total > 0:
                    add(
                        severity,
                        "Treatment",
                        name,
                        f"Found {total} occurrences of forbidden pattern "
                        f"in log. {rationale}",
                    )
                else:
                    ok("Treatment", f"{name}: no forbidden patterns in log")
            except Exception:
                pass

        elif check_type == "log_pattern_present":
            if not log_path or not os.path.exists(log_path):
                continue
            try:
                log_text = Path(log_path).read_text()
                parts = [p.strip() for p in pattern.split("|")]
                total = sum(log_text.count(p) for p in parts)
                if total == 0:
                    add(
                        severity,
                        "Treatment",
                        name,
                        f"Expected pattern not found in log. {rationale}",
                    )
                else:
                    ok("Treatment", f"{name}: pattern found {total} times in log")
            except Exception:
                pass

        elif check_type == "fitness_uniformity":
            metric_key = check.get(
                "metric_key",
                f"{check_prefix}:metrics:history:program_metrics:valid_frontier_fitness",
            )
            metric_key = metric_key.replace("{prefix}", check_prefix)
            frontier = r.lrange(metric_key, 0, -1)
            if not frontier:
                continue
            values = set()
            for entry in frontier:
                try:
                    v = json.loads(entry)["v"]
                    if v is not None:
                        values.add(round(v, 6))
                except (json.JSONDecodeError, KeyError):
                    continue
            if len(values) == 1:
                sole_value = values.pop()
                stuck_value = check.get("stuck_value")
                if stuck_value is not None and abs(sole_value - stuck_value) < 0.001:
                    add(
                        severity,
                        "Treatment",
                        name,
                        f"Fitness stuck at {sole_value:.4f} (expected stuck value "
                        f"{stuck_value}) across {len(frontier)} entries. {rationale}",
                    )
                else:
                    add(
                        "MAJOR",
                        "Treatment",
                        name,
                        f"Fitness uniform at {sole_value:.4f} across "
                        f"{len(frontier)} entries. {rationale}",
                    )
            elif len(values) <= 2 and gen >= 10:
                add(
                    "MINOR",
                    "Treatment",
                    f"{name}: low diversity",
                    f"{len(values)} distinct values in {len(frontier)} entries. "
                    f"{rationale}",
                )
            else:
                ok(
                    "Treatment",
                    f"{name}: {len(values)} distinct values in {len(frontier)} entries",
                )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def report():
    print(f"\n{'=' * 70}")
    print("  DIAGNOSTIC REPORT")
    print(f"{'=' * 70}\n")

    # Group by layer
    layers = [
        "Process",
        "Engine",
        "DAG",
        "Server",
        "Redis",
        "Log",
        "Config",
        "Treatment",
    ]
    for layer in layers:
        layer_findings = [f for f in findings if f.layer == layer]
        if not layer_findings:
            continue

        print(f"  --- {layer} ---")
        for f in layer_findings:
            print(f)
        print()

    # Summary
    criticals = [f for f in findings if f.severity == "CRITICAL"]
    majors = [f for f in findings if f.severity == "MAJOR"]
    minors = [f for f in findings if f.severity == "MINOR"]
    infos = [f for f in findings if f.severity == "INFO"]

    print(f"{'=' * 70}")
    print(
        f"  Summary: {len(infos)} OK, {len(minors)} MINOR, {len(majors)} MAJOR, {len(criticals)} CRITICAL"
    )

    if criticals:
        print(
            f"\n  ACTION REQUIRED: {len(criticals)} critical issue(s) need immediate attention."
        )
        return 2
    elif majors:
        print(
            f"\n  WARNING: {len(majors)} major issue(s) found. Review before continuing."
        )
        return 1
    else:
        print("\n  Run appears healthy.")
        return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _diagnose_one_run(
    *,
    db: int,
    prefix: str,
    label: str,
    pid: int | None,
    log: str | None,
    chain_url: str | None,
    mutation_url: str | None,
    max_gen: int | None,
    cfg_file: str | None,
    pipeline: str | None,
    problem_dir: str | None,
    extra_overrides: list[str] | None,
    experiment: str | None,
    api_key: str = "None",
) -> int:
    """Run all diagnostic checks for a single run. Returns exit code."""
    global findings
    findings = []  # Reset for each run

    import redis as redis_lib

    r = redis_lib.Redis(host="localhost", port=6379, db=db)

    print(f"Diagnosing {label} (db={db}, prefix={prefix})")
    print(f"{'=' * 70}")

    # Determine if run is complete (engine set completion_reason)
    _snap = _read_engine_snapshot(r, prefix)
    run_complete = _snap is not None and _snap.completion_reason is not None

    # Run all checks
    check_process(pid, label, r=r, prefix=prefix, max_gen=max_gen)
    check_redis(r, db)
    gen = check_iteration_progress(r, prefix, max_gen, log_path=log)
    check_iteration_rate(r, prefix, gen, max_gen=max_gen)
    check_invalidity(r, prefix, gen)
    check_fitness(r, prefix, gen)
    check_rejections(r, prefix, gen)
    check_dag_metrics(r, prefix)
    check_server(chain_url, "chain", api_key=api_key)
    check_server(mutation_url, "mutation", api_key=api_key)
    check_log(log, run_complete=run_complete)
    check_config_coherence(
        cfg_file,
        pipeline,
        problem_dir,
        prefix,
        has_experiment=bool(experiment),
    )
    check_overrides_in_config(cfg_file, extra_overrides)

    # Check 13: Declarative treatment checks from experiment.yaml
    treatment_checks = []
    runs_by_label = {}
    if experiment:
        import yaml

        exp_yaml_path = Path(f"experiments/{experiment}/experiment.yaml")
        if exp_yaml_path.exists():
            with open(exp_yaml_path) as f:
                exp_data = yaml.safe_load(f)
            raw_checks = exp_data.get("treatment_checks", [])
            # Normalize old dict format {log_pattern_present: [...], ...}
            # into new list-of-dicts format [{type: ..., name: ...}, ...]
            if isinstance(raw_checks, dict):
                treatment_checks = []
                for pattern in raw_checks.get("log_pattern_present", []):
                    treatment_checks.append(
                        {
                            "type": "log_pattern_present",
                            "name": f"log_present: {pattern[:40]}",
                            "pattern": pattern,
                            "severity": "MAJOR",
                        }
                    )
                for pattern in raw_checks.get("log_pattern_absent", []):
                    treatment_checks.append(
                        {
                            "type": "log_pattern_absent",
                            "name": f"log_absent: {pattern[:40]}",
                            "pattern": pattern,
                            "severity": "MAJOR",
                        }
                    )
                for pattern in raw_checks.get("redis_key_pattern", []):
                    treatment_checks.append(
                        {
                            "type": "redis_key_pattern",
                            "name": f"redis_key: {pattern[:40]}",
                            "pattern": pattern,
                            "severity": "MAJOR",
                        }
                    )
            else:
                treatment_checks = raw_checks
            for run_spec in exp_data.get("runs", []):
                runs_by_label[run_spec["label"]] = {
                    "db": run_spec["db"],
                    "prefix": run_spec["prefix"],
                }

    check_treatment_declarative(
        label,
        db,
        prefix,
        gen,
        log,
        treatment_checks,
        runs_by_label,
    )

    return report()


def main():
    parser = argparse.ArgumentParser(description="Diagnose a GigaEvo experiment run")
    parser.add_argument("--db", type=int, help="Redis DB number")
    parser.add_argument("--prefix", help="Redis key prefix (e.g. chains/hover/static)")
    parser.add_argument("--pid", type=int, help="Process PID to check")
    parser.add_argument("--log", help="Path to run log file")
    parser.add_argument("--chain-url", help="Chain LLM server URL")
    parser.add_argument("--mutation-url", help="Mutation LLM server URL")
    parser.add_argument(
        "--max-gen", type=int, help="Expected iteration cap (manifest max_generations)"
    )
    parser.add_argument("--label", default="run", help="Run label for display")
    parser.add_argument(
        "--cfg-file", help="Path to cfg_run_<label>.txt (Hydra --cfg job output)"
    )
    parser.add_argument(
        "--pipeline", help="Pipeline name (e.g. hover_feedback, standard)"
    )
    parser.add_argument(
        "--problem-dir", help="Path to problem dir (e.g. problems/chains/hover/static)"
    )
    parser.add_argument(
        "--extra-overrides",
        nargs="*",
        help="Extra Hydra overrides from experiment.yaml (e.g. prompt_fetcher=coevolved prompt_fetcher.prompt_redis_db=11)",
    )
    parser.add_argument(
        "--experiment",
        help="Experiment path (e.g. hover/dynamic-topology). "
        "When used alone (without --db/--prefix), auto-discovers all runs "
        "from experiment.yaml and diagnoses each one.",
    )
    args = parser.parse_args()

    # Auto-discover mode: --experiment without --db/--prefix
    if args.experiment and args.db is None and args.prefix is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
        from gigaevo.experiment.manifest import load_manifest

        m = load_manifest(args.experiment)
        api_key = (m.contract.custom_env or {}).get("OPENAI_API_KEY", "None")
        worst_exit = 0
        for run in m.contract.runs:
            exp_dir = f"experiments/{args.experiment}"
            log_path = f"{exp_dir}/run_{run.label}.log"
            cfg_path = f"{exp_dir}/cfg_run_{run.label}.txt"
            exit_code = _diagnose_one_run(
                db=run.db,
                prefix=run.prefix,
                label=run.label,
                pid=run.pid,
                log=log_path if Path(log_path).exists() else None,
                chain_url=run.chain_url,
                mutation_url=run.mutation_url,
                max_gen=m.contract.max_generations,
                cfg_file=cfg_path if Path(cfg_path).exists() else None,
                pipeline=run.pipeline,
                problem_dir=f"problems/{run.problem_name}",
                extra_overrides=run.extra_overrides,
                experiment=args.experiment,
                api_key=api_key,
            )
            worst_exit = max(worst_exit, exit_code)
            print()
        sys.exit(worst_exit)

    # Single-run mode: --db and --prefix required
    if args.db is None or args.prefix is None:
        parser.error("--db and --prefix are required (or use --experiment alone)")

    exit_code = _diagnose_one_run(
        db=args.db,
        prefix=args.prefix,
        label=args.label,
        pid=args.pid,
        log=args.log,
        chain_url=args.chain_url,
        mutation_url=args.mutation_url,
        max_gen=args.max_gen,
        cfg_file=args.cfg_file,
        pipeline=args.pipeline,
        problem_dir=args.problem_dir,
        extra_overrides=args.extra_overrides,
        experiment=args.experiment,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
