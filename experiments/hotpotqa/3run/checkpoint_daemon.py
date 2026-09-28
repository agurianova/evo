#!/usr/bin/env python3
"""
Checkpoint daemon for the 3-run HotpotQA evolution experiment.

Polls generation counts every 10 minutes. At generations 10, 20, 30, 50:
  1. Extracts top-3 programs from each run
  2. Generates fitness comparison plot
  3. Evaluates best program on test set (gen >= 20 only)
  4. Posts a formatted checkpoint report to GitHub PR #65

Usage:
    nohup python experiments/hotpotqa_3run/checkpoint_daemon.py > \
        experiments/hotpotqa_3run/checkpoint_daemon.log 2>&1 &
"""

from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
import sys
import time

# Ensure project root is on path
PROJ = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJ))

PYTHON = os.environ.get("GIGAEVO_PYTHON", sys.executable)
PR_NUMBER = "65"
CHECKPOINTS = [10, 20, 30, 50]
POLL_INTERVAL = 600  # 10 minutes

RUNS = [
    {
        "label": "A",
        "db": 10,
        "pid": 1512530,
        "log": PROJ / "experiments/hotpotqa_3run/run_a.log",
        "top_dir": PROJ / "experiments/hotpotqa_3run/top_programs_a",
        "seed_em": 42.3,
        "desc": "control (8 mut/gen)",
    },
    {
        "label": "B",
        "db": 11,
        "pid": 1415664,
        "log": PROJ / "experiments/hotpotqa_3run/run_b.log",
        "top_dir": PROJ / "experiments/hotpotqa_3run/top_programs_b",
        "seed_em": 42.3,
        "desc": "high budget (16 mut/gen)",
    },
    {
        "label": "C",
        "db": 12,
        "pid": 1418523,
        "log": PROJ / "experiments/hotpotqa_3run/run_c.log",
        "top_dir": PROJ / "experiments/hotpotqa_3run/top_programs_c",
        "seed_em": 56.3,
        "desc": "warm-start 56% (8 mut/gen)",
    },
]

PLOTS_DIR = PROJ / "experiments/hotpotqa_3run/plots"
REPORTS_DIR = PROJ / "experiments/hotpotqa_3run/reports"

# Track which checkpoints have been reported per run
_reported: dict[str, set[int]] = {"A": set(), "B": set(), "C": set()}
_reported_combined: set[int] = set()  # for combined reports


def log(msg: str):
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{ts}] {msg}", flush=True)


def get_generation(log_path: Path) -> int:
    """Count 'Phase 1: Idle confirmed' lines minus 1 (first is gen 0)."""
    try:
        count = int(
            subprocess.check_output(
                ["grep", "-c", "Phase 1: Idle confirmed", str(log_path)],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        return max(0, count - 1)
    except subprocess.CalledProcessError:
        return 0


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def get_archive_programs(db: int) -> list[dict]:
    """Get all programs in the archive with their fitness from Redis."""
    import redis

    r = redis.Redis(host="localhost", port=6379, db=db)
    archive = r.hgetall("island_fitness_island:archive")
    if not archive:
        return []

    prefix = "chains/hotpotqa/static"
    import json

    programs = []
    for _bin, pid in archive.items():
        pid_str = pid.decode()
        raw = r.get(f"{prefix}:program:{pid_str}")
        if raw:
            p = json.loads(raw)
            fitness = p.get("metrics", {}).get("fitness", -1.0)
            programs.append({"id": pid_str, "fitness": fitness, "data": p})
    programs.sort(key=lambda x: x["fitness"], reverse=True)
    return programs


def extract_top_programs(run: dict, n: int = 3) -> list[Path]:
    """Run top_programs.py and return saved file paths."""
    top_dir = run["top_dir"]
    top_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJ)
    result = subprocess.run(
        [
            PYTHON,
            "tools/top_programs.py",
            "--run",
            f"chains/hotpotqa/static@{run['db']}:{run['label']}",
            "-n",
            str(n),
            "--save-dir",
            str(top_dir),
            "--state",
            "done",
        ],
        capture_output=True,
        text=True,
        cwd=PROJ,
        env=env,
    )
    if result.returncode != 0:
        log(f"  top_programs.py failed for Run {run['label']}: {result.stderr[:200]}")
        return []

    saved = sorted(top_dir.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    return saved[:n]


def evaluate_on_test(program_path: Path, llm_url: str) -> float | None:
    """Run evaluate.py on the test split, return EM score."""
    env = os.environ.copy()
    env["NO_PROXY"] = "localhost,127.0.0.1,10.226.17.25"
    env["no_proxy"] = "localhost,127.0.0.1,10.226.17.25"
    env["PYTHONPATH"] = str(PROJ)

    result = subprocess.run(
        [
            PYTHON,
            "experiments/hotpotqa_improvement/exp0_baseline/evaluate.py",
            "--program",
            str(program_path),
            "--split",
            "test",
            "--llm-base-url",
            llm_url,
        ],
        capture_output=True,
        text=True,
        cwd=PROJ,
        env=env,
        timeout=600,
    )
    if result.returncode != 0:
        log(f"  evaluate.py failed: {result.stderr[-300:]}")
        return None

    # Parse "Test EM: 0.5233" or "EM: 52.33%" from output
    for line in result.stdout.splitlines():
        line = line.lower()
        if "em:" in line or "exact match" in line:
            parts = line.replace("%", "").split()
            for i, p in enumerate(parts):
                if "em" in p or "match" in p:
                    for j in range(i + 1, min(i + 3, len(parts))):
                        try:
                            val = float(parts[j])
                            return val if val > 1 else val * 100
                        except ValueError:
                            continue
    return None


def generate_plot(checkpoint_gen: int) -> Path | None:
    """Generate fitness comparison plot, return path to PNG."""
    plot_dir = PLOTS_DIR / f"gen{checkpoint_gen:03d}"
    plot_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJ)
    result = subprocess.run(
        [
            PYTHON,
            "tools/comparison.py",
            "--run",
            "chains/hotpotqa/static@10:Run A (control, 8 mut/gen)",
            "--run",
            "chains/hotpotqa/static@11:Run B (high budget, 16 mut/gen)",
            "--run",
            "chains/hotpotqa/static@12:Run C (warm-start, 8 mut/gen)",
            "--title",
            f"HotpotQA Evolution — Fitness vs Iteration (gen {checkpoint_gen})",
            "--xlabel",
            "Iteration (program evaluations)",
            "--ylabel",
            "Validation EM",
            "--smooth-method",
            "lowess",
            "--annotate-frontier",
            "--output-folder",
            str(plot_dir),
        ],
        capture_output=True,
        text=True,
        cwd=PROJ,
        env=env,
    )
    if result.returncode != 0:
        log(f"  Plot generation failed: {result.stderr[-200:]}")
        return None

    png = plot_dir / "evolution_runs_comparison.png"
    return png if png.exists() else None


def compute_trend(db: int, last_n: int = 5) -> str:
    """Determine trend from recent fitness history in Redis."""
    import json

    import redis

    r = redis.Redis(host="localhost", port=6379, db=db)
    prefix = "chains/hotpotqa/static"

    # Collect all program fitnesses sorted by creation time
    all_keys = [k.decode() for k in r.keys(f"{prefix}:program:*")]
    fitnesses = []
    for k in all_keys:
        raw = r.get(k)
        if raw:
            p = json.loads(raw)
            f = p.get("metrics", {}).get("fitness")
            t = p.get("created_at") or p.get("updated_at") or 0
            if f is not None and f > 0:
                fitnesses.append((t, f))

    fitnesses.sort(key=lambda x: x[0])
    if len(fitnesses) < 3:
        return "Early"

    recent = [f for _, f in fitnesses[-last_n:]]
    earlier = [f for _, f in fitnesses[-(last_n * 2) : -last_n]]

    if not earlier:
        return "Early"

    recent_best = max(recent)
    earlier_best = max(earlier) if earlier else recent_best

    if recent_best > earlier_best + 0.01:
        return "Rising"
    elif recent_best > earlier_best + 0.003:
        return "Flat"
    else:
        return "Stagnant"


def signal_str(delta_pp: float) -> str:
    if abs(delta_pp) > 5:
        return "Strong"
    elif abs(delta_pp) > 3:
        return "Suggestive"
    else:
        return "Noise"


def post_pr_comment(body: str) -> bool:
    result = subprocess.run(
        ["gh", "pr", "comment", PR_NUMBER, "--body", body],
        capture_output=True,
        text=True,
        cwd=PROJ,
    )
    return result.returncode == 0


def build_gen10_report(
    checkpoint_gen: int,
    run_stats: list[dict],
    git_hash: str,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    stats_a = run_stats[0]
    stats_b = run_stats[1]
    stats_c = run_stats[2]

    def em_str(v):
        return f"{v:.1f}" if v is not None else "—"

    def delta_str(v, seed):
        return f"+{v - seed:.1f}" if v is not None else "—"

    b_minus_a = (stats_b["best_em"] or 0) - (stats_a["best_em"] or 0)
    c_minus_a = (stats_c["best_em"] or 0) - (stats_a["best_em"] or 0)

    best = max(run_stats, key=lambda s: s["best_em"] or 0)

    # Decision per run
    def decision(s):
        em = s["best_em"] or 0
        trend = s["trend"]
        if em >= 55:
            return "Continue", "Val EM ≥ 55%; strong signal."
        elif em >= 50:
            return "Continue", "Val EM 50–55%, on track."
        elif em >= 45 and trend == "Rising":
            return "Continue", "Val EM 45–50% but rising; re-evaluate at gen 20."
        elif em >= 45 and trend in ("Flat", "Stagnant"):
            return (
                "Investigate",
                "Val EM 45–50% and not rising; check archive diversity.",
            )
        else:
            return (
                "Debug",
                f"Val EM {em:.1f}% below 45%; immediate investigation required.",
            )

    dec_a, rat_a = decision(stats_a)
    dec_b, rat_b = decision(stats_b)
    dec_c, rat_c = decision(stats_c)

    best_em_all = best["best_em"] or 0
    overall = f"At generation 10, best val EM is **{best_em_all:.1f}%** (Run {best['label']})."
    if best_em_all >= 55:
        overall += " All runs are on track to challenge GEPA's 62.3% benchmark."
    elif best_em_all >= 50:
        overall += " Progress is consistent with the target trajectory."
    else:
        overall += " Progress is below the expected trajectory; monitor carefully."

    # Estimate gen 20 ETA (~8-14 min/gen × 10 gens ≈ 80-140 min)

    eta_hours = 10 * 11 / 60  # ~11 min/gen median
    from datetime import timedelta

    eta = datetime.now(UTC) + timedelta(hours=eta_hours)
    eta_str = eta.strftime("%Y-%m-%d %H:%M UTC")

    best_snippet = best.get("snippet") or "# (unavailable)"

    report = f"""## Checkpoint Report: Generation 10 — {now}

**Branch**: `exp/hotpotqa-efficiency` | **Git HEAD**: `{git_hash}`

---

### Per-Run Status

| | **Run A (control)** | **Run B (high budget)** | **Run C (warm-start)** |
|--|---|---|---|
| **Generation** | {stats_a["gen"]} | {stats_b["gen"]} | {stats_c["gen"]} |
| **Best val EM** | {em_str(stats_a["best_em"])}% | {em_str(stats_b["best_em"])}% | {em_str(stats_c["best_em"])}% |
| **Improvement over seed** | {delta_str(stats_a["best_em"], stats_a["seed_em"])} pp | {delta_str(stats_b["best_em"], stats_b["seed_em"])} pp | {delta_str(stats_c["best_em"], stats_c["seed_em"])} pp |
| **Archive size** | {stats_a["archive_size"]} | {stats_b["archive_size"]} | {stats_c["archive_size"]} |
| **Fitness trend** | {stats_a["trend"]} | {stats_b["trend"]} | {stats_c["trend"]} |

### Pairwise Comparisons

| Comparison | Delta (val EM) | Signal | Interpretation |
|------------|---------------|--------|----------------|
| B vs A (mutation budget) | {b_minus_a:+.1f} pp | {signal_str(b_minus_a)} | {"Larger mutation budget may help" if b_minus_a > 3 else "No clear budget effect yet"} |
| C vs A (warm start) | {c_minus_a:+.1f} pp | {signal_str(c_minus_a)} | {"Warm-start seed provides meaningful advantage" if c_minus_a > 3 else "Warm-start advantage not yet apparent"} |

### Best Program (Run {best["label"]}, {em_str(best["best_em"])}% val EM)

<details>
<summary>Program snippet</summary>

```python
{best_snippet}
```
</details>

### Decision per Run

| Run | Decision | Rationale |
|-----|----------|-----------|
| A | **{dec_a}** | {rat_a} |
| B | **{dec_b}** | {rat_b} |
| C | **{dec_c}** | {rat_c} |

### Overall Assessment

{overall}

**Next checkpoint**: Generation 20 — estimated {eta_str}.
"""
    return report


def build_gen20plus_report(
    checkpoint_gen: int,
    run_stats: list[dict],
    git_hash: str,
    prior_checkpoints: list[dict],
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    stats_a, stats_b, stats_c = run_stats

    def em_str(v):
        return f"{v:.1f}" if v is not None else "—"

    def gap_str(val, test):
        if val is None or test is None:
            return "—"
        g = val - test
        return f"{g:+.1f}"

    def overfit_status(gap):
        if gap is None:
            return "—"
        if gap < 2:
            return "Clean"
        elif gap < 4:
            return "Acceptable"
        else:
            return "Concerning"

    best = max(run_stats, key=lambda s: s.get("test_em") or s.get("best_em") or 0)
    best_test = best.get("test_em") or best.get("best_em") or 0

    b_minus_a = (stats_b.get("test_em") or stats_b["best_em"] or 0) - (
        stats_a.get("test_em") or stats_a["best_em"] or 0
    )
    c_minus_a = (stats_c.get("test_em") or stats_c["best_em"] or 0) - (
        stats_a.get("test_em") or stats_a["best_em"] or 0
    )

    # Cumulative rows
    cum_rows = ""
    for cp in prior_checkpoints:
        cum_rows += (
            f"| Gen {cp['gen']} | {em_str(cp.get('a_val'))}% | {em_str(cp.get('a_test'))} | "
            f"{em_str(cp.get('b_val'))}% | {em_str(cp.get('b_test'))} | "
            f"{em_str(cp.get('c_val'))}% | {em_str(cp.get('c_test'))} |\n"
        )

    def decision20(s):
        em = s.get("test_em") or s.get("best_em") or 0
        trend = s["trend"]
        if em >= 62.3:
            return (
                "Replicate",
                "Primary success threshold reached; initiate 3-seed replication.",
            )
        elif em >= 55 and trend == "Rising":
            return (
                "Continue/Extend",
                "Partial success; on track, continue or leapfrog if near gen 50.",
            )
        elif em >= 50:
            return "Continue", f"Minimum viability reached; trend is {trend.lower()}."
        else:
            return "Investigate", f"Below minimum threshold with {trend.lower()} trend."

    dec_a, rat_a = decision20(stats_a)
    dec_b, rat_b = decision20(stats_b)
    dec_c, rat_c = decision20(stats_c)

    gepa_delta = best_test - 62.3
    mipro_delta = best_test - 55.3

    # Pass/fail (gen 30+)
    pf_section = ""
    if checkpoint_gen >= 30:
        pf_section = f"""
### Pass/Fail Assessment

| Criterion | Threshold | Best Run Result | Verdict |
|-----------|-----------|----------------|---------|
| Primary success | Test EM ≥ 62.3% | {em_str(best_test)}% | {"✅ PASS" if best_test >= 62.3 else "❌ FAIL"} |
| Partial success | Test EM ≥ 55.0% | {em_str(best_test)}% | {"✅ PASS" if best_test >= 55.0 else "❌ FAIL"} |
| Minimum viability | Test EM ≥ 50.0% | {em_str(best_test)}% | {"✅ PASS" if best_test >= 50.0 else "❌ FAIL"} |
"""

    # Next steps
    if checkpoint_gen >= 50:
        next_steps = "**Final checkpoint.** " + (
            "Primary success reached — proceed to 3-seed replication."
            if best_test >= 62.3
            else "If best test EM is rising, initiate leapfrog continuation on a new Redis DB."
        )
    else:
        next_checkpoint = min(c for c in CHECKPOINTS if c > checkpoint_gen)
        from datetime import timedelta

        eta = datetime.now(UTC) + timedelta(
            hours=(next_checkpoint - checkpoint_gen) * 11 / 60
        )
        next_steps = f"**Next checkpoint**: Generation {next_checkpoint} — estimated {eta.strftime('%Y-%m-%d %H:%M UTC')}."

    a_gap = gap_str(stats_a.get("best_em"), stats_a.get("test_em"))
    b_gap = gap_str(stats_b.get("best_em"), stats_b.get("test_em"))
    c_gap = gap_str(stats_c.get("best_em"), stats_c.get("test_em"))

    report = f"""## Checkpoint Report: Generation {checkpoint_gen} — {now}

**Branch**: `exp/hotpotqa-efficiency` | **Git HEAD**: `{git_hash}`

---

### Per-Run Status

| | **Run A (control)** | **Run B (high budget)** | **Run C (warm-start)** |
|--|---|---|---|
| **Generation** | {stats_a["gen"]} | {stats_b["gen"]} | {stats_c["gen"]} |
| **Best val EM** | {em_str(stats_a["best_em"])}% | {em_str(stats_b["best_em"])}% | {em_str(stats_c["best_em"])}% |
| **Best test EM** | {em_str(stats_a.get("test_em"))}% | {em_str(stats_b.get("test_em"))}% | {em_str(stats_c.get("test_em"))}% |
| **Val–test gap** | {a_gap} pp | {b_gap} pp | {c_gap} pp |
| **Improvement over seed** | +{(stats_a["best_em"] or 0) - stats_a["seed_em"]:.1f} pp | +{(stats_b["best_em"] or 0) - stats_b["seed_em"]:.1f} pp | +{(stats_c["best_em"] or 0) - stats_c["seed_em"]:.1f} pp |
| **Archive size** | {stats_a["archive_size"]} | {stats_b["archive_size"]} | {stats_c["archive_size"]} |
| **Fitness trend** | {stats_a["trend"]} | {stats_b["trend"]} | {stats_c["trend"]} |

### Cumulative Progress

| Checkpoint | Run A Val EM | Run A Test EM | Run B Val EM | Run B Test EM | Run C Val EM | Run C Test EM |
|------------|-------------|---------------|-------------|---------------|-------------|---------------|
| Gen 0 (seed) | 42.3% | — | 42.3% | — | 52.3% | — |
{cum_rows}
| **Gen {checkpoint_gen}** | **{em_str(stats_a["best_em"])}%** | **{em_str(stats_a.get("test_em"))}%** | **{em_str(stats_b["best_em"])}%** | **{em_str(stats_b.get("test_em"))}%** | **{em_str(stats_c["best_em"])}%** | **{em_str(stats_c.get("test_em"))}%** |

### Comparison to Published Benchmarks

| Method | Test EM | Delta vs Best Run |
|--------|---------|-------------------|
| GEPA (target) | 62.3% | {gepa_delta:+.1f} pp |
| MIPROv2 | 55.3% | {mipro_delta:+.1f} pp |
| Baseline | 42.3% | — |
| **Best run (Run {best["label"]})** | **{em_str(best_test)}%** | — |

### Pairwise Comparisons (Test EM)

| Comparison | Delta | Signal | Interpretation |
|------------|-------|--------|----------------|
| B vs A (mutation budget) | {b_minus_a:+.1f} pp | {signal_str(b_minus_a)} | {"Larger mutation budget yields meaningful improvement" if b_minus_a > 3 else "No significant mutation budget effect"} |
| C vs A (warm start) | {c_minus_a:+.1f} pp | {signal_str(c_minus_a)} | {"Warm-start seed confers a meaningful advantage" if c_minus_a > 3 else "Warm-start advantage is within noise"} |

### Overfitting Check

| Run | Val EM | Test EM | Gap | Status |
|-----|--------|---------|-----|--------|
| A | {em_str(stats_a["best_em"])}% | {em_str(stats_a.get("test_em"))}% | {a_gap} pp | {overfit_status(stats_a["best_em"] - stats_a["test_em"] if stats_a.get("test_em") else None)} |
| B | {em_str(stats_b["best_em"])}% | {em_str(stats_b.get("test_em"))}% | {b_gap} pp | {overfit_status(stats_b["best_em"] - stats_b["test_em"] if stats_b.get("test_em") else None)} |
| C | {em_str(stats_c["best_em"])}% | {em_str(stats_c.get("test_em"))}% | {c_gap} pp | {overfit_status(stats_c["best_em"] - stats_c["test_em"] if stats_c.get("test_em") else None)} |

### Best Program (Run {best["label"]}, {em_str(best_test)}% {"test" if best.get("test_em") else "val"} EM)

<details>
<summary>Program snippet</summary>

```python
{best.get("snippet") or "# (unavailable)"}
```
</details>
{pf_section}
### Decision per Run

| Run | Decision | Rationale |
|-----|----------|-----------|
| A | **{dec_a}** | {rat_a} |
| B | **{dec_b}** | {rat_b} |
| C | **{dec_c}** | {rat_c} |

{next_steps}
"""
    return report


def get_git_hash() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=PROJ,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def get_program_snippet(py_path: Path) -> str:
    """First 15 meaningful lines of the best program."""
    try:
        lines = py_path.read_text().splitlines()
        # Skip blank lines at start
        start = next((i for i, line in enumerate(lines) if line.strip()), 0)
        return "\n".join(lines[start : start + 15])
    except Exception:
        return "# (unavailable)"


def run_checkpoint(checkpoint_gen: int, prior_checkpoints: list[dict]):
    """Execute all checkpoint actions for a given generation milestone."""
    log(f"=== CHECKPOINT: Generation {checkpoint_gen} ===")
    git_hash = get_git_hash()

    run_stats = []
    for run in RUNS:
        log(f"  Extracting top programs for Run {run['label']} (db={run['db']})...")
        top_files = extract_top_programs(run, n=3)

        progs = get_archive_programs(run["db"])
        best_em = progs[0]["fitness"] * 100 if progs else None
        archive_size = len(progs)
        trend = compute_trend(run["db"])
        gen = get_generation(run["log"])

        snippet = ""
        if top_files:
            snippet = get_program_snippet(top_files[0])

        test_em = None
        if checkpoint_gen >= 20 and top_files:
            log(f"  Evaluating Run {run['label']} best program on test set...")
            llm_url = "http://10.226.17.25:8000/v1"
            try:
                test_em = evaluate_on_test(top_files[0], llm_url)
                log(
                    f"  Run {run['label']} test EM: {test_em:.1f}%"
                    if test_em
                    else "  Test eval failed"
                )
            except subprocess.TimeoutExpired:
                log(f"  Run {run['label']} test eval timed out")

        run_stats.append(
            {
                "label": run["label"],
                "db": run["db"],
                "gen": gen,
                "best_em": best_em,
                "test_em": test_em,
                "archive_size": archive_size,
                "trend": trend,
                "seed_em": run["seed_em"],
                "snippet": snippet,
                "top_file": top_files[0] if top_files else None,
            }
        )

    # Generate plot
    log(f"  Generating fitness plot for gen {checkpoint_gen}...")
    generate_plot(checkpoint_gen)

    # Build and post report
    if checkpoint_gen <= 10:
        report = build_gen10_report(checkpoint_gen, run_stats, git_hash)
    else:
        report = build_gen20plus_report(
            checkpoint_gen, run_stats, git_hash, prior_checkpoints
        )

    # Save report to file
    report_path = REPORTS_DIR / f"checkpoint_gen{checkpoint_gen:03d}_report.md"
    report_path.write_text(report)
    log(f"  Report saved: {report_path}")

    # Post to PR
    log("  Posting checkpoint report to PR #65...")
    if post_pr_comment(report):
        log("  PR comment posted successfully")
    else:
        log("  WARNING: PR comment posting failed")

    # Update monitor.log with checkpoint note
    monitor_log = PROJ / "experiments/hotpotqa_3run/monitor.log"
    with open(monitor_log, "a") as f:
        f.write(f"\n{'=' * 60}\n")
        f.write(
            f"CHECKPOINT gen={checkpoint_gen} completed at {datetime.now(UTC).strftime('%H:%M UTC')}\n"
        )
        for s in run_stats:
            test_part = f", test={s['test_em']:.1f}%" if s.get("test_em") else ""
            f.write(
                f"  Run {s['label']}: val={s['best_em']:.1f}%"
                f"{test_part}, archive={s['archive_size']}, trend={s['trend']}\n"
            )
        f.write(f"{'=' * 60}\n")

    # Record this checkpoint for cumulative table
    return {
        "gen": checkpoint_gen,
        "a_val": run_stats[0]["best_em"],
        "a_test": run_stats[0].get("test_em"),
        "b_val": run_stats[1]["best_em"],
        "b_test": run_stats[1].get("test_em"),
        "c_val": run_stats[2]["best_em"],
        "c_test": run_stats[2].get("test_em"),
    }


def main():
    log("Checkpoint daemon started")
    log(
        f"Watching runs: A(db=10,pid={RUNS[0]['pid']}), B(db=11,pid={RUNS[1]['pid']}), C(db=12,pid={RUNS[2]['pid']})"
    )
    log(f"Checkpoints at generations: {CHECKPOINTS}")

    prior_checkpoints = []

    # Also generate an initial plot immediately
    log("Generating initial fitness plot...")
    generate_plot(0)

    while True:
        time.sleep(POLL_INTERVAL)

        gens = {}
        for run in RUNS:
            g = get_generation(run["log"])
            alive = is_alive(run["pid"])
            gens[run["label"]] = g
            if not alive:
                log(
                    f"WARNING: Run {run['label']} (PID {run['pid']}) appears to have died!"
                )

        log(f"Current gens — A:{gens['A']} B:{gens['B']} C:{gens['C']}")

        # Check if any run has crossed a checkpoint (use the MINIMUM gen across runs
        # so we report when ALL runs have reached the checkpoint)
        min_gen = min(gens.values())

        for cp in CHECKPOINTS:
            if cp <= min_gen and cp not in _reported_combined:
                log(f"All runs at or past gen {cp}. Running checkpoint...")
                try:
                    summary = run_checkpoint(cp, prior_checkpoints)
                    prior_checkpoints.append(summary)
                    _reported_combined.add(cp)
                except Exception as e:
                    log(f"ERROR during checkpoint {cp}: {e}")
                break  # one checkpoint at a time

        # Also generate a rolling plot every 2 hours (4 poll cycles)
        # Track via a simple file counter
        counter_file = PROJ / "experiments/hotpotqa_3run/.plot_counter"
        try:
            count = int(counter_file.read_text()) if counter_file.exists() else 0
            count += 1
            counter_file.write_text(str(count))
            if count % 12 == 0:  # every ~2 hours
                log("Generating rolling fitness plot...")
                generate_plot(min_gen)
        except Exception:
            pass


if __name__ == "__main__":
    main()
