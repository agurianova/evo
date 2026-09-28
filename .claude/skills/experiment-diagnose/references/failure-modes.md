# Failure Mode Catalog

Comprehensive reference for diagnosing GigaEvo experiment run failures.
Organized by layer, from most visible (process) to deepest (data).

---

## Layer 1: Process-Level

### 1.1 Run process crashed
- **Symptom**: PID gone, log ends with traceback
- **Check**: `kill -0 <pid>` returns error
- **Log pattern**: Python traceback at end of log file
- **Common causes**: OOM, unhandled exception in engine loop, import error
- **Fix**: Check last 100 lines of log, fix root cause, relaunch

### 1.2 Run process hung
- **Symptom**: PID alive, but iteration count frozen for hours
- **Check**: Iteration count unchanged between two checks 30min apart
- **Log pattern**: No new log lines for extended period
- **Common causes**: Redis connection deadlock, asyncio event loop blocked, infinite loop in user code
- **Fix**: Kill process, check Redis connectivity, relaunch

### 1.3 Run process killed externally
- **Symptom**: PID gone, no traceback in log, log ends mid-line
- **Check**: `dmesg | grep -i oom` or `dmesg | grep <pid>`
- **Common causes**: OOM killer, machine reboot, user kill
- **Fix**: Check system logs, increase memory if OOM, relaunch

---

## Layer 2: Evolution Engine

### 2.1 Step timeout
- **Symptom**: Iterations take much longer than expected, some skipped
- **Log pattern**: `[EvolutionEngine] step() timed out after Xs`
- **Metric**: Iteration timestamps in Redis show irregular spacing
- **Common causes**: LLM server slow, stage_timeout too low, Redis slow
- **Fix**: Increase `stage_timeout` / `dag_timeout` in config, check LLM server health

### 2.2 Step failure (non-timeout)
- **Symptom**: Iteration count advances but programs aren't improving
- **Log pattern**: `[EvolutionEngine] step() failed:` with traceback
- **Common causes**: Redis connection error, storage corruption, acceptor bug
- **Fix**: Read traceback, fix root cause

### 2.3 All mutations failing
- **Symptom**: `mutations_creation_errors` high, `mutations_created` low
- **Log pattern**: `[mutation] Task X: Failed to generate/persist mutation:`
- **Metric**: `rejected_validation` increasing while `added` stagnant
- **Common causes**: LLM server returning errors, prompt format error, empty code from LLM
- **Fix**: Check LLM server, check prompt templates, check mutation_url reachability

### 2.4 All programs rejected by acceptor
- **Symptom**: Programs evaluated but never added to archive
- **Log pattern**: `[EvolutionEngine] Program X rejected by acceptor`
- **Metric**: `rejected_validation` >> `added`
- **Common causes**: validate.py return type mismatch (tuple vs dict), missing metric keys, fitness always <= 0
- **Fix**: Check validate.py return type matches pipeline, check required metric keys

### 2.5 Strategy rejecting everything
- **Symptom**: Programs pass validation but rejected by strategy
- **Log pattern**: `[EvolutionEngine] Program X rejected by strategy`
- **Metric**: `rejected_strategy` >> `added`
- **Common causes**: MapElites cells full, significant_change too high, diversity threshold
- **Fix**: Lower `significant_change`, check strategy config

---

## Layer 3: DAG / Pipeline Stages

### 3.1 DAG timeout
- **Symptom**: Programs take forever, eventually discarded
- **Log pattern**: `[DAG][X] DAG run timed out after Xs`
- **Metric**: `dag_timeouts` > 0 in dag_runner metrics
- **Config**: `dag_timeout` (default 3600s)
- **Common causes**: stage_timeout too high (stages run full timeout), eval function slow, infinite loop in program code
- **Fix**: Lower `dag_timeout` and `stage_timeout`, check eval timing

### 3.2 DAG deadlock
- **Symptom**: DAG hangs, then fails with RuntimeError
- **Log pattern**: `[DAG] DEADLOCK: Automata requested skips=X but none could be applied`
- **Common causes**: Pipeline misconfiguration, circular dependencies
- **Fix**: Check pipeline YAML for stage dependency errors

### 3.3 DAG stall
- **Symptom**: DAG running but no progress
- **Log pattern**: `[DAG] STALLED (no progress for Xs). Diagnostics:`
- **Common causes**: Stage waiting for resource, asyncio deadlock
- **Fix**: Check which stage is blocked (from diagnostics), check resources

### 3.4 Stage timeout cascade
- **Symptom**: Many stages timing out, most programs invalid
- **Log pattern**: `[StageName] TIMED OUT after X.XXs (timeout=Ys)`
- **Metric**: `stage_failure` counts high
- **Common causes**: `stage_timeout` too low for problem complexity, eval function slow on hard inputs
- **Fix**: Increase `stage_timeout`, profile eval function timing

### 3.5 Stage input validation failure
- **Symptom**: Stage fails immediately (0s duration)
- **Log pattern**: `[StageName] Missing required inputs:` or `Unknown input fields:`
- **Common causes**: Pipeline wiring error, stage output/input type mismatch
- **Fix**: Check pipeline YAML stage connections

---

## Layer 4: Program Validation & Execution

### 4.1 Syntax errors in generated code
- **Symptom**: High invalidity, programs rejected at validation
- **Log pattern**: `SyntaxError at line X, offset Y:`
- **Common causes**: LLM generating malformed code, bad prompt instructions
- **Fix**: Check mutation prompts, check LLM model capability

### 4.2 Security violations
- **Symptom**: Programs rejected for importing forbidden modules
- **Log pattern**: `SecurityViolationError: Forbidden import: X`
- **Common causes**: LLM generating code with os/sys/subprocess imports
- **Fix**: Add security constraints to mutation prompt

### 4.3 Code execution error
- **Symptom**: Programs compile but crash during evaluation
- **Log pattern**: Error dict with `_error=True, stderr=...`
- **Common causes**: Runtime error in generated code (IndexError, TypeError, etc.)
- **Fix**: This is expected — evolution should select away from these. Only a problem if >90%

### 4.4 Code execution timeout
- **Symptom**: Programs take too long to evaluate
- **Log pattern**: Stage timeout for CallValidatorFunction or CallProgramFunction
- **Common causes**: Generated code has O(n^3+) complexity, infinite loops
- **Fix**: Lower stage timeout, add complexity limits to prompt

---

## Layer 5: LLM / Mutation

### 5.1 LLM server unreachable
- **Symptom**: No mutations generated, all mutation tasks fail
- **Log pattern**: `[MutationAgent] Structured LLM call failed: ConnectionError`
- **Check**: `curl -s <mutation_url>/v1/models`
- **Common causes**: Server down, wrong IP, NO_PROXY not set, network issue
- **Fix**: Check server status, verify NO_PROXY includes server IP

### 5.2 LLM rate limiting
- **Symptom**: Mutations intermittently fail, 429 errors
- **Log pattern**: `RateLimitError` or HTTP 429
- **Common causes**: Too many concurrent requests, API quota exceeded
- **Fix**: Reduce concurrency, check API quotas

### 5.3 LLM returning empty/invalid responses
- **Symptom**: Mutations created but code is empty
- **Log pattern**: `Failed to extract code from LLM response`
- **Common causes**: Model confused by prompt, structured output schema mismatch, model not supporting thinking mode
- **Fix**: Check prompt quality, verify model supports structured output

### 5.4 Wrong model loaded on server
- **Symptom**: Mutations poor quality, model name mismatch
- **Check**: Compare `curl <url>/v1/models` with `experiment.yaml runs[].model_name`
- **Common causes**: Server restarted with different model, model swap
- **Fix**: Restart server with correct model, or update experiment config

### 5.5 Thinking mode not active
- **Symptom**: Mutations lower quality than expected, no `<think>` in responses
- **Check**: Send test prompt, check for `<think>` tag in response
- **Common causes**: Server config changed, model doesn't support thinking
- **Fix**: Verify server thinking mode config

### 5.6 Prompt loading failure
- **Symptom**: Agent fails at initialization, no mutations
- **Log pattern**: `FileNotFoundError` for prompt file
- **Common causes**: `prompts_dir` wrong path, file missing, prompts_dir not in pipeline YAML
- **Fix**: Verify prompts_dir path, check both evolution_context and mutation_operator blocks

---

## Layer 6: Redis

### 6.1 Redis connection failure
- **Symptom**: Run crashes or hangs
- **Log pattern**: `[RedisConnection] X failed:` or `StorageError`
- **Check**: `redis-cli -h localhost -p 6379 ping`
- **Common causes**: Redis server down, wrong port, memory full
- **Fix**: Restart Redis, check `redis-cli info memory`

### 6.2 Wrong Redis DB
- **Symptom**: Run sees stale data from another experiment
- **Check**: `redis-cli -n <db> keys "*:run_state"` — should show only this experiment's prefix
- **Common causes**: DB not flushed before launch, DB collision with another experiment
- **Fix**: Flush DB with `gigaevo flush --db <N> --confirm`, use DB claims

### 6.3 Redis data corruption
- **Symptom**: Sporadic errors reading programs
- **Log pattern**: `[RedisProgramStorage] Corrupt data in X:`
- **Common causes**: Partial writes, concurrent modification
- **Fix**: If sporadic, ignore (engine handles it). If persistent, flush and relaunch

---

## Layer 7: Config / Data

### 7.1 Pipeline mismatch
- **Symptom**: validate.py returns tuple but pipeline=standard, or vice versa
- **Effect**: Fitness never computed correctly, all programs invalid
- **Check**: Read validate.py return type, compare with pipeline YAML
- **Fix**: Use `pipeline=hover_feedback` or `hotpotqa_asi` for tuple return, `standard` for dict

### 7.2 Missing seed programs
- **Symptom**: Run starts but immediately has 0 programs
- **Check**: `ls chains/<prefix>/initial_programs/`
- **Fix**: Create seed programs

### 7.3 Dataset missing or corrupted
- **Symptom**: validate.py crashes on all inputs
- **Log pattern**: `FileNotFoundError` or `KeyError` in validation stage
- **Check**: Verify dataset files exist and SHA matches
- **Fix**: Re-download or regenerate dataset

### 7.4 Config parameter miscalibration
- **Symptom**: Run works but is inefficient
- **Signs**: stage_timeout >> actual eval time (wasting time on failures), max_mutations too high (overwhelming LLM), significant_change too high (rejecting good programs)
- **Fix**: Profile eval timing, adjust configs based on CONTEXT.md recommendations

---

## Layer 8: Task-Specific / Hydra Composition

These failures arise from mismatches between independently-configured components that Hydra composes at runtime. They are invisible until DAG execution because Hydra resolves configs lazily.

**Key diagnostic tool**: `python run.py <overrides> --cfg job` dumps the fully-resolved config. Read it to verify composition.

### 8.1 Pipeline <-> task mismatch
- **Symptom**: Crash or silent metric corruption in first iteration
- **Check**: `pipeline_builder._target_` in `--cfg job` output references a task-locked PipelineBuilder (e.g., `ASIPipelineBuilder`) but `problem.name` is for a different task
- **Example**: `pipeline=hotpotqa_asi` with `problem.name=chains/hover/static` — the HotpotQA formatter will crash on HoVer failure dicts
- **Common causes**: Copy-paste from another experiment's launch config
- **Fix**: Use the correct pipeline for the task (see `config/pipeline/*.yaml` header comments)

### 8.2 Pipeline <-> validate.py return type mismatch (repr-contamination)
- **Symptom**: 100% invalidity or garbled fitness values from gen 1
- **Check**: validate.py returns `(metrics, failures)` tuple but pipeline=standard (which calls `repr()` on the full return)
- **Log pattern**: Fitness values are string representations of tuples, not floats
- **Common causes**: validate.py was changed to return feedback tuple but pipeline override wasn't updated
- **Fix**: Use `pipeline=hover_feedback` or `hotpotqa_asi` for tuple-returning validate.py. See PR #67.

### 8.3 Wrong prompts for task
- **Symptom**: LLM generates poor mutations, uses wrong domain vocabulary
- **Check**: `prompts_dir` in `--cfg job` points to another task's prompts (e.g., `prompts/hotpotqa` for a hover run)
- **Common causes**: `prompts=hotpotqa` override left in launch command from previous experiment
- **Fix**: Use `prompts=default` (package defaults) or the correct task-specific prompts config

### 8.4 prompts_dir path does not exist
- **Symptom**: Crash at InsightsStage or MutationAgent initialization
- **Log pattern**: `FileNotFoundError` for prompt template file
- **Check**: `prompts_dir` in `--cfg job` resolves to a non-existent path
- **Common causes**: Prompt dir renamed/moved, Hydra interpolation failed
- **Fix**: Verify path exists; use `prompts=default` to fall back to package defaults

### 8.5 Missing formatter.py for feedback pipeline
- **Symptom**: ImportError at pipeline build time
- **Check**: Feedback pipeline (`hover_feedback`, `hotpotqa_asi`) requires `formatter.py` in the problem dir
- **Common causes**: New problem variant copy-pasted without formatter
- **Fix**: Create formatter.py with appropriate FormatterStage subclass

### 8.6 Custom PipelineBuilder not found
- **Symptom**: ImportError or ModuleNotFoundError at startup
- **Log pattern**: `ModuleNotFoundError: No module named 'problems.chains...'`
- **Check**: `pipeline_builder._target_` in `--cfg job` references a Python path that doesn't exist
- **Common causes**: pipeline.py not created in problem dir, typo in pipeline YAML
- **Fix**: Create the PipelineBuilder class or fix the _target_ path

### 8.7 Hydra override order conflict
- **Symptom**: Config values differ from what launch.sh specifies
- **Check**: Compare launch.sh CLI overrides against `--cfg job` output
- **Common causes**: Hydra config group defaults override CLI values, or YAML merge keys collide
- **Fix**: Read `cfg_run_<label>.txt` carefully; later overrides win in Hydra
