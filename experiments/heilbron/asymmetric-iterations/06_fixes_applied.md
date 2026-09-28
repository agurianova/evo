# Fixes Applied: heilbron/asymmetric-iterations

**Generated:** 2026-04-14
**Source:** 04_issues_log.md (5 entries processed)

| # | Issue Summary | Fix Type | Files Changed | Status | Commit/Reason |
|---|--------------|----------|---------------|--------|----------------|
| 1 | MetricsTracker crash (no `iteration` field, no error isolation, min_delta=1 desync) | core code | Program model, MetricsTracker, sync hook config | SKIPPED | Already fixed during experiment (KF-04, KF-05 in PATTERNS.md) |
| 2 | MainRunSyncHook deadlock in SteadyState | config | adversarial_asymmetric.yaml | SKIPPED | Already fixed during experiment (KF-01); ProgressBasedSyncHook wired |
| 3 | Missing overrides at launch (evolution, population_role, unquoted ${}) | config/tool | experiment.yaml, generate_launch.py | SKIPPED | Already fixed during experiment (KF-02, KF-03) |
| 4 | Orphan processes repopulate Redis after flush | -- | -- | SKIPPED | Self-resolving race condition on second flush attempt |
| 5 | Telegram sendPhoto 400 on large plots | core code | gigaevo/monitoring/telegram_channel.py | DONE | Fallback to sendDocument (50 MB) on HTTP 400 |
| 6 | `min_delta` hardcoded to 1 in adversarial_coevo_ss.yaml | config | config/pipeline/adversarial_coevo_ss.yaml, config/pipeline/adversarial_asymmetric.yaml | DONE | Bind to `${max_mutations_per_generation}` Hydra ref |
| 7 | KF-03 status stale in PATTERNS.md | docs | experiments/PATTERNS.md | DONE | Updated ACTIVE to FIXED |
| 8 | LaTeX compilation broken on server | infra | -- | DONE | tectonic available at /home/user/conda/bin/tectonic; compiled 05_results.pdf successfully |

**Summary:** 4 fixed, 4 skipped
**Patterns promoted to PATTERNS.md:** KF-06 (new: Telegram sendPhoto 400 fallback), KF-03 updated to FIXED, KF-05 updated with Hydra ref detail
