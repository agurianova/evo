# Implementation Plan: heilbron/k5-budget-loose

**Goal**: Produce all artifacts needed for smoke test (experiment.yaml runs, launch.sh, watchdog, treatment verification).

**Scope**: Config-only experiment. No new Python code. 12 runs using existing `adversarial_asymmetric` pipeline.

**Template**: `experiments/heilbron/asymmetric-iterations-v2/experiment.yaml` (16 runs, same pipeline)

---

## Task 1: Fill experiment.yaml runs[] (12 runs)

**Action**: Add 12 run entries to experiment.yaml. 6 treatment pairs (T1-T3) + 6 control pairs (C1-C3).

**Files**: `experiments/heilbron/k5-budget-loose/experiment.yaml`

**Spec** (from 03_plan.md Run Design Table):

Treatment arm (D gets K=5 + loose coupling):
- T1_G: DB=1, prefix=heilbron_adversarial/pop_a, role=constructor, opponent_db=2
- T1_D: DB=2, prefix=heilbron_adversarial/pop_b, role=improver, opponent_db=1, max_mutations=40, sync_min_delta=1
- T2_G: DB=3, prefix=heilbron_adversarial/pop_a, role=constructor, opponent_db=4
- T2_D: DB=4, prefix=heilbron_adversarial/pop_b, role=improver, opponent_db=3, max_mutations=40, sync_min_delta=1
- T3_G: DB=5, prefix=heilbron_adversarial/pop_a, role=constructor, opponent_db=6
- T3_D: DB=6, prefix=heilbron_adversarial/pop_b, role=improver, opponent_db=5, max_mutations=40, sync_min_delta=1

Control arm (K=1 symmetric):
- C1_G: DB=7, prefix=heilbron_adversarial/pop_a, role=constructor, opponent_db=8
- C1_D: DB=8, prefix=heilbron_adversarial/pop_b, role=improver, opponent_db=7
- C2_G: DB=9, prefix=heilbron_adversarial/pop_a, role=constructor, opponent_db=10
- C2_D: DB=10, prefix=heilbron_adversarial/pop_b, role=improver, opponent_db=9
- C3_G: DB=11, prefix=heilbron_adversarial/pop_a, role=constructor, opponent_db=12
- C3_D: DB=12, prefix=heilbron_adversarial/pop_b, role=improver, opponent_db=11

**G run extra_overrides** (all G runs identical):
```yaml
- evolution=steady_state
- opponent_redis_db=<D_DB>
- opponent_redis_prefix=heilbron_adversarial/pop_b
- feedback_mode=composition
- population_role=constructor
- post_step_hook=\${composition_injection_hook}
```

**Treatment D run extra_overrides** (T1_D, T2_D, T3_D):
```yaml
- evolution=steady_state
- max_mutations_per_generation=40
- sync_min_delta=1
- opponent_redis_db=<G_DB>
- opponent_redis_prefix=heilbron_adversarial/pop_a
- feedback_mode=composition
- population_role=improver
- d_sees_g_source=true
- d_archive_persistent=true
```

**Control D run extra_overrides** (C1_D, C2_D, C3_D):
```yaml
- evolution=steady_state
- opponent_redis_db=<G_DB>
- opponent_redis_prefix=heilbron_adversarial/pop_a
- feedback_mode=composition
- population_role=improver
- d_sees_g_source=true
- d_archive_persistent=true
```

All runs: pipeline=adversarial_asymmetric, chain_url=null, mutation_url=http://10.232.30.185:4000/v1, model_name=Qwen3-235B-A22B-Thinking-2507

**KF mitigations**:
- KF-01: All runs include `evolution=steady_state` in extra_overrides
- KF-02: `post_step_hook=\${composition_injection_hook}` uses `\${}` escape
- KF-03: All runs include `population_role=constructor/improver`

**Acceptance**: `gigaevo -e heilbron/k5-budget-loose manifest get runs --format json | jq length` returns 12

---

## Task 2: Fill servers[] and verify infrastructure

**Action**: Add server `10.232.30.185` to servers[]. Verify LiteLLM proxy reachable.

**Files**: `experiments/heilbron/k5-budget-loose/experiment.yaml`

**Acceptance**: `curl -s http://10.232.30.185:4000/v1/models -H "Authorization: Bearer sk-gigaevo"` returns model list

---

## Task 3: Generate launch.sh

**Action**: Run `gigaevo -e heilbron/k5-budget-loose launch --generate-script`

**Files**: `experiments/heilbron/k5-budget-loose/launch.sh`

**Acceptance**: `launch.sh` exists, is executable, contains 12 run commands, treatment D runs show `max_mutations_per_generation=40` and `sync_min_delta=1`

---

## Task 4: Write watchdog config

**Action**: Watchdog section already in experiment.yaml from design phase. Verify schema validates.

**Files**: `experiments/heilbron/k5-budget-loose/experiment.yaml`

**Acceptance**: `gigaevo -e heilbron/k5-budget-loose manifest gate preregistered` passes

---

## Task 5: Create 04_issues_log.md

**Action**: Create empty issues log from template.

**Files**: `experiments/heilbron/k5-budget-loose/04_issues_log.md`

**Acceptance**: File exists

---

## Task 6: Treatment verification (treatment-verifier agent)

**Action**: Invoke treatment-verifier to trace silent fallback modes.

**Acceptance**: All CRITICAL fallbacks covered. Treatment checks recorded in experiment.yaml.

---

## Task 7: Implementation alignment check (implementation-aligner agent)

**Action**: Invoke implementation-aligner to verify code matches 01_design.md.

**Acceptance**: ALIGNED verdict.
