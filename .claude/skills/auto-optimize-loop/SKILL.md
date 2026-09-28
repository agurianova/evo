---
name: auto-optimize-loop
description: Autonomous optimization sprint with agent criticism gates. Analyzes code for perf gains, criticizes proposals before and after implementation, benchmarks, and ships. Stops when gains are exhausted. Use for any code optimization campaign.
argument-hint: <target-file> [--benchmark <bench-cmd>] [--tests <test-paths>] [--pr <number>] [--interval <minutes>]
---

# Auto-Optimize Loop: $ARGUMENTS

Run an autonomous optimization sprint on a target codebase module. Each cycle:
analyze -> criticize proposal -> implement -> criticize implementation -> benchmark -> ship.

Fully autonomous — never ask the user. Decide and execute.

## Step 0 — Parse arguments

Extract from `$ARGUMENTS`:
- `TARGET_FILE`: primary file to optimize (e.g. `gigaevo/evolution/engine/steady_state.py`)
- `BENCHMARK_CMD`: benchmark command (default: `/home/jovyan/envs/evo_fast/bin/python tools/benchmarks/bench_lpt.py`). For the canonical end-to-end measurement grid, use `python tools/canonical_benchmark/run_benchmark.py --label <label>` instead — it runs 5 problems × 2 seeds and writes BENCHMARK_HISTORY.md.
- `TEST_PATHS`: test paths to validate (default: auto-detect from TARGET_FILE using the same mapping as `/run-tests`)
- `PR_NUMBER`: PR to post comments to (default: auto-detect from current branch)
- `INTERVAL`: minutes between cycles (default: 120)

If only a file path is given, use defaults for everything else.

## Step 1 — Baseline benchmark

```bash
$BENCHMARK_CMD 2>&1 | grep -v "^2026\|RuntimeWarning\|tracemalloc\|snapshot.bump"
```

Save output to `/tmp/optloop_baseline.txt`. This is the number to beat.

## Step 2 — Analyze (use `superpowers:dispatching-parallel-agents`)

Use `superpowers:dispatching-parallel-agents` — the two agents are fully independent.

Launch **perf-engineer** and **systems-architect** agents IN PARALLEL. Both receive:

```
You are analyzing `$TARGET_FILE` for performance optimization opportunities.

HARD CONSTRAINTS:
1. Logic equivalence: same inputs must produce same outputs (same seeds = same program flow)
2. All existing tests must pass
3. No new user-facing configuration knobs

RESEARCH ONLY — do NOT edit files. Read the target file and its dependencies.

Produce a RANKED list of optimization proposals. For each:
- What to change (specific code locations)
- Expected throughput improvement (%)
- Risk to correctness (LOW/MEDIUM/HIGH)
- Implementation complexity (LOW/MEDIUM/HIGH)

Think CREATIVELY. Consider:
- TCP-style congestion control for throughput management
- Event-driven patterns replacing polling loops
- Speculative execution / prefetching
- Batched I/O (Redis pipelining, bulk operations)
- Lock-free data structures or reduced lock scope
- Architectural decoupling (separate sync points from data flow)
- Amortized costs (cache, memoize, lazy compute)
```

The **perf-engineer** focuses on micro-optimizations, profiling, and I/O patterns.
The **systems-architect** focuses on architecture, async patterns, and decoupling.

## Step 3 — Synthesize proposals

Merge the two agents' proposals into a single ranked list. Pick the top candidate.

## Step 4 — Criticize proposal (chaos-hacker)

Launch **chaos-hacker agent** with:

```
Adversarial review of this PROPOSED optimization (not yet implemented):

TARGET FILE: $TARGET_FILE
PROPOSED CHANGE: [describe the candidate optimization]
EXPECTED GAIN: [X%]

Find every way this breaks:
1. Correctness — different results for same inputs?
2. Race conditions — concurrent access to shared state?
3. Resource leaks — semaphores, locks, file handles not released?
4. Deadlocks — circular waits, gate never reopens?
5. Edge cases — empty inputs, timeouts, cancellation, exceptions?
6. Ordering violations — events happen in different sequence?

Rate each finding: CRITICAL / HIGH / MEDIUM / LOW.
Suggest mitigations for each.
```

**GATE**: If CRITICAL findings exist that can't be mitigated:
- Try the next-ranked proposal from Step 3
- If all proposals are blocked, stop the cycle (go to Step 10)

## Step 5 — Implement

Make the change. Keep it minimal and focused — one optimization per cycle.
Apply any mitigations suggested by chaos-hacker in Step 4.

## Step 6 — Test

Run `/run-tests $TEST_PATHS`. ALL tests must pass.

If tests fail:
- Revert: `git checkout -- $(dirname $TARGET_FILE)/`
- Try the next-ranked proposal
- If all proposals fail tests, stop the cycle

## Step 7 — Criticize implementation (chaos-hacker)

Launch **chaos-hacker agent** on the actual code DIFF:

```
Adversarial review of this code change in $TARGET_FILE.

[paste the git diff]

Find edge cases, race conditions, resource leaks, and logic flaws.
Check: Can any resource grow unbounded? Can any lock/gate stay closed forever?
Can any counter be incremented/decremented incorrectly?

Rate findings: CRITICAL / HIGH / MEDIUM / LOW.
```

**GATE**: Fix any MEDIUM+ bugs found. Re-run tests after fixes.

## Step 8 — Benchmark

Run the same benchmark command from Step 1. Compare to baseline.

**GATE**: If best-case gain < 2% across all configurations:
- This optimization is not worth shipping
- Revert: `git checkout -- $(dirname $TARGET_FILE)/`
- Try the next-ranked proposal
- If ALL proposals yield < 2%, stop the cycle

## Step 9 — Ship (use `superpowers:verification-before-completion` + `superpowers:finishing-a-development-branch`)

1. Lint: `ruff check $TARGET_FILE && ruff format $TARGET_FILE`
2. Verify: re-run tests one final time to confirm the optimized code is stable (use `superpowers:verification-before-completion`).
3. Commit with message including before/after benchmark table.
4. Use `superpowers:finishing-a-development-branch` to push and update the PR.
5. If PR_NUMBER is set, post a comment on the PR with the comparison table.

## Step 10 — Decide continuation

**Continue** (set up next cycle via cron) if:
- This cycle shipped an improvement >= 2%
- Failed cycles < 3 consecutive

**Stop** (cancel the cron) if:
- 3 consecutive cycles found no >= 2% improvement
- All proposals from agents are exhausted or blocked by correctness
- Post a final summary comment on the PR: "Optimization sprint complete. N cycles, X% cumulative improvement. Remaining bottleneck: [description]."

To set up recurring execution:
```
/loop ${INTERVAL}m /auto-optimize-loop $ARGUMENTS
```

## Tracking

After each cycle, append a line to `/tmp/optloop_history.txt`:
```
CYCLE=N | RESULT=shipped|skipped|stopped | GAIN=X% | CHANGE="description" | BASELINE=Y | AFTER=Z
```

## Gotchas

- The benchmark has randomness — use `random.seed(42)` or accept ~5% variance between runs
- Some optimizations improve mutation rate but not ingestion rate (pipeline filling vs throughput). Both matter — report both.
- Async code is subtle — chaos-hacker review is NOT optional, it's a hard gate
- If the target file was modified externally since last cycle, re-read before editing
- Never amend commits — always create new ones
- The 2% threshold is per-cycle, not cumulative. A 1.5% gain that compounds over 5 cycles is still worth shipping — but only if you're confident the measurement is real (run benchmark 2x to confirm)
