#!/usr/bin/env python3
"""Paired A/B for the embedding-informed reward card prior.

Both arms run the identical memory-v2 pipeline (Gemini 3 Flash mutations, qwen
memory LLM, old-era knobs) so the ONLY lever between them is the reward card
prior: ``control`` selects ``memory/embedding_prior=none`` (the byte-identical
disabled path) and ``embed`` selects ``linear`` (the frozen-projection prior
that pulls a cold card toward its embedding neighbours). Mirrors the fixed-memory
longeval recipe so its numbers sit directly beside the memory-vs-no-memory pairs.

The runner imports gigaevo from the worktree (``seeded_run.py`` asserts the
package resolves under this checkout, and ``PYTHONPATH`` pins it for the worker
pool) so the uncommitted embedding layer is the code that actually runs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import BinaryIO
from urllib.parse import urlparse

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.telegram_notify import notify  # noqa: E402

PYTHON = Path("/home/jovyan/.mlspace/envs/evo/bin/python3")
GIGAEVO = Path("/home/jovyan/.mlspace/envs/evo/bin/gigaevo")
MUTATION_LLM_CONFIG = "gemini3_flash"
MUTATION_MODEL = "google/gemini-3-flash-preview"
DEFAULT_SEEDS = (101, 202, 303)


class Arm(StrEnum):
    CONTROL = "control"
    EMBED = "embed"


# The config group option each arm selects. ``none`` is the default byte-identical
# control; ``linear`` turns the embedding-informed prior on.
EMBEDDING_PRIOR = {Arm.CONTROL: "none", Arm.EMBED: "linear"}


@dataclass(frozen=True)
class Problem:
    slug: str
    name: str
    overrides: tuple[str, ...] = ()


PROBLEMS = (
    Problem(slug="heilbron", name="heilbron"),
    Problem(slug="circle26", name="alphaevolve/packing_circles/n_26"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--max-mutants", type=int, default=250)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument(
        "--problems",
        nargs="+",
        choices=[problem.slug for problem in PROBLEMS],
        help="restrict to these problem slugs (default: all)",
    )
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=[arm.value for arm in Arm],
        help="restrict to these arms (default: both control and embed)",
    )
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def selected_problems(args: argparse.Namespace) -> tuple[Problem, ...]:
    if not args.problems:
        return PROBLEMS
    chosen = set(args.problems)
    return tuple(problem for problem in PROBLEMS if problem.slug in chosen)


def selected_arms(args: argparse.Namespace) -> tuple[Arm, ...]:
    if not args.arms:
        return tuple(Arm)
    chosen = set(args.arms)
    return tuple(arm for arm in Arm if arm.value in chosen)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def primary_repo() -> Path:
    common_dir = subprocess.run(
        [
            "git",
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    return Path(common_dir).parent


def load_environment() -> dict[str, str]:
    load_dotenv(primary_repo() / ".env", override=False)
    required = ("LOCAL_LLM_PROXY", "LITELLM_MASTER_KEY", "OPENROUTER_API_KEY")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"missing required environment variables: {missing}")
    env = dict(os.environ)
    # Gemini mutation calls use OpenRouter; memory calls use the local LiteLLM
    # proxy and read LITELLM_MASTER_KEY independently.
    env["OPENAI_API_KEY"] = env["OPENROUTER_API_KEY"]
    # Pin the worktree on the worker pool's import path so the uncommitted
    # embedding layer wins over the editable install (see embed_prior_launch
    # lineage note). seeded_run.py additionally asserts this for the main process.
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        os.pathsep.join([str(REPO_ROOT), existing_path])
        if existing_path
        else str(REPO_ROOT)
    )
    proxy_host = urlparse(env["LOCAL_LLM_PROXY"]).hostname
    if proxy_host:
        bypass = [
            item
            for item in env.get("NO_PROXY", env.get("no_proxy", "")).split(",")
            if item
        ]
        for host in ("localhost", "127.0.0.1", proxy_host):
            if host not in bypass:
                bypass.append(host)
        env["NO_PROXY"] = env["no_proxy"] = ",".join(bypass)
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env.setdefault(name, "8")
    if "GIGAEVO_TABULAR_DATA" not in env:
        tabular_data = Path("/home/jovyan/tabm-data/data")
        if tabular_data.is_dir():
            env["GIGAEVO_TABULAR_DATA"] = str(tabular_data)
    return env


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def command(
    *,
    problem: Problem,
    arm: Arm,
    seed: int,
    run_dir: Path,
    max_mutants: int,
) -> list[str]:
    overrides = [
        "storage=disk",
        f"problem.name={problem.name}",
        f"llm={MUTATION_LLM_CONFIG}",
        "num_parents=1",
        "max_in_flight=8",
        f"max_mutants={max_mutants}",
        "stage_timeout=3600",
        "dag_timeout=7200",
        "engine_config.terminal_drain_timeout_s=7200",
        f"hydra.run.dir={run_dir}",
        f"checkpoint_dir={run_dir / 'memory'}",
        # Both arms are memory-v2 arms; the embedding-informed reward card prior
        # is the only lever toggled between control and embed.
        "pipeline=memory_guided",
        "memory=v2",
        "memory/write=live",
        "memory/llm=qwen_instruct",
        f"memory.run_seed={seed}",
        f"memory/embedding_prior={EMBEDDING_PRIOR[arm]}",
        *problem.overrides,
    ]
    return [str(PYTHON), str(Path(__file__).with_name("seeded_run.py")), *overrides]


def compose_config(
    *,
    cmd: list[str],
    run_dir: Path,
    env: dict[str, str],
) -> None:
    run_dir.mkdir(parents=True, exist_ok=False)
    seeded_env = dict(env)
    seeded_env["GIGAEVO_EXPERIMENT_SEED"] = run_dir.parent.name.removeprefix("seed_")
    seeded_env["PYTHONHASHSEED"] = seeded_env["GIGAEVO_EXPERIMENT_SEED"]
    with (run_dir / "resolved_config.yaml").open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [*cmd, "--cfg", "job"],
            cwd=REPO_ROOT,
            env=seeded_env,
            stdout=output,
            stderr=subprocess.PIPE,
            text=True,
        )
    if result.returncode:
        (run_dir / "config_error.log").write_text(
            result.stderr,
            encoding="utf-8",
        )
        raise RuntimeError(f"configuration failed for {run_dir}")


def launch(
    *,
    cmd: list[str],
    run_dir: Path,
    seed: int,
    env: dict[str, str],
) -> tuple[subprocess.Popen[bytes], BinaryIO]:
    seeded_env = dict(env)
    seeded_env["GIGAEVO_EXPERIMENT_SEED"] = str(seed)
    seeded_env["PYTHONHASHSEED"] = str(seed)
    log = (run_dir / "run.log").open("wb")
    process = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=seeded_env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return process, log


def best_fitness(run_dir: Path) -> float | None:
    result = subprocess.run(
        [
            str(GIGAEVO),
            "-r",
            str(run_dir / "storage"),
            "-f",
            "json",
            "top",
            "-n",
            "1",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return None
    try:
        rows = json.loads(result.stdout)
        return float(rows[0]["Fitness"]) if rows else None
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def telegram(message: str) -> None:
    try:
        notify(message, parse_mode="")
    except Exception:
        pass


def main() -> int:
    args = parse_args()
    problems = selected_problems(args)
    arms = selected_arms(args)
    env = load_environment()
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_root = (
        args.output_root.resolve()
        if args.output_root
        else REPO_ROOT / "outputs" / f"memory-v2-embedding-ab-{stamp}"
    )
    output_root.mkdir(parents=True, exist_ok=False)
    commit = git_commit()
    status: dict[str, object] = {
        "schema_version": 1,
        "started_at_utc": utc_now(),
        "git_commit": commit,
        "max_mutants": args.max_mutants,
        "seeds": args.seeds,
        "problems": [problem.name for problem in problems],
        "mutation_model": MUTATION_MODEL,
        "arms": {arm.value: EMBEDDING_PRIOR[arm] for arm in arms},
        "knobs": {
            "max_in_flight": 8,
            "stage_timeout": 3600,
            "dag_timeout": 7200,
        },
        "runs": {},
    }
    atomic_json(output_root / "matrix_status.json", status)

    prepared: dict[tuple[str, int, Arm], tuple[Path, list[str]]] = {}
    for problem in problems:
        for seed in args.seeds:
            for arm in arms:
                run_dir = output_root / problem.slug / f"seed_{seed}" / arm.value
                cmd = command(
                    problem=problem,
                    arm=arm,
                    seed=seed,
                    run_dir=run_dir,
                    max_mutants=args.max_mutants,
                )
                compose_config(cmd=cmd, run_dir=run_dir, env=env)
                atomic_json(
                    run_dir / "run_manifest.json",
                    {
                        "problem": problem.name,
                        "arm": arm.value,
                        "embedding_prior": EMBEDDING_PRIOR[arm],
                        "seed": seed,
                        "git_commit": commit,
                        "max_mutants": args.max_mutants,
                        "command": cmd,
                    },
                )
                prepared[(problem.slug, seed, arm)] = (run_dir, cmd)

    if args.validate_only:
        print(f"Validated {len(prepared)} configurations under {output_root}")
        return 0

    telegram(
        "MILESTONE — launched embedding-prior runs "
        f"({len(prepared)} runs, arms={[arm.value for arm in arms]}) "
        f"at commit {commit[:8]} "
        "(control=memory/embedding_prior=none byte-identical, embed=linear). "
        f"Problems {[problem.slug for problem in problems]}, "
        f"Gemini 3 Flash mutations, old-era knobs "
        "(max_in_flight=8, stage_timeout=3600, dag_timeout=7200). "
        f"Seeds {args.seeds}; {args.max_mutants} mutations/arm. "
        f"Output: {output_root}"
    )
    runs = status["runs"]
    assert isinstance(runs, dict)
    failures = 0
    for problem in problems:
        problem_fitness: dict[int, dict[Arm, float | None]] = {
            seed: {} for seed in args.seeds
        }
        for seed in args.seeds:
            active: dict[Arm, tuple[subprocess.Popen[bytes], BinaryIO, Path]] = {}
            for arm in arms:
                run_dir, cmd = prepared[(problem.slug, seed, arm)]
                process, log = launch(cmd=cmd, run_dir=run_dir, seed=seed, env=env)
                active[arm] = (process, log, run_dir)
                runs[f"{problem.slug}/seed_{seed}/{arm.value}"] = {
                    "pid": process.pid,
                    "started_at_utc": utc_now(),
                    "return_code": None,
                }
            atomic_json(output_root / "matrix_status.json", status)

            while any(process.poll() is None for process, _, _ in active.values()):
                time.sleep(30)

            for arm, (process, log, run_dir) in active.items():
                log.close()
                return_code = process.returncode
                fitness = best_fitness(run_dir)
                row = {
                    "problem": problem.name,
                    "seed": seed,
                    "arm": arm.value,
                    "embedding_prior": EMBEDDING_PRIOR[arm],
                    "return_code": return_code,
                    "fitness": fitness,
                    "completed_at_utc": utc_now(),
                }
                problem_fitness[seed][arm] = fitness
                runs[f"{problem.slug}/seed_{seed}/{arm.value}"].update(row)
                if return_code:
                    failures += 1
                    telegram(
                        "ANOMALY — embedding-prior A/B run failed: "
                        f"{problem.name}, seed {seed}, {arm.value}, rc={return_code}. "
                        f"Log: {run_dir / 'run.log'}"
                    )
            atomic_json(output_root / "matrix_status.json", status)

        deltas: list[float] = []
        for rows in problem_fitness.values():
            embed_fitness = rows.get(Arm.EMBED)
            control_fitness = rows.get(Arm.CONTROL)
            if embed_fitness is not None and control_fitness is not None:
                deltas.append(embed_fitness - control_fitness)
        delta_text = (
            f"paired mean Δ (embed − control)={statistics.mean(deltas):+.6g}, "
            f"embed wins={sum(delta > 0 for delta in deltas)}/{len(deltas)}"
            if deltas
            else "no complete fitness pairs"
        )
        telegram(
            f"MILESTONE — {problem.name} embedding-prior A/B complete: {delta_text}. "
            f"Output: {output_root / problem.slug}"
        )

    status["completed_at_utc"] = utc_now()
    status["failures"] = failures
    atomic_json(output_root / "matrix_status.json", status)
    telegram(
        f"MILESTONE — embedding-prior A/B complete with {failures} failed runs. "
        f"Output: {output_root}"
    )
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
