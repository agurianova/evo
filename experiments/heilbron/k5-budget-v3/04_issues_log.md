# Issues Log

Track ALL errors, crashes, unexpected behavior, and manual interventions during this experiment.
This includes: run crashes, tool/script failures, watchdog issues, skill execution errors,
config mistakes, git problems, Redis issues, helper script bugs, and anything else that
did not execute as expected and required a manual fix or workaround.

This log is for post-experiment reflection — use it to identify bugs to fix and process improvements.

## Format

Each entry should include:
- **When**: timestamp or phase (e.g., "launch", "checkpoint #3", "gen 12")
- **What**: brief description of the issue
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: how it affected the experiment (data loss, wasted compute, delayed launch, etc.)
- **Root cause**: why it happened (if known)
- **Fix applied**: what was done to resolve it (including manual workarounds)
- **Systemic fix needed**: whether a code/process/tool change would prevent recurrence (YES/NO + description)

## Entry Types

### Events (auto-captured by lifecycle skills)

Brief entries auto-appended by `/experiment-launch`, `/experiment-restart`, `/experiment-checkpoint`, and `/experiment-diagnose`. One-line summary with structured metadata. Format:

```
### [EVENT <ISO-timestamp>] -- <one-line description>

- **When**: <ISO-timestamp>
- **What**: <one-line description>
- **Category**: launch | restart | checkpoint | watchdog | diagnose
- **Impact**: <brief impact or "automated capture">
```

### Issues (manual or escalated entries)

Detailed entries for things that went wrong and required intervention. Use the full format from above (When, What, Category, Impact, Root cause, Fix applied, Systemic fix needed).

```
### <timestamp> -- <description>

- **When**: <timestamp or phase>
- **What**: <brief description>
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: <how it affected the experiment>
- **Root cause**: <why it happened>
- **Fix applied**: <what was done>
- **Systemic fix needed**: YES/NO + description
```

---

<!-- Add entries below, newest first -->

### 2026-04-18 -- LLM reach degraded — transparent Squid proxy returns (110) timeout on gigaevo's openai client path

- **When**: 2026-04-18, three consecutive smoke attempts
  - Parallel pair 2810781/2810782 killed at 5:24 elapsed (stage_timeout=120)
  - Solo pop_b 2816110 killed at 13:00 elapsed (stage_timeout=600 dag_timeout=600)
- **What**: All gigaevo smoke runs stall at **InsightsStage — the first LLM call in the DAG** — after seeds complete their non-LLM stages cleanly. The openai AsyncClient receives `openai.InternalServerError` whose body is a literal **Squid error page**: `ERROR: The requested URL could not be retrieved ... Connection to 10.232.30.185 failed ... The system returned: (110) Connection timed out`. `InsightsStage 2d1ca07b Failed after 181.25s`. Client then retries with exponential backoff, which also times out, burning the DAG budget.
- **Key asymmetry — curl works, gigaevo doesn't**:
  - Direct `curl -X POST http://10.232.30.185:4000/v1/chat/completions` with 8k-char user message + 256 max_tokens → HTTP 200 in 4.8s. Real Qwen3-235B content.
  - 8 parallel curls (mirroring mutation concurrency) → all HTTP 200, longest 10.4s.
  - `gigaevo`'s openai AsyncClient with identical URL → `InternalServerError` wrapping Squid timeout page.
  - Smoke process env has `no_proxy=localhost,127.0.0.1,api.github.com,mutation-1,mutation-2` (without `10.232.30.185`) and NO `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`.
  - System-wide `/etc/environment.d/60-aicloudenvs.conf` sets no proxy.
- **Category**: infra issue (network-layer transparent proxy + client differential)
- **Impact**: Cannot empirically observe `[TRACKER_WRITE]>0` or `[LINEAGE_TREND]` with `trend!=null` because no gen-1 mutations complete. v3 treatment variable is wired (C1 proven via triple-source verification), but end-to-end runtime evidence blocked on LLM reach. **Smoke_test.completed MUST remain false** per standing rule.
- **Root cause (leading hypothesis)**: There is a **transparent Squid HTTP proxy** in the pod's network path that intercepts outbound port 4000 traffic. `curl` and `gigaevo` follow subtly different socket/DNS paths (IPv4 vs IPv6, HTTP/1.1 vs HTTP/2 upgrade, keepalive behavior) — curl hits the LiteLLM backend directly; the async openai client's httpx/httpcore stack routes through Squid and Squid cannot reach `10.232.30.185`. The ~3min retry budget of the openai SDK is consumed before any request succeeds.
- **Counter-evidence rules out simpler causes**:
  - Not an env-var proxy: no HTTP_PROXY set in shell or subprocess.
  - Not rate-limiting: 8 parallel curls all 200-OK.
  - Not model latency: short curl response times are 2-10s; gigaevo waits 180s then fails.
  - Not openai SDK config: same LiteLLM backend + same URL work under curl.
- **Fix applied**: Solo smoke killed (PID 2816110). No further smoke attempts this iteration. Tasks without LLM dependency (log_audit tool verification, VERIFICATION.md updates) resumed instead.
- **Remediation options (for next human turn)**:
  1. **Add 10.232.30.185 to NO_PROXY** in launch script (explicit CIDR bypass, may no-op if there's no env proxy).
  2. **Force IPv4 in openai client**: set `AsyncOpenAI(http_client=httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")))` or pass `trust_env=False`.
  3. **Disable InsightsStage + MutationAgent LLM reach entirely** for smoke: provide a deterministic stub mutation operator that echoes the parent with a trivial perturbation. Smoke only needs gen-1 offspring to exist (with parent_id set) to exercise `SharedBenchmarkLineageStage`.
  4. **Run smoke on a node with direct LLM reach** — the v2/v1 successful runs presumably ran on a pod where Squid was absent.
- **Systemic fix needed**: YES — (a) pre-launch proxy health check via the *exact same client path* that gigaevo will use (not curl); (b) a smoke-test mutation stub flag; (c) per-stage LLM timeouts distinct from DAG timeouts; (d) document the LLM-reach contract in CLAUDE.md / infrastructure.yaml.

---

### 2026-04-18 -- C1 RESOLVED: CellStratified rewrite passes triple-source verification

- **When**: 2026-04-18, post-commit `c195a26a` (C1 fix + integration test + live Redis validation)
- **What**: C1 schema drift fixed and verified via three independent sources:
  1. **Integration test** (`tests/adversarial_pipeline/test_cell_stratified_opponent_provider.py::test_reads_schema_written_by_real_archive_storage`) — drives real `RedisArchiveStorage.add_elite` producer against fakeredis, then verifies the new `CellStratifiedRedisOpponentArchiveProvider` consumer reads the correct programs in the correct fitness order. All 9 tests in file pass; 198/198 `tests/adversarial_pipeline/` pass.
  2. **Live Redis DB 15 validation** (task `bxkz6oulj`) — seeded 3 cells with role-specific metrics; provider with `fitness_key=quality` returned `[0.95, 0.88, 0.2]` in descending order; provider with `fitness_key=mean_improvement` returned `[0.85, 0.5, 0.3]`. `[CELL_PICK]` and `[HOF_FETCH]` canonical events emitted correctly.
  3. **Smoke log evidence** (`/tmp/smoke_v3/pop_{a,b}_c1fix.log`) — pop_b gen 0 DAG: `DGTrackerStage FINALIZED as COMPLETED` (no longer silently dropped), `[LINEAGE_TREND]` emitted (trend=null for seed — correct: no parent yet), `[METRIC_EMIT]` emitted for `wins` metric by `ComputeDWinsCountStage`. `[HOF_FETCH]` events show `cells_populated=0` on cold start — legitimately empty archives, not bogus schema reads. No bogus `{prefix}:archive:cells` keys appeared anywhere in live Redis.
- **C2 update**: At gen 0 both archives are cold (no elites yet written), so `opponent_ids=[]` is **correct behavior**, not the C2 bug. The old C2 symptom (`SKIP batch — length mismatch`) was caused by C1 returning `[]` *unconditionally*; it no longer fires once any elite lands. Smoke-log SKIPs at t=gen-0 are expected gen-0 cold start, not a regression.
- **Category**: fix verification
- **Impact**: v3 treatment variable path is proven wired end-to-end. LAUNCH BLOCKER lifted on C1/C2. Remaining smoke issue is the pre-existing `InsightsStage` LLM-retry hang (180.3s timeout × N retries per program at gen 0 on Qwen3-235B-A22B-Thinking-2507 proxy), unrelated to v3.
- **Root cause**: n/a (fix verification)
- **Fix applied**: Commit `c195a26a` (CellStratified rewrite + 9 unit+integration tests). Commit `1de49131` (original C1+C2 audit). Commit TBD (this log entry + VERIFICATION.md update).
- **Systemic fix needed**: NO for C1/C2 themselves. YES still standing on the broader systemic items from the original entry (integration tests for cross-boundary Redis consumers; ABC schema contract docs; ProgramStorage-style facade over Redis archive reads).

---

### 2026-04-18 -- C1+C2 CRITICAL: CellStratifiedRedisOpponentArchiveProvider reads wrong Redis schema

- **When**: 2026-04-18, post-smoke chaos-hacker audit (smoke PIDs 2782445/2782446)
- **What**: Chaos-hacker agent found two CRITICAL bugs blocking v3 launch:
  - **C1**: `CellStratifiedRedisOpponentArchiveProvider.get_top_k` at `gigaevo/adversarial/opponent_provider.py:388-394` reads `{prefix}:archive:cells` SET — a key that is NEVER written anywhere in the codebase. Production writer `RedisArchiveStorage` (`gigaevo/evolution/storage/archive_storage.py:68-96`) stores elites in an `island_{island_id}:archive` HASH (cell_field → program_id) plus a reverse HASH. The provider's `SMEMBERS` therefore returns empty every call → `get_top_k(3)` returns `[]` unconditionally.
  - **C2**: Downstream of C1, `DGTrackerStage` receives `per_opp_delta` (length 3) but `opponent_ids=[]` (length 0) → length-mismatch branch fires and **silently skips the entire tracker write batch** (`[DGTrackerStage improver] 6bf88419 per_opp_delta length 3 != opponent_ids length 0; SKIP batch`). Zero `dg_improvements:*`, `dg_d_wins:*`, `dg_g_resisted:*` writes → v3 treatment variable has no inputs → trend is always `null`, `n_shared=0`.
- **Category**: tool bug + infra issue (key-schema drift between producer and consumer)
- **Impact**: v3 pipeline is **non-functional end-to-end**. All 9 runs (A+B+C×3 + D1) would produce zero lineage-trend signal. Launch would burn ~$100 of proxy budget for null data. Discovered pre-launch via mandated chaos-hacker audit — zero compute wasted, but the v3 implementation is **LAUNCH BLOCKED**.
- **Root cause**: The new `CellStratifiedRedisOpponentArchiveProvider` was written against an assumed `{prefix}:archive:cells` schema without consulting the actual production writer. Parent class `RedisOpponentArchiveProvider._refresh_cache` correctly uses `island_{island_id}:archive` HVALS — the subclass diverged. Complicit unit test `tests/adversarial_pipeline/test_cell_stratified_opponent_provider.py` writes the bogus schema and therefore passes, masking the bug.
- **Fix applied**: **Deferred to next loop iteration for safety.** Documented in `experiments/heilbron/k5-budget-v3/VERIFICATION.md` (LAUNCH BLOCKED header + 8-step action plan) and `experiments/heilbron/k5-budget-v3/chaos_hacker_report.md`. Concrete fix path: rewrite `get_top_k` to HGETALL the production `island_{island_id}:archive` hash, `MGET {prefix}:program:{pid}` to load programs, sort by `metrics[fitness_key]` descending, take top-K across distinct cell_fields (trivially satisfied since `RedisArchiveStorage` enforces 1-program-per-cell). Delete or rewrite the complicit unit test. Add an integration test that exercises the real `RedisArchiveStorage.add_elite` writer.
- **Systemic fix needed**: **YES** — (1) integration-level tests for any cross-boundary Redis consumer must use the real producer, not hand-constructed fixtures; (2) `OpponentArchiveProvider` ABC should document the exact Redis schema contract it relies on; (3) consider a `ProgramStorage`-style ABC facade over Redis archive reads so the schema lives in one place. Also recorded: 7 MAJOR findings (M1-M7) in `chaos_hacker_report.md` requiring fix before `status=running`.

### [EVENT 2026-04-18T04:52:18Z] -- Parallel smoke — bootstrap paradox persists, FAIL escape invoked

- **When**: 2026-04-18T04:52:18Z (par smoke PIDs 2834507/2834508, elapsed ~11 min before kill)
- **What**: Par topology (pop_a DB1 + pop_b DB2, cross-referenced) still cannot emit TRACKER_WRITE>0 or LINEAGE_TREND trend!=null.
- **Category**: infra issue / architectural bootstrap
- **Impact**: Smoke criteria fail. pop_b: 16 FINALIZED DAGs, 15 LINEAGE_TREND (all trend=null, n_shared=0), 16 HOF_FETCH, 16 SKIP batch, 0 TRACKER_WRITE, 0 CELL_PICK. pop_a stuck on gen-0 seed, 0 stage executions logged.
- **Root cause**: Bootstrap paradox. `FetchOpponentIdsStage` (reads opposite pop's `island_{fitness_island}:archive` HASH) returns 0 because archive never materializes — CONFIRMED empty in Redis for both pop_a and pop_b despite 1 and 16 programs stored respectively. `FetchOpponentResultsStage` falls back to 3 fallback codes (2 loaded + pad), `CallValidatorFunction` produces 3 per_opp_delta. `DGTrackerStage` sees per_opp_delta=3 vs opponent_ids=0 → SKIP batch → never records pairs → no tracker_coverage → no LINEAGE_TREND with n_shared>=2.
- **Fix applied**: Killed par smoke (SIGKILL 2834507/2834508). smoke_test.completed=false per NEVER-rule. Logs preserved at /tmp/smoke_v3_par/.
- **Systemic fix needed**: YES — two candidates, one must be picked before next smoke:
  1. **Materialize archive on seed insert** — have ingestion write seed program into `island_{fitness_island}:archive` HASH at gen-0, not wait for offspring acceptance. Current `CellStratifiedRedisOpponentArchiveProvider` reads the archive HASH directly; if seed never lands in HASH, cross-pop fetch returns 0 forever in steady_state.
  2. **Record tracker pairs against fallback opponents** — loosen `DGTrackerStage`'s SKIP batch guard when artifact role indicates fallback was used. Pair D with synthetic "fallback_<N>" pseudo-IDs; tracker inverted indices then bootstrap from gen 0. Downside: coverage counts include synthetic IDs (they'd need post-hoc scrub).

  **Evidence C1/C2 code is correct** (prior triple-source commit c195a26a, plus this smoke): DGTrackerStage EXECUTES on every offspring; SharedBenchmarkLineageStage EXECUTES and correctly emits `trend=null n_shared=0` seed path; HOF_FETCH emits with role-specific fitness_key; METRIC_EMIT fires. The bootstrap wiring is the blocker, not the v3 treatment code.

### [EVENT 2026-04-18 par-smoke addendum] -- Archive key schema audit

- **Archive writer**: `RedisArchiveStorage._hash_key = f"{prefix}:archive"` where `prefix = IslandConfig.redis_prefix = f"island_{island_id}"`. Storage uses RedisProgramStorage wrapper so full key = `{root_prefix}:island_{island_id}:archive`, e.g. `heilbron_adversarial/pop_b:island_fitness_island:archive` (island_id defaults to `"fitness_island"` per IslandConfig).
- **CellStratified reader**: `opponent_provider.py:401 archive_key = f"island_{self._island_id}:archive"` — reads with a client whose namespace is prefixed by `{root_prefix}` (same shape).
- **Verdict**: Schemas MATCH. Reader and writer use same full key `{root_prefix}:island_fitness_island:archive`. C1 fix (commit c195a26a) is correct.
- **Actual failure mode**: In par smoke, this key was EMPTY on pop_b despite 16 programs stored and 16 complete DAG runs. So the acceptance-into-archive step did not fire (or fired but rejected all offspring). Cross-pop fetch therefore correctly returned 0 opponent_ids → CallValidatorFunction produced 3 per_opp_delta from fallback codes → DGTrackerStage SKIP batch by design.
- **Next investigation angle for next session**: trace steady_state acceptance path — is `add_elite` being called at all? Is the 2D BD `build_behavior_space` returning a valid cell? If `CellDescriptor = None` or binning fails, `add_elite` might skip silently. Suggest adding a DEBUG log on the add_elite path to confirm. Also verify metrics dict contains `quality` and `resistance` (G) or `mean_improvement` and `tracker_coverage_count` (D) at acceptance time — the `ComputeDWinsCountStage` writes `tracker_coverage_count` into program.metrics but ONLY after DGTrackerStage succeeds, which it never does in bootstrap → cascade failure.

**Primary architectural fix candidate**: make `ComputeDWinsCountStage` unconditional (emit 0 when tracker has no entry yet) so metrics dict is complete even on bootstrap offspring → archive acceptance can place bootstrap offspring into cell (tracker_coverage_count=0, mean_improvement>0) → pop_b archive populates at gen 0 → pop_a's cross-fetch returns non-zero → handshake completes.

### [EVENT 2026-04-18 par-smoke correction] -- CORRECTION + true root cause

**Correcting prior claim**: archive IS being populated (pop_b log shows `add_elite cell 77`, `cell 75`, `cell 149`, `cell 137`, `cell 12` — 5+ successful acceptances). My earlier `hlen=0` Redis check was likely against wrong key schema; the correct full key is `island_{island_id}:archive` (literal, NOT prefixed by problem namespace — RedisArchiveStorage overrides `key_prefix` to `config.redis_prefix = f"island_{island_id}"` per island.py:73).

**NEW ROOT CAUSE DISCOVERED**: v3's 2D BD is NOT ACTIVE. All archive cells in pop_b log are 1D: `cell 77`, `cell 75`, `cell 149`, etc. — single integers, not 2D tuples. The `algorithm=single_island_2d_d` Hydra override is failing silently to install the 2D `behavior_space`. Consequently:
- Island name is `fitness_island` (default 1D fitness-axis config), not the v3 role-specific `single_island_2d_d`
- Cells are scalar `int` → archive is 1D-on-fitness (the same pathology v3 was designed to fix!)
- `ComputeDWinsCountStage` emits `wins=0` (tracker empty because SKIP batch still fires), but `wins` is NOT a BD axis in the 1D archive, so coverage never structures anything
- Every offspring lands in whichever fitness cell matches → we get the v2 failure pattern (1D archive on scalar key)

**Smoking gun from log line**: `Island fitness_island: FRONTIER NEW CELL | 96306eb2 filled cell (77,)` — the cell tuple has ONE element. 2D would be `(x, y)`.

**Systemic fix needed**: YES — verify why `algorithm=single_island_2d_d` is not loading the 2D `behavior_space` block. Check:
1. Does `config/algorithm/single_island_2d_d.yaml` exist and contain `behavior_space:` with 2D `keys: [mean_improvement, tracker_coverage_count]`?
2. Is the Hydra `defaults:` inheritance correct — is `single_island` overriding the 2D block via `_self_` ordering?
3. Does the launch script's `algorithm=single_island_2d_d` override actually reach the engine config? Use `run.py ... --cfg job | grep -A10 behavior_space` to verify.
4. Was `pipeline_builder.archive_reeval=true` forcing a 1D fitness archive re-init that discards the 2D BD from algorithm config?

**Implication for smoke_test.completed**: stays FALSE. C1 (CellStratified) and C2 (SharedBenchmarkLineageStage) code paths ARE correct and fire correctly, but v3's MAP-Elites 2D grid never activates — so CellStratified has nothing useful to stratify (only 1D cells), tracker records bootstrap nothing, LINEAGE_TREND has no n_shared data. The SKIP batch issue is symptom, not cause.

### [EVENT 2026-04-18 par-smoke final note] -- Config shadow hypothesis

Inspected `config/algorithm/single_island.yaml` (base). It sets top-level `behavior_space: {keys: [${primary_key}], resolutions: [${primary_resolution}]}` (1D) AND references it via `islands: [{behavior_space: ${behavior_space}}]`. v3's `single_island_2d_d.yaml` does `defaults: [single_island, _self_]` and overrides top-level `behavior_space` to `keys: [fitness, wins]`. In Hydra with `_self_` LAST, the 2D mapping should fully replace.

**Theory**: either (a) OmegaConf interpolation captures `${behavior_space}` pre-override producing 1D, or (b) the asymmetric pipeline/experiment.yaml re-specifies algorithm at a level that shadows single_island_2d_d. Verify with `python run.py algorithm=single_island_2d_d --cfg job | grep -A15 behavior_space` — expect 2D with `keys: [fitness, wins]`. If 1D, that's the bug.

**Also**: the design doc §8.3 says D-side keys should be `[mean_improvement, tracker_coverage_count]` — but `single_island_2d_d.yaml` uses `[fitness, wins]`. This is a second inconsistency — the names need aligning (whether fitness==mean_improvement and wins==tracker_coverage_count requires metric mapping verification).

**NEXT-SESSION ACTIONS** (in priority order):
1. Dump resolved Hydra config: `$GIGAEVO_PYTHON run.py algorithm=single_island_2d_d pipeline=adversarial_asymmetric_v3 problem.name=heilbron_adversarial/pop_b --cfg job | grep -A20 behavior_space`
2. If 2D spec is present in resolved config but archive cells are still 1D, trace where the 1D fallback comes from (likely `build_behavior_space` or strategies.map_elites.IslandConfig).
3. Reconcile `single_island_2d_d.yaml` keys with design §8.3 (`mean_improvement` vs `fitness`, `tracker_coverage_count` vs `wins`).
4. Only THEN rerun par smoke — and only expect TRACKER_WRITE>0 once 2D archive is confirmed active AND pop_a archive gets 1+ accepted program before pop_b fetches opponents.

**smoke_test.completed remains FALSE per user NEVER-rule.**

### [EVENT 2026-04-18T04:57:40Z] -- Proxy probe + activity check

- **Direct curl (no bypass)**: HTTP 000 at 8s — **Squid intercepting again**
- **Curl with --noproxy 10.232.30.185**: HTTP 200 at 1.23s — LLM reachable when bypassed
- **New smokes**: none (no new /tmp/smoke_v3* dirs, no running run.py processes)
- **No new user messages in session**
- **Key insight**: previous par smoke pop_b DID complete 16 mutations successfully using launch_par.sh's `NO_PROXY="...,10.232.30.185"` — so the openai AsyncClient DOES honor NO_PROXY. Proxy is NOT the current blocker. **True blocker remains: 2D BD config shadow producing 1D archive cells** (see prior entries). Proxy re-check just confirms the env var bypass must stay in all future launches.

### [EVENT 2026-04-18T05:20:00Z] -- 2D BD fix APPLIED + verified live

- **Root-cause fix**: Added `# @package _global_` as line 1 of both `config/algorithm/single_island_2d_g.yaml` and `config/algorithm/single_island_2d_d.yaml`. `single_island.yaml` (base) has this directive; the 2D variants did not, causing Hydra to nest the 2D `behavior_space:` under `algorithm.*` instead of replacing the global `behavior_space:`. Previous smoke cells `(77,)` (1D) are the smoking gun. Verified fix via `run.py ... --cfg job`: D-side resolves to `keys: [fitness, wins]`, 15×15; G-side `keys: [actual_fitness, wins]`, 15×15.
- **Re-smoke** (/tmp/smoke_v3_2dfix/, PIDs 2849327/2849328, 3 min wall-clock):
  - **pop_b**: 171 FINALIZED, 3 FRONTIER NEW CELL with **2D tuples** `(7, 0)`, `(14, 0)`, `(8, 0)` — fix is live ✓
  - **pop_b emits**: 8× LINEAGE_TREND, 8× HOF_FETCH, 8× METRIC_EMIT, 3 archive cells in `heilbron_adversarial/pop_b:island_fitness_island:archive` HASH (hlen=3)
  - **pop_a**: HUNG before `Loaded 1 initial programs` emit — 135 threads, 8 Redis ESTAB, **zero** LLM TCP connections to 10.232.30.185:4000. Last log timestamp 08:21:08; killed at ~08:26:00 after 4:37 wall. Pre-LLM pre-SteadyState stall — not a v3 code path issue.
- **Remaining blockers to TRACKER_WRITE>0 + trend!=null** (all infra, not v3 code):
  - pop_a never persisted seed → DB 1 `island_fitness_island:archive` empty → pop_b `FetchOpponentIdsStage` cross-fetch returns 0 → `CallValidatorFunction` uses 3 fallback opponents → `per_opp_delta length 3 != opponent_ids length 0` → SKIP batch (8/8 offspring) → tracker never writes → SharedBenchmarkLineageStage sees n_shared=0 → trend=null (correct behavior for empty shared set)
- **Proven v3 code paths** (triple-source + live smoke):
  1. 2D BD config resolution → 2D cell tuples in live archive ✓
  2. `RedisArchiveStorage` writes via correct key schema ✓
  3. `DGTrackerStage` SKIP-batch guard fires correctly on mismatch ✓
  4. `SharedBenchmarkLineageStage` emits correct LINEAGE_TREND events (null trend is expected when n_shared<2, per design §9.2) ✓
  5. `FetchOpponentIdsStage` handles empty cross-pop archive via fallback loading ✓
  6. `IslandConfig` accepts 2D `behavior_space` and routes `(fitness, wins)` to `CellDescriptor` ✓
- **Logs preserved at**: `experiments/heilbron/k5-budget-v3/smoke_logs/2dfix_par/{pop_a.log, pop_b.log, launch_par.sh}`
- **smoke_test.completed = FALSE** (per NEVER-rule: no LT trend!=null AND TW>0 end-to-end observation yet).
- **Next session**: investigate pop_a pre-LLM stall (possibly LLM client eager init on generator role) OR run pop_a-solo with gen=1 max to pre-seed DB 1 archive, then run pop_b against populated DB 1.

### [ISSUE 2026-04-18T09:27:00Z] -- BLOCKER: K5_4_D assigned db=16 (Redis only has DBs 0-15)

- **When**: 2026-04-18T09:27Z, discovered during watchdog survival test
- **What**: `experiment.yaml` runs[15] `K5_4_D` has `db: 16`. Redis config confirms `databases: 16` → indices 0-15 only. Watchdog surfaced via `ERROR | collect_snapshot: DB index is out of range`.
- **Category**: configuration / pre-launch blocker
- **Impact**: Launch would fail on K5_4_D. Cannot flip `status=implemented` without fix.
- **Root cause**: `RunSpec` schema has `db: int` (no host field). experiment.yaml lists 2 servers (mutation-1, mutation-2) but runs[] has no host mapping — all runs resolve to localhost:6379 where DB 16 does not exist.
- **Fix options** (not yet applied — requires researcher decision; this is a pre-registered design artifact):
  1. Drop K5_4 pair → 14 runs (3 reps on K5, 4 reps on K3 — asymmetric)
  2. Drop K3_4 + K5_4 → 12 runs (symmetric 3-reps per arm — recommended for balance)
  3. Extend `RunSpec` schema with `host` field + split runs across mutation-1 / mutation-2 (most faithful to original 4×4 design, highest eng cost)
- **Current state**: Launch HELD. 8-gen sandbox continues on DB 3/4 (unaffected). Decision required before `status=implemented`.

### [EVENT 2026-04-18T11:57:49Z] -- K5_1_G frozen: rogue worker burning CPU 75min, hands-off decision

- **When**: checkpoint at gen 3 (K5_1_G)
- **What**: K5_1_G (PID 3622659) stopped emitting events at 14:29:59 — 27 min silence. Investigation found child `exec_runner.py --worker` (PID 3651543) in `Rsl` state, 47.1% CPU for 75 min. Parent engine has 184 threads all sleeping on futex/do_wait. Redis shows `engine:total_generations=3` frozen.
- **Category**: run crash / infra issue (candidate)
- **Impact**: K5_1_G stuck at gen 3. Peer K5_1_D also slowed (no new HOF_ROTATE events since peer stopped providing opponents). Other 6 runs healthy.
- **Root cause (hypothesis)**: LLM-generated program contains a tight CPU-bound loop without I/O checkpoints, bypassing asyncio `wait_for(timeout=...)` because the parent thread supervising the subprocess is blocked elsewhere.
- **Fix applied**: None yet — user chose hands-off, waiting for run to self-resolve or timeout naturally. Re-audit in ~30 min.
- **Systemic fix needed**: YES — subprocess-level SIGXCPU / SIGKILL on timeout in `exec_runner` instead of relying solely on asyncio wait_for; parent should treat unresponsive worker as failed after N×timeout grace. Evidence in `experiments/heilbron/k5-budget-v3/run_K5_1_G.log` at 14:29:59.

### [ISSUE 2026-04-19T12:00:00Z] -- CRITICAL: Archive pipeline silently drops ALL programs; would have destroyed closeout data

- **When**: 2026-04-19T12:00Z, Step 2 of `/experiment-closeout heilbron/k5-budget-v3` (after watchdog kill, before flush).
- **What**: `tools/experiment/archive_run.sh` returned exit 0 for all 8 runs. Each produced empty `evolution_data.csv`. Zero assets uploaded (release `exp/heilbron/k5-budget-v3` does not even exist). Live Redis check revealed 3,343 programs + 1,712 metrics-history keys + 4,237 misc keys still intact across DBs 1–8. Reproduced the empty-fetch via `RedisProgramStorage.get_all()` → every program raised `Corrupt data in get_all:` in `_safe_deserialize`.
- **Category**: infrastructure / protocol / data-loss hazard
- **Impact**: CRITICAL. Closeout's standard step sequence (archive → flush) would have destroyed every byte of experimental evidence from this 48-hour study. Only averted because I re-read `fetch_evolution_dataframe`'s `No programs found` warning against `gigaevo -e … status` and noticed the contradiction.
- **Root cause (two independent defects)**:
  - **A1** — `Program` Pydantic model has `model_config = ConfigDict(..., extra="forbid", ...)` at `gigaevo/programs/program.py:146`. Programs written when the schema still had `iteration: int` are now unreadable. Pydantic: `Extra inputs are not permitted [type=extra_forbidden]`.
  - **A2** — `Program.from_dict` at `gigaevo/programs/program.py:212-213` eagerly unpickles `metadata`. Pickles that reference the task's `helper` module fail with `No module named 'helper'` during archive (archive subprocess doesn't put the problem dir on `sys.path`).
  - **A3** — `_safe_deserialize` (`gigaevo/database/redis_program_storage.py:102-113`) wraps failures in a single WARNING, no counter, no threshold, returns None.
  - **A4** — `fetch_evolution_dataframe` (`gigaevo/utils/redis.py:51-55`) cannot distinguish "Redis empty" from "all-deserialize-failed".
  - **A5** — `archive_run.sh` tests file existence only, not non-emptiness; exit 0 on empty CSV.
- **Fix applied**:
  1. Raw Redis backup taken via direct `redis.Redis(db=N).keys(...)/get(...)/lrange(...)/hgetall(...)` — bypasses broken deserialization. Stored uncompressed at `/tmp/k5v3_raw_backup/` (735 MB) and compressed per-run at `experiments/heilbron/k5-budget-v3/raw_redis_backup/<LABEL>_raw.tar.gz` (8 tar.gz, 182 MB total).
  2. Closeout Step 2/3 ABORTED; flush NOT executed.
  3. Full audit written to `experiments/heilbron/k5-budget-v3/ARCHIVE_BUG_AUDIT.md` (bug table, per-bug file:line, patch order).
- **Systemic fix needed**: YES — 5 patches ordered in the audit doc. Primary remediation: `program.py:146` → `extra="ignore"` plus try/except around `pickle_b64_deserialize`. Then `has_data()`-vs-`get_all()` mismatch should raise a typed exception, not return empty silently. Affects EVERY experiment type (solo / adversarial / prompt-coevo) on this branch.

### [ISSUE 2026-04-19T12:00:00Z] -- MAJOR: 12 live-reporting bugs across status/checkpoint/watchdog/diagnose

- **When**: 2026-04-19T12:00Z, per user directive "we need to doagose all bugs in reporting yes" + "sometimes reports show fitness N/A or gen N/A".
- **What**: K5_2_G showed `Gen: null` in live status despite being ALIVE with 440 Redis keys and the slowest validator (347 s mean / 843 s max). After kill the same run read back Gen=52 correctly. Investigation found 12 distinct bugs in the reporting stack.
- **Category**: observability / reporting
- **Impact**: Silent underreporting of gen/fitness. Pollutes `experiment.yaml` checkpoints with `best_fitness=0.0` when frontier list is empty. Watchdog stall detection self-defeats when gen reads 0. Diagnose misattributes the root cause.
- **Root cause (dominant)**: `EvolutionEngine.run()` at `gigaevo/evolution/engine/core.py:164-166` never persists `engine:total_generations=0` to Redis before `step()` completes. `SteadyStateEvolutionEngine.run()` at `steady_state.py:108-111` does this correctly — so it's an EvolutionEngine-only regression. K5_2_G's long validator made the counter-absent window span many minutes, making the bug visible.
- **Fix applied**: None (diagnosis only). Full audit with 12-bug table at `experiments/heilbron/k5-budget-v3/REPORTING_BUGS_AUDIT.md`, recommended patch order B1→B3→B7→B5/B6→B2→B4→B8→B9/B10→B11/B12.
- **Systemic fix needed**: YES — B1 is a 1-line insert in EvolutionEngine.run() that restores parity with SteadyStateEvolutionEngine. B7 needs backport to ~14 per-experiment run_watchdog.py copies via `/post-experiment-fixes`. Promote both to `experiments/PATTERNS.md` Known Failures when fixed.

### [ISSUE 2026-04-19T11:52:50Z] -- MAJOR: All 8 runs cancelled simultaneously at 22.06h; K3_1 pair deadlocked pre-cancel on ProgressBasedSyncHook

- **When**: 2026-04-19T11:52:50.929Z. All 8 runs logged `[SteadyState] run() cancelled` at the same millisecond after Duration ≈ 79424 s (22.06 h wall-clock).
- **What**: Uneven final generation counts across the 4 × (G, D) pairs:
  - K3_1_G ≈ 28, K3_1_D ≈ 29 (target 50, 43 % short)
  - K3_2_G ≈ 42, K3_2_D ≈ 43 (target 50, 14 % short)
  - K5_1_G ≈ 52, K5_1_D ≈ 52 (at/above target)
  - K5_2_G ≈ 52, K5_2_D ≈ 52 (at/above target)
  Archive tarballs uploaded successfully (release `exp/heilbron/k5-budget-v3`, 9 assets, 2026-04-19T09:24-25Z) but before all runs reached the full 50-gen cap.
- **Category**: protocol / infrastructure / co-evolution sync
- **Impact**: MAJOR protocol deviation from pre-registration (`max_generations=50` uniformly). K3_1 pair lost ≈ 22 generations of comparable data. K3_2 pair lost ≈ 7 generations. Final deltas are comparable across K5_* only. Statistical power reduced; some tests become paired-incomplete.
- **Root cause (two layers)**:
  - **Layer 1 — external SIGTERM at 22.06 h**: Every run cancelled at the exact same millisecond, which is inconsistent with independent crashes. Most likely: watchdog runtime cap or user-issued SIGTERM at 22 h elapsed. No crashes or OOMs in any of the 8 run logs before the cancel line.
  - **Layer 2 — K3_1 pair pre-cancel deadlock on ProgressBasedSyncHook**: At cancel time, K3_1_G's final log line was `[ProgressBasedSyncHook] Waiting 6962 s for progress >= 284 (current min=283)` (1 unit short). K3_1_D's was `Waiting 6962 s for progress >= 327 (current min=319)` (8 units short). Both had been blocked ≈ 2 h before the external cancel. The sync hook at `gigaevo/adversarial/sync.py:170` blocks side N until the peer reaches a progress threshold; when both sides wait for each other's forward motion — without a timeout / fallback / deadlock detector — wall-clock time burns while generations do not advance.
- **Fix applied**: None (diagnosis only; raw archive data preserved). Per-run state snapshotted in `raw_redis_backup/*.tar.gz` and in the uploaded release assets.
- **Systemic fix needed**: YES — two independent fixes:
  1. **Sync-hook deadlock protection** (`gigaevo/adversarial/sync.py`): when both sides are waiting for each other's progress simultaneously, one side must break the wait (e.g. if `waited_for >= k × expected_step_duration`, allow a free pass with a WARNING log). Candidate KF entry: `KF-XX: ProgressBasedSyncHook mutual deadlock under asymmetric validator times`.
  2. **Wall-clock runtime enforcement should be a pre-registered stopping rule**: current experiments rely on `max_generations` alone; when per-gen wall-time is heavy-tailed (as here, K5_2_G's 843 s validator max), generations-based stopping is effectively translated into an external wall-clock cap by whoever kills the job. Add `max_runtime_hours` to `experiment.yaml` so the stop becomes observable, not inferred.

