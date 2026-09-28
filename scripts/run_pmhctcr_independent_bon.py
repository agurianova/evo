#!/usr/bin/env python3
"""Best-of-N independent mutations: no evolution engine.

Each attempt starts from the same python_patch seed, asks gpt-5.6-terra for
one SEARCH/REPLACE improvement, then scores the child with problems/pmhctcr
validate.py (fit ImmRep25 r0 train, Macro-AUCPR on the 4 val pMHCs) — the
same fitness path as the final terra runs.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PROBLEM = REPO / "problems" / "pmhctcr"
SEED_PATH = PROBLEM / "initial_programs" / "python_patch_seed.py"
EXPERT_PATH = PROBLEM / "expert_hypotheses.txt"
TASK_PATH = PROBLEM / "task_description_final.txt"
SCRIPT = Path(__file__).resolve()

_BLOCKED_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "pickle",
    "shutil",
    "glob",
    "importlib",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if hasattr(obj, "item"):
        try:
            return jsonable(obj.item())
        except Exception:
            return str(obj)
    return str(obj)


def _prepare_score_env() -> None:
    os.environ.setdefault("PMHCTCR_SPLIT", "r0")
    os.environ.setdefault("PMHCTCR_DATA", str(REPO / "pmhctcr_data"))
    for path in (str(REPO), str(PROBLEM)):
        if path not in sys.path:
            sys.path.insert(0, path)


def score_child_main(source_path: Path) -> int:
    _prepare_score_env()
    source = source_path.read_text(encoding="utf-8")
    from validate import validate  # noqa: WPS433  (problem-dir import)

    metrics, artifact = validate(source)
    sys.stdout.write(
        json.dumps(
            {"metrics": jsonable(metrics), "artifact": jsonable(artifact)},
            ensure_ascii=False,
        )
    )
    sys.stdout.write("\n")
    return 0


def _scan_blocked_imports(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return f"syntax: {exc}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_MODULES:
                    return f"blocked import {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _BLOCKED_MODULES:
                return f"blocked import {node.module}"
    return None


def _build_prompt(seed: str, seed_metrics: dict[str, Any], expert: str, task: str):
    from langchain_core.messages import HumanMessage, SystemMessage

    system = f"""You evolve a complete Python program by editing marked regions only.
Return only one or more patches in this exact format:
<<<<<<< SEARCH
exact text copied from the parent
=======
replacement text
>>>>>>> REPLACE

SEARCH must match exactly once and must be wholly inside an EVOLVE block.
Never edit EVOLVE markers or code outside them. Keep top-level
entrypoint() working and returning an object with fit()/score().
Insights describe a Python code change — translate them into SEARCH/REPLACE on
real source. Ignore any OPERATOR=/CHANGE_*/CREATE_*/NOOP JSON-genotype language.
The predictor's active_modalities tuple is a runtime MAP-Elites contract. When
adding or removing actual sequence, structure, or surface use, update that tuple
in the same mutation to match what fit()/score() consume.

This is an independent best-of-N sample: always edit the seed below. There is
no lineage, archive, inspirations, or previous children. Propose one concrete
improvement.

## EXPERT HYPOTHESES (stay within these four areas)

{expert}

## TASK

{task}
"""
    user = f"""=== seed_program ===
metrics={json.dumps(jsonable(seed_metrics), ensure_ascii=False)}

```python
{seed}
```
"""
    return [SystemMessage(content=system), HumanMessage(content=user)]


def _make_llm(run_dir: Path, request_timeout: float):
    from gigaevo.llm.harness import HarnessChat

    workspace = run_dir / "llm_io"
    workspace.mkdir(parents=True, exist_ok=True)
    return HarnessChat(
        model_name="codex/gpt-5.6-terra",
        request_timeout=request_timeout,
        prompts_dir=str(PROBLEM / "prompts_python_patch_final"),
        schema_flag="--output-schema",
        schema_as_path=True,
        answer_file_flag="--output-last-message",
        strict_schema=True,
        stdin_prompts=True,
        workspace_root=str(workspace),
        command=[
            "codex",
            "exec",
            "--model",
            "gpt-5.6-terra",
            "-c",
            'model_reasoning_effort="medium"',
            "-c",
            'forced_login_method="chatgpt"',
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--skip-git-repo-check",
            "--json",
        ],
    )


def _message_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def _score_source(
    source: str,
    dest: Path,
    *,
    timeout: int,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO), str(PROBLEM), env.get("PYTHONPATH", "")]
    )
    env["PMHCTCR_SPLIT"] = os.environ.get("PMHCTCR_SPLIT", "r0")
    env["PMHCTCR_DATA"] = os.environ.get("PMHCTCR_DATA", str(REPO / "pmhctcr_data"))
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    if extra_env:
        env.update(extra_env)
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-u", str(SCRIPT), "--score-child", str(dest)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO),
            env=env,
            start_new_session=True,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "metrics": {"fitness": -1.0, "is_valid": 0.0},
            "artifact": {"reason": f"validator_timeout>{timeout}s"},
            "elapsed_s": time.time() - started,
        }
    elapsed = time.time() - started
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2000:]
        return {
            "status": "score_error",
            "metrics": {"fitness": -1.0, "is_valid": 0.0},
            "artifact": {"reason": err or f"exit={proc.returncode}"},
            "elapsed_s": elapsed,
        }
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        return {
            "status": "score_error",
            "metrics": {"fitness": -1.0, "is_valid": 0.0},
            "artifact": {"reason": f"bad scorer json: {exc}"},
            "elapsed_s": elapsed,
            "stdout_tail": (proc.stdout or "")[-500:],
        }
    metrics = payload.get("metrics") or {"fitness": -1.0, "is_valid": 0.0}
    valid = float(metrics.get("is_valid") or 0.0) >= 1.0
    fit = float(metrics.get("fitness") or -1.0)
    status = "ok" if valid and 0.0 <= fit <= 1.0 else "invalid"
    return {
        "status": status,
        "metrics": metrics,
        "artifact": payload.get("artifact") or {},
        "elapsed_s": elapsed,
    }


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_attempts(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _best_of(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    best = None
    for row in rows:
        if row.get("status") != "ok":
            continue
        fit = float((row.get("metrics") or {}).get("fitness") or -1.0)
        if best is None or fit > float((best.get("metrics") or {}).get("fitness") or -1.0):
            best = row
    return best


def _write_summary(run_dir: Path, payload: dict[str, Any]) -> None:
    (run_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "run_state.json").write_text(
        json.dumps(
            {
                "completion_reason": payload.get("completion_reason"),
                "n_attempts": payload.get("n_attempts"),
                "n_ok": payload.get("n_ok"),
                "best_fitness": payload.get("best_fitness"),
                "best_attempt": payload.get("best_attempt"),
                "seed_fitness": payload.get("seed_fitness"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


async def _one_mutation(
    llm: Any,
    seed: str,
    seed_metrics: dict[str, Any],
    expert: str,
    task: str,
) -> dict[str, Any]:
    from gigaevo.evolution.mutation.python_patch import (
        PythonSourceGenome,
        parse_search_replace,
    )
    from gigaevo.exceptions import MutationError

    response = await llm.ainvoke(_build_prompt(seed, seed_metrics, expert, task))
    patch_text = _message_text(response)
    patches = parse_search_replace(patch_text)
    child = PythonSourceGenome(seed, entry_function="entrypoint").apply(patches)
    return {
        "patch_text": patch_text,
        "n_patches": len(patches),
        "code": child.source,
    }


async def run_replicate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    children_dir = run_dir / "children"
    children_dir.mkdir(exist_ok=True)
    attempts_path = run_dir / "attempts.jsonl"
    lock_path = run_dir / "instance.lock"
    lock_path.write_text(str(os.getpid()), encoding="utf-8")

    seed = SEED_PATH.read_text(encoding="utf-8")
    expert = EXPERT_PATH.read_text(encoding="utf-8") if args.expert_on else ""
    task = TASK_PATH.read_text(encoding="utf-8")

    try:
        shared_seed = REPO / "outputs" / "_bon_seed_val_metrics.json"
        if shared_seed.is_file():
            seed_payload = json.loads(shared_seed.read_text(encoding="utf-8"))
            print(f"[{utc_now()}] reuse cached seed metrics {shared_seed}", flush=True)
        else:
            print(f"[{utc_now()}] scoring seed on ImmRep25 r0 val ...", flush=True)
            seed_payload = _score_source(
                seed,
                run_dir / "seed.py",
                timeout=args.validator_timeout,
            )
            seed_payload["scored_at"] = utc_now()
            shared_seed.parent.mkdir(parents=True, exist_ok=True)
            shared_seed.write_text(
                json.dumps(seed_payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        (run_dir / "seed.py").write_text(seed, encoding="utf-8")
        (run_dir / "seed_metrics.json").write_text(
            json.dumps(seed_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        seed_metrics = seed_payload.get("metrics") or {"fitness": None}

        done = _load_attempts(attempts_path)
        print(
            f"[{utc_now()}] START independent BoN n={args.n} resume={len(done)} "
            f"seed_fitness={seed_metrics.get('fitness')} run_dir={run_dir}",
            flush=True,
        )
        llm = _make_llm(run_dir, args.request_timeout)
        pending = run_dir / "in_progress.json"

        for attempt in range(len(done) + 1, args.n + 1):
            row: dict[str, Any] = {
                "attempt": attempt,
                "ts": utc_now(),
                "parent": "seed",
            }
            try:
                if pending.is_file():
                    staged = json.loads(pending.read_text(encoding="utf-8"))
                    if int(staged.get("attempt") or 0) == attempt and staged.get("code"):
                        print(
                            f"[{utc_now()}] attempt {attempt}/{args.n}: resume staged child",
                            flush=True,
                        )
                        mut = staged
                    else:
                        mut = None
                else:
                    mut = None
                if mut is None:
                    print(
                        f"[{utc_now()}] attempt {attempt}/{args.n}: terra mutate seed",
                        flush=True,
                    )
                    mut = await _one_mutation(llm, seed, seed_metrics, expert, task)
                    pending.write_text(
                        json.dumps(
                            {"attempt": attempt, "n_patches": mut["n_patches"], "code": mut["code"], "patch_text": mut["patch_text"]},
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                blocked = _scan_blocked_imports(mut["code"])
                if blocked:
                    row.update(
                        {
                            "status": "security",
                            "error": blocked,
                            "n_patches": mut.get("n_patches"),
                        }
                    )
                else:
                    child_path = children_dir / f"a{attempt:03d}.py"
                    scored = _score_source(
                        mut["code"],
                        child_path,
                        timeout=args.validator_timeout,
                    )
                    row.update(scored)
                    row["n_patches"] = mut.get("n_patches")
                    row["child_path"] = str(child_path.relative_to(run_dir))
                    (children_dir / f"a{attempt:03d}.patch.txt").write_text(
                        mut.get("patch_text") or "", encoding="utf-8"
                    )
            except Exception as exc:
                row["status"] = "mutate_error"
                row["error"] = f"{type(exc).__name__}: {exc}"
                row["traceback"] = traceback.format_exc()[-2000:]
                print(f"[{utc_now()}] attempt {attempt} {row['status']}: {row.get('error')}", flush=True)

            if pending.is_file():
                pending.unlink()
            _append_jsonl(attempts_path, row)
            done.append(row)
            best = _best_of(done)
            fit = (row.get("metrics") or {}).get("fitness")
            print(
                f"[{utc_now()}] attempt {attempt}/{args.n} status={row.get('status')} "
                f"fitness={fit} best={(best or {}).get('metrics', {}).get('fitness')}",
                flush=True,
            )
            summary = {
                "run_name": args.run_name,
                "n_attempts": len(done),
                "n_ok": sum(1 for r in done if r.get("status") == "ok"),
                "best_fitness": None
                if best is None
                else (best.get("metrics") or {}).get("fitness"),
                "best_attempt": None if best is None else best.get("attempt"),
                "seed_fitness": seed_metrics.get("fitness"),
                "completion_reason": None,
                "updated_at": utc_now(),
            }
            if best is not None:
                src = run_dir / (best.get("child_path") or "")
                if src.is_file():
                    (run_dir / "champion.py").write_text(
                        src.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                    (run_dir / "champion_metrics.json").write_text(
                        json.dumps(best, indent=2, ensure_ascii=False, default=str) + "\n",
                        encoding="utf-8",
                    )
            _write_summary(run_dir, summary)

        best = _best_of(done)
        summary = {
            "run_name": args.run_name,
            "n_attempts": len(done),
            "n_ok": sum(1 for r in done if r.get("status") == "ok"),
            "best_fitness": None
            if best is None
            else (best.get("metrics") or {}).get("fitness"),
            "best_attempt": None if best is None else best.get("attempt"),
            "seed_fitness": seed_metrics.get("fitness"),
            "completion_reason": "max_mutants_reached",
            "updated_at": utc_now(),
        }
        _write_summary(run_dir, summary)
        print(f"[{utc_now()}] DONE {args.run_name} {summary}", flush=True)
        return 0
    finally:
        if lock_path.is_file():
            lock_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir")
    parser.add_argument("--run-name")
    parser.add_argument("-n", type=int, default=100)
    parser.add_argument("--validator-timeout", type=int, default=900)
    parser.add_argument("--request-timeout", type=float, default=180.0)
    parser.add_argument("--expert-on", action="store_true", default=True)
    parser.add_argument("--score-child", type=Path, default=None)
    args = parser.parse_args()
    if args.score_child is not None:
        return score_child_main(args.score_child)
    if not args.run_dir or not args.run_name:
        parser.error("the following arguments are required: --run-dir, --run-name")
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    return asyncio.run(run_replicate(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        raise
