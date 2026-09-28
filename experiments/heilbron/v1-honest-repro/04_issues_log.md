# Issues Log: heilbron/v1-honest-repro

## I-01: Treatment check regex too strict for fallback opponents
- **Date**: 2026-04-26 (smoke test)
- **What**: `treatment_checks.log_pattern_present` had `\[ExecOpponentResultProvider\] produced \d+/\d+` which failed to match the actual fallback log line `[ExecOpponentResultProvider] fallback produced 2/2 ok` emitted when D archive is cold.
- **Where**: `experiment.yaml:282`
- **Root cause**: ExecOpponentResultProvider has two log forms:
  - normal path: `[ExecOpponentResultProvider] produced X/Y ok`
  - fallback path: `[ExecOpponentResultProvider] fallback produced X/Y ok` (cold D archive)
  The original regex only allowed the normal form, but G-only smoke runs always hit fallback because D's pop_b archive is empty.
- **Fix applied**: Pattern relaxed to `\[ExecOpponentResultProvider\].*produced \d+/\d+|\[CachedOpponentResultProvider\] hit=\d+` — accepts either form.
- **Systemic fix needed**: NO — smoke-time artifact. In real run both pops produce, so both forms appear.

## I-02: Smoke test cut short
- **Date**: 2026-04-26 02:30 UTC
- **What**: Researcher requested skip-to-launch. Smoke killed at gen 2 of 3 with PID 3509593, etime 37:47, 6 programs evaluated, 0 errors, all treatment markers present, fitness values plausible (0.00035–0.00038 raw quality).
- **Where**: smoke.log shows `[SteadyState] Epoch 0 refresh ----` at 02:09:57, then proceeded to gen 2 by 02:15:41. Killed at 02:30:21.
- **Root cause**: Time tradeoff — Qwen3-235B-Thinking averaged ~12 min per epoch; full 3-gen smoke would have completed ~02:50. Treatment markers were already verified by 02:30, so further runtime added zero verification value.
- **Fix applied**: None. Treatment_checks pass on partial log (Redis key present, 12 of 12 log patterns match, 0 absent-patterns triggered).
- **Systemic fix needed**: NO — operational decision per researcher.

## I-03: D-side runs crashed at instantiation — dg_tracker/lineage_filter coupling
- **Date**: 2026-04-26 03:09 UTC (first launch attempt)
- **What**: All 4 D-side runs (A1_D, A2_D, C1_D, C2_D) died within ~2s of launch with `ValueError('lineage_filter.aggregator required — no silent fallback')` raised by `_resolve_lineage_filter` in `gigaevo/adversarial/asymmetric_pipeline.py:73-113`. The 4 G-side runs continued unaffected.
- **Where**: `AdversarialAsymmetricPipelineBuilder.__init__` → `_resolve_lineage_filter` (asymmetric_pipeline.py:73-113, called from line 200-215). When `population_role == "improver"` AND `dg_tracker is not None`, the builder rejects `lineage_filter == None`.
- **Root cause**: Hydra config inheritance. `config/pipeline/heilbron_v1_honest.yaml` overrides only `pipeline_builder.aggregator` and `pipeline_builder.lineage_filter: null` — leaf-level merge. The parent `config/pipeline/adversarial_asymmetric.yaml` wires `pipeline_builder.dg_tracker: ${dg_tracker}` (DGImprovementTracker) and that survives the child override. Result: D ended up with `dg_tracker != None` and `lineage_filter == None` → guard tripped. Smoke test never exposed this because smoke ran A1_G only (constructor role); the role=improver code path was never instantiated.
- **Fix applied**: Added `- pipeline_builder.dg_tracker=null` to all 4 D-side `extra_overrides` in `experiment.yaml` (A1_D, A2_D, C1_D, C2_D). Verified by re-launch at 03:23:12 UTC: all 4 D logs show `[AsymmetricPipeline] role=improver feedback={composition,gradient_in_prompt} n_opp=1 source_prompt_k=1 dg_tracker=no aggregator=ConfigurableAggregator`. All 9 PIDs alive at +2 min, 0 errors across all 8 logs, all 8 Redis DBs populating.
- **Systemic fix needed**: YES — twofold.
  1. **Smoke-test coverage gap**: Smoke must exercise both roles for adversarial-asymmetric experiments, not just one. A G-only smoke validates the constructor code path but leaves the improver instantiation entirely unverified. Promote to PATTERNS.md as a Known Failure (smoke-tests-must-cover-all-roles).
  2. **Architectural drift from v1**: Original `01_design.md` Q16 stated "lineage_filter: null disables SBF" as the only modification needed. Current main has additional `dg_tracker→lineage_filter` coupling that did not exist (or was unconstrained) at the v1 commit. The `dg_tracker=null` requirement on D is therefore an additional deviation from v1; documented in `01_design.md` deviations addendum. This is arguably MORE faithful to v1 (which had no DGImprovementTracker), but represents a deeper rip-out than originally specified.
- **Re-launched**: 2026-04-26 03:23:12 UTC. New PIDs: A1_G=3546906, A1_D=3546907, A2_G=3546908, A2_D=3546909, C1_G=3546910, C1_D=3546911, C2_G=3546912, C2_D=3546913, watchdog=3548072.

### [EVENT 2026-04-26T01:52:56Z] -- Checkpoint #1 recorded at gen ~0 (Redis), gen 1-3 (status table)

- **When**: 2026-04-26T01:52:56Z
- **What**: First scheduled checkpoint at ~85 min elapsed. All 9 PIDs alive, manifest validates, top programs saved per run. best_actual_fitness range: 0.0167 (C1_G) to 0.0297 (A1_D). All runs below baseline mean=0.03574, but at <2% of max_generations this is uninformative.
- **Category**: checkpoint
- **Decisions made**:
  1. Skipped Step 6 test eval — has_test_set=false, no test eval applicable.
  2. Skipped Step 7 checkpoint analyst — gen 0-3 << 50% of max_gen=200.
  3. Did NOT alert researcher: errors in logs (24-126 per run) decomposed into LLM-generated-program failures (SyntaxError, SecurityViolationError — security gate working) and analytics-stage timeouts (LineageStage, InsightsStage). None on fitness path; matches PATTERNS.md known-noise classes.
- **Impact**: Automated capture. No protocol deviation.

## I-04: experiment-checkpoint Step 8 yaml.dump recurrence of prereg_commit quote-strip

- **Date**: 2026-04-26 01:48 UTC (this checkpoint)
- **What**: The Step 8 checkpoint script in `.claude/skills/experiment-checkpoint/SKILL.md` does `yaml.dump(data, ...)` and silently strips the quotes from `prereg_commit: "25470e37"`, leaving `prereg_commit: 25470e37`. On next `gigaevo manifest gate` (or any load_manifest call), Pydantic rejects with `Input should be a valid string [input_value=2.547e+41, input_type=float]`. This is the same trap that bit launch (originally fixed in I-01-adjacent commit during /experiment-launch).
- **Where**: `.claude/skills/experiment-checkpoint/SKILL.md` Step 8, the `manifest_path.write_text(yaml.dump(data, ...))` call.
- **Root cause**: PyYAML's default representer prefers no-quote for strings that look unambiguous to the dumper but ARE ambiguous to the loader (any 8-char hex starting with digits and containing one or more 'e'/'E' chars looks like `<digits>e<digits>` scientific notation).
- **Fix applied (this checkpoint, local hack)**: After yaml.dump, regex re-quote: `re.sub(r'(prereg_commit:\s+)([0-9a-fA-F]{6,12})(\s*$)', r'\1"\2"\3', text, flags=re.M)`.
- **Systemic fix needed**: YES. Two options:
  1. Patch experiment-checkpoint's Step 8 (and any other skill that dumps yaml back) with the regex re-quote, OR
  2. Use ruamel.yaml round-trip to preserve quoting, OR
  3. Add a custom representer/dumper class in a shared util that quotes any string matching the hex-like-but-also-numeric-looking pattern.
  Best home: `gigaevo/experiment/manifest.py` should expose a `save_manifest(data, path)` helper that all skills use, with the bug-resistant dumper. Skills then call `save_manifest()` instead of raw yaml.dump.

### [EVENT 2026-04-26T05:49:30Z] -- Checkpoint #2 recorded at engine gen ~0 (per-run status gens 5-11)

- **When**: 2026-04-26T05:49:30Z
- **What**: Second scheduled checkpoint at ~5h elapsed since launch. All 9 PIDs alive, manifest validates after yaml.dump, top programs saved per run. best_actual_fitness range: 0.0264 (C1_G) to 0.03382 (A1_G); A1_G now within 6.7% of baseline 0.03574 and trending toward v1 SOTA 0.03648.
- **Category**: checkpoint
- **Decisions made**:
  1. Skipped Step 6 test eval — has_test_set=false.
  2. Skipped Step 7 checkpoint analyst — gen ~0-11 << 50% of max_gen=200.
  3. /experiment-diagnose skill skipped — done manually (PIDs, log freshness, error class triage). Verdict HEALTHY: only TimeoutError noise from analytics stage; treatment markers present in all 8 runs.
  4. Did NOT alert researcher: 268-410 errors per run all decompose into LLM-program SyntaxError/SecurityViolationError (gates working) and LineageStage/InsightsStage TimeoutError (analytics off the fitness path); none on fitness path.
- **Impact**: Automated capture. No protocol deviation. [CHECKPOINT engine_gen=0 status_gen=5-11] — no deviations or decisions affecting hypothesis interpretation.

### [EVENT 2026-04-26T09:48:15Z] -- Checkpoint #3 recorded at engine gen ~0 (per-run status gens 10-16)

- **When**: 2026-04-26T09:48:15Z
- **What**: Third scheduled checkpoint at ~9h elapsed since launch. All 9 PIDs alive. best_actual_fitness range: 0.03049 (A2_D) to 0.03382 (A1_G). All 4 D runs improved this period; A2_G/C1_G both jumped to 0.03170 (C1_G +0.0053).
- **Category**: checkpoint
- **Decisions made**:
  1. Skipped Step 6 test eval — has_test_set=false.
  2. Skipped Step 7 checkpoint analyst — gen ~10-16 << 50% of max_gen=200.
  3. /experiment-diagnose skill skipped — done manually. Verdict HEALTHY: known-noise TimeoutError (analytics) + SyntaxError (LLM-program gating); treatment markers present in all 8 runs.
  4. Did NOT alert researcher: no infrastructure errors, no pattern matches, no anomalies.
- **Impact**: Automated capture. No protocol deviation. [CHECKPOINT engine_gen=0 status_gen=10-16] — no deviations or decisions affecting hypothesis interpretation.

## I-05: InsightsStage opponent-keyed cache_on edge — structural confound vs v1, removed pre-relaunch

- **Date**: 2026-04-26 (researcher question after Checkpoint #3, ~9.5h into first launch)
- **What**: Researcher asked whether InsightsStage on D was cached on opponent IDs in v1. It was not. Current main wires `FetchOpponentIdsStage → InsightsStage cache_on` in `_wire_cache_on_edges()` (`gigaevo/adversarial/asymmetric_pipeline.py:304-314`). Because D's opponents rotate every generation, the InsightsStage cache misses every generation on main and runs an LLM call per program per gen — work that did not exist in v1 (PR #204).
- **Where**: Wiring introduced in commit `1d25a9a8` (2026-04-17 01:18:35 +0300, "feat(adversarial): wire DGTrackerStage + cache_on edges in asymmetric builder"). PR #204 (v1 baseline, commit `0b8e4467`) predates `1d25a9a8`.
- **Root cause**: Cache-correctness optimization added in `_wire_cache_on_edges` after v1 launched. The optimization is sound for stages whose semantics depend on the opponent set, but InsightsStage describes a program in isolation — opponents do not feed into its `compute()`, so opponent-keyed invalidation is gratuitous.
- **Effect on this experiment**: Extra D-side LLM work per generation, depressing D's gen pace and altering cache hit-rates relative to v1. Means current run is no longer a strict v1 reproduction even after I-03's `dg_tracker=null` correction. Detected at ~9.5h, before any cross-50% milestone.
- **Fix applied**: Made the wiring parametric. Added `cache_insights_on_opponents: bool = True` constructor kwarg on `AdversarialAsymmetricPipelineBuilder` (default True preserves current main behavior for all other adversarial experiments). Set `pipeline_builder.cache_insights_on_opponents: false` in `config/pipeline/heilbron_v1_honest.yaml` so v1-honest-repro runs with v1's exact cache semantics. Tests added: `test_insights_cache_on_disabled_for_d/g` cover the flag-False branch; existing `test_cache_on_edges_wired_for_d/g` retained on default-True. Commit `063c9cc9`. LineageStage cache_on wiring left intact.
- **Re-launch decision**: Researcher elected to abort the running experiment and re-launch under the corrected wiring rather than carry the confound. ~9.5h sunk on first launch. Pre-50% checkpoint had no test eval committed and no checkpoint-analyst run, so the abort costs nothing in terms of unblinding.
- **Systemic fix needed**: NO for this experiment (config flag is the systemic fix). Optional follow-up for the broader codebase: add a comment in `_wire_cache_on_edges` warning that InsightsStage caching on opponent IDs is semantically gratuitous and may bias gen-pace comparisons against any baseline that pre-dated `1d25a9a8`.

## I-06: Upstream LLM (Qwen3-235B-A22B-Thinking-2507) unresponsive — all 8 runs blocked on /chat/completions

- **Date**: 2026-04-26 ~16:39 UTC (anomaly-detector cycle 2, ~2h26m post-relaunch)
- **What**: All 8 runs alive but stalled at `engine:total_generations = 0` since launch. Mutation pipeline started ~14:49 (36 min after launch); first cascade of `[MutationAgent] Structured LLM call failed: Request timed out.` at 14:59 across all 8 runs simultaneously. As of 16:39 every log's most recent line is still `openai._base_client INFO - Retrying request to /chat/completions in ~0.4s` and processes are in S/Sl state at ~0.7% CPU — i.e. blocked on httpx retries. Watchdog Cycle 3 (16:16) independently flagged 7 stall alerts (`gen=0, running=0, total=1`). No replicate asymmetry, no PID death, no helper bug, no import error.
- **Where**: Upstream model serving layer behind `http://10.232.30.185:4000/v1` (LiteLLM proxy), specifically the Qwen3-235B-A22B-Thinking-2507 backend.
- **Category**: infra issue (upstream LLM)
- **Root cause** (best evidence available without server-side access):
  - `GET /v1/models` returns HTTP 200 in <5 ms and lists Qwen3-235B-A22B-Thinking-2507 + Qwen/Qwen3-8B → LiteLLM proxy front door is healthy.
  - Direct probe `POST /v1/chat/completions {model: Qwen3-235B-A22B-Thinking-2507, max_tokens: 2}` hangs 90+ s with 0 bytes received → the model-serving instance behind the proxy is non-responsive.
  - The runs see this as instant `Request timed out` (sub-200ms) because `MutationAgent` uses `with_structured_output`/openai-sdk async path that is configured to fail fast on connect-level errors, then loops; the visible "timed out" message is misleading wording for what is effectively a 5xx/queue-stall on the upstream.
  - Pattern match: **Pattern 10 (Server Down / Model Drift)** — variant where proxy front-door is up but model server is unresponsive.
- **Pattern-matching exclusions**: NOT Pattern 1 (no helper shape mismatch — invalidity 0% across runs), NOT Pattern 2 (no ImportError), NOT Pattern 6 (pipeline correct, treatment markers verified at smoke), NOT Pattern 9 (all PIDs alive), NOT Pattern 11 (auth works — 200 on /models with Bearer key).
- **Action taken by anomaly detector**:
  1. NO auto-restart attempted. Per Pattern 10 doctrine: server issues require infra intervention; restarting runs would reproduce the same hang since the upstream is the bottleneck. Run processes are not crashed and will resume automatically once the model server recovers (httpx retry loop is idempotent at the mutation-agent level).
  2. PR #224 comment posted with this finding.
  3. Telegram alert sent (CRITICAL infrastructure anomaly, per standing autonomous-mode authorization).
  4. Restart counter NOT incremented (no run restart performed).
- **Recommended researcher action**: Investigate vLLM backend serving Qwen3-235B-A22B-Thinking-2507 on 10.232.30.185 (likely candidates: GPU OOM / queue saturation / model unloaded). Once backend recovers, expect runs to resume from current state without intervention. If the backend is down >12h, consider whether process-side retry budgets will exhaust; if so, a coordinated restart (all 8 + watchdog) will be needed.
- **Systemic fix needed**: NO for the experiment (this is environmental). Optional improvement for the framework: surface the underlying httpx exception rather than collapsing it to "Request timed out" in `MutationAgent.acall_llm` — this would make Pattern 10 vs Pattern 3 vs Pattern 11 distinguishable from logs alone without proxy probing.

### [EVENT 2026-04-26T16:51:30Z] -- Checkpoint #4 SKIPPED — CRITICAL infrastructure (I-06)

- **When**: 2026-04-26T16:51:30Z (~2.6h post-relaunch)
- **What**: experiment-checkpoint skill invoked but stopped before Step 4 per skill's CRITICAL rule. All 8 PIDs alive but engine_gen=0 across all runs since launch (mutation pipeline blocked on upstream LLM hang since 14:59 UTC, see I-06). Status table shows non-zero seed-eval values (G runs fitness=0.00035 from initial 8-program seed eval; D runs fitness=0.03786 likewise) — these are pre-run-loop seed numbers, not evolution progress.
- **Category**: checkpoint
- **Decisions made**:
  1. Skipped Steps 4-9: recording a checkpoint at engine_gen=0 across all runs would write misleading "0 generations of progress" rows into the manifest after 2.6h elapsed time, polluting the trajectory. Better: skip cleanly, wait for upstream recovery, take next checkpoint when real progress resumes.
  2. Did NOT save top programs: no evolution progress to capture; current Redis state is identical to launch state.
  3. Did NOT post a checkpoint PR comment: I-06 was already posted to PR #224 by anomaly-detector cycle 2; another comment now would duplicate.
  4. Test eval (Step 6) and checkpoint analyst (Step 7) are gated on >= 50% of max_gen (gen=0 << 100); both correctly skipped by the skill's own logic regardless.
- **Impact**: No protocol deviation against pre-registration. Standing autonomous-mode policy (Telegram only on CRITICAL infra) was honored at the I-06 detection event; no further escalation needed for this checkpoint event. Next checkpoint cron fires ~20:14 UTC; if upstream is recovered by then, a real checkpoint will be recorded; otherwise this same skip-and-log decision will repeat.

## I-07: Run processes wedged after upstream LLM recovery — coordinated restart needed

- **Date**: 2026-04-26 ~17:25 UTC (researcher restarted LiteLLM proxy ~17:22; runs did not self-recover)
- **What**: After researcher restarted the LiteLLM proxy at 10.232.30.185:4000 (resolving I-06), the 8 run processes (3650880–3650887) failed to resume. Direct probe `POST /v1/chat/completions` to Qwen3-235B-A22B-Thinking-2507 returned HTTP 200 in 77ms (proxy + upstream healthy), and TCP connections from the runs to 10.232.30.185:4000 were ESTABLISHED, but no log activity for ~7 min after the proxy came back. Last gigaevo log was at 16:59:13 (mutation:acall_llm:261 ERROR cascade), last openai SDK retry log at 17:19:13. Processes were in S state at ~0.7% CPU with 832 MB RSS and 143 threads, sleeping in asyncio await with no in-flight requests that would see the recovered backend.
- **Where**: Same upstream as I-06 (LiteLLM proxy 10.232.30.185:4000 + Qwen3-235B-A22B-Thinking-2507 backend), but the failure mode this time is process-side, not backend-side. The 2.5h openai-SDK retry-budget exhaustion during the upstream outage left the asyncio task graph wedged in a way that the SDK's exception did not propagate back to gigaevo's mutation loop, so the runs sat silently on dead-from-the-runs'-perspective sockets even after the backend recovered.
- **Category**: infra issue (downstream — process-side residue of upstream outage)
- **Pattern**: Same pattern noted in I-06's recommended-action footnote: "If the backend is down >12h, consider whether process-side retry budgets will exhaust; if so, a coordinated restart (all 8 + watchdog) will be needed." The 2.5h outage was sufficient to trigger this mode at smaller scale.
- **Researcher heads-up**: Mid-restart, researcher reminded "dont forget no_proxy for litellm". Verified before restart: launch.sh exports `NO_PROXY="localhost,127.0.0.1,10.232.30.185"`, and /proc/<pid>/environ confirmed it was set on the wedged PIDs. Carried into the new launch unchanged.
- **Fix applied**:
  1. SIGTERM 8 PIDs (3650880–3650887) — all died gracefully in 15s.
  2. Flushed Redis DBs 1–8 (`gigaevo flush --db N --confirm`) — only ~140-220 keys per DB lost (seed-eval state; no real generations had completed under this launch, so cost is minimal).
  3. Reset `experiment.status = implemented`, `lifecycle.status = implemented`, `lifecycle.launch = {}`, cleared all `runs[].pid` (Python helper with `prereg_commit` re-quote regex per I-04).
  4. Re-launched via `gigaevo -e heilbron/v1-honest-repro launch --skip-preflight`.
  5. New PIDs at 17:32:56 UTC: A1_G=3686874, A1_D=3686875, A2_G=3686876, A2_D=3686877, C1_G=3686878, C1_D=3686879, C2_G=3686880, C2_D=3686881. New watchdog: 3687516.
  6. **Watchdog dedup**: launch spawned a new watchdog 3687516 while the old one (3651643, alive from the prior launch) was still running. SIGTERM-killed 3651643 to avoid duplicate alerts/PR comments. Manifest now correctly references 3687516.
  7. Verified: all 8 new run PIDs alive at +60s, status=running, manifest gate passes, seed-eval started (G runs at val_dur 1/1, A2_G already showing seed fitness 0.00035).
- **Cron persistence**: Anomaly-detector cron `f0967ce0` and checkpoint cron `b7c8d567` remain active and target the experiment name (unchanged). They will resume monitoring the new PIDs automatically.
- **Systemic fix needed**: YES (deferred). Two improvements:
  1. **`MutationAgent.acall_llm` should propagate underlying httpx exceptions** rather than collapsing to "Request timed out." This would make the wedged-asyncio-task mode visible in logs at gigaevo level, allowing watchdog or anomaly-detector to flag it without process-state inspection. Already noted in I-06.
  2. **Anomaly-detector / watchdog should detect "wedged after upstream recovery" pattern**: criterion = (upstream proxy probes healthy) AND (no gigaevo-level log activity for >5 min) AND (PIDs alive). When triggered, recommend coordinated restart. Currently this requires manual intervention via diagnosis chain (curl probe → process inspection → tcp-state inspection → restart). Promote to PATTERNS.md as KF-XX (post-outage-process-wedge).

### [EVENT 2026-04-26T17:52:42Z] -- Checkpoint #5 recorded at gen ~6 (avg)

- **When**: 2026-04-26T17:52:42Z
- **What**: Checkpoint #5 recorded. avg_gen=6.4 (D-side ~7.5, G-side ~5.25). Best actual_fitness 0.01965-0.02866 across 8 runs — within v2 NULL band as expected for early gens. PIDs 3686874-3686881 all alive; watchdog 3687516 alive.
- **Category**: checkpoint
- **Impact**: Automated capture. First post-relaunch checkpoint after I-07 — confirms experiment recovered cleanly and is making progress.
- **Decisions**:
  - SKIP test eval — has_test_set=false.
  - SKIP checkpoint-analyst — ~3% of max_gen=200, well below 50% gate.
  - SKIP /experiment-diagnose — CLI/skill not present in repo. Substituted: anomaly-detector cycle 4 HEALTHY (~21 min prior).
  - Manifest write hit I-04 (yaml.dump un-quoted prereg_commit `25470e37` → `2.547e+41` float). Re-quoted inline; checkpoint #5 was rewritten with correct paths (engine:snapshot JSON blob for gen, contract.problem.metric_name for metric).
  - Tooling note: canned recent-invalidity probe in checkpoint script returns 0% due to a key-path mismatch on `{prefix}:metrics:history:program_metrics:is_valid`. True invalidity (from `gigaevo status`) is 8-51% across runs — recorded in PR comment text. Not a regression; pre-existing bug in the checkpoint helper script.

### [EVENT 2026-04-26T21:46:09Z] -- Checkpoint #6 recorded at gen ~17.9 (avg)

- **When**: 2026-04-26T21:46:09Z
- **What**: Checkpoint #6 recorded. avg_gen=17.9 (D-side ~21.5, G-side ~14.25). C-arm 3/4 leaders crossed v2 NULL band center (0.03315): C2_D=0.03458, C2_G=0.03452, C1_D=0.03434. C1_G=0.03306 just below. Gap to asymmetric-iterations baseline (0.03574) ~3.2-7.0% on C-arm leaders. A-arm trails C-arm by ~0.004.
- **Category**: checkpoint
- **Impact**: Automated capture. No actions taken; experiment progressing healthily.
- **Decisions**:
  - SKIP test eval — has_test_set=false.
  - SKIP checkpoint-analyst — ~9% of max_gen=200 (<50% gate).
  - SKIP /experiment-diagnose — CLI not in repo. Substituted: anomaly-detector cycle 6 HEALTHY (~ minutes prior).
  - Manifest write hit I-04 again (yaml.dump un-quoted `prereg_commit`); re-quoted inline. Systemic fix still deferred.
  - Stopping-rule canned probe still uses stale `engine:total_generations` (returns 0); checkpoint write uses correct `engine:snapshot` JSON blob.

### [EVENT 2026-04-27T01:45:26Z] -- Checkpoint #7 recorded at gen ~28.5 (avg)

- **When**: 2026-04-27T01:45:26Z
- **What**: Checkpoint #7 recorded. avg_gen=28.5 (D-side ~36.25, G-side ~20.75). Frontier C1_D=0.03494 (-0.00080 from baseline 0.03574, -0.00154 from SOTA 0.03648). A-arm closing fast: A1_D=0.03305 (+0.00267 since CP#6, just 0.0001 below v2 NULL center 0.03315). Best-A vs best-C gap narrowed from -0.004 (CP#6) to -0.00189.
- **Category**: checkpoint
- **Impact**: Automated capture. No interventions.
- **Decisions**:
  - SKIP test eval — has_test_set=false.
  - SKIP checkpoint-analyst — ~14% of max_gen=200 (<50% gate).
  - SKIP /experiment-diagnose — CLI not in repo. Substituted: anomaly-detector cycle 8 HEALTHY (~ minutes prior).
  - A2_D Mean Improvement Raw=0.0 noted by anomaly cycle 8 — gen still advancing (+7 since CP#6), so not a stall yet. Will re-check at CP#8.
  - Manifest write hit I-04 again (yaml.dump un-quoted `prereg_commit`); re-quoted inline. Systemic fix still deferred.

### [EVENT 2026-04-27 closeout] -- Experiment early-terminated and closed out

- **When**: 2026-04-27 (early-terminate authorized by researcher; final fitness extraction immediately followed)
- **What**: Researcher authorized early termination at G gens 50-58 / D gens 71-91 (vs. pre-registered max=200), after observing C-arm G plateau (no improvement gen 28→58) and emerging A-vs-C divergence. All 8 PIDs SIGTERMed cleanly (no SIGKILL escalation). Watchdog 3687516 killed; anomaly cron f0967ce0 and checkpoint cron b7c8d567 cancelled. All 8 archives uploaded to GitHub Release exp/heilbron/v1-honest-repro. Elena wrote 05_results.md (verdict: SUGGESTIVE, lean H₁); researcher approved at R8 gate.
- **Category**: closeout
- **Impact**: Experiment closed; status set to complete. Pre-registration deviation (early termination at ~25-46% of pre-reg horizon) documented in 05_results.md § Deviations from Pre-Registration as the largest caveat against a firm NEGATIVE call.
- **Root cause**: N/A (researcher decision, not infrastructure failure)
- **Fix applied**: SIGTERM all 8 run PIDs; killed watchdog; cancelled crons; archived all runs; wrote 05_results.md.
- **Systemic fix needed**: NO

### [EVENT 2026-04-27 closeout] -- Step 13b paper-draft skipped (deferred to retrospective)

- **When**: 2026-04-27 (post-merge cleanup)
- **What**: Closeout Step 13b (`/experiment-paper-draft heilbron heilbron/v1-honest-repro`) skipped. A single-experiment paper draft for a SUGGESTIVE-lean-H₁ reproducibility study is too thin to constitute a paper contribution; the right artifact is a multi-experiment synthesis across the heilbron task's 10 completed experiments, which is the retrospective skill's job, not closeout's.
- **Category**: closeout / paper
- **Impact**: None on experiment closeout. Paper-draft is explicitly non-blocking per skill spec ("This step does NOT block closeout. If paper-draft fails for any reason, log the error to `04_issues_log.md` and continue."). When researcher decides to write a heilbron paper, invoke `/experiment-retrospective heilbron` first, then `/experiment-paper-draft heilbron <list-of-experiments>` against the synthesized result.
- **Root cause**: N/A — design decision on artifact granularity, not a failure.
- **Fix applied**: Logged here per skill guidance.
- **Systemic fix needed**: NO
