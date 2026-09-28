# Adversarial Review: Prompt Co-Evolution

**Date**: 2026-03-16
**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)

---

## Round 1 (initial review)

**Verdict**: NEEDS REVISION (1 critical, 4 major, 3 minor)

| # | Concern | Severity | Resolution required |
|---|---------|----------|-------------------|
| 1 | `set_main_redis_db` never called -- stats write silently dead | Critical | Fix code; add smoke test criterion |
| 2 | max_generations=50 vs. cold_start reference=25 | Major | Match reference or evaluate at both timepoints |
| 3 | Temporal autocorrelation of prompt fitness | Major | Add to confound table; acknowledge in H1_mech |
| 4 | n=2 statistical language overstates power | Major | Replace "compelling" with "suggestive, requiring replication" |
| 5 | Redis key pattern match unverified | Major | Add smoke test verification |
| 6 | Pipeline footnote missing for prompt runs | Minor | Clarify in Section 5 |
| 7 | Prompt run max_elites rationale missing | Minor | Add rationale |
| 8 | Fallback period stats gap not in confound table; mixed-result verdict missing | Minor | Move to confound table; add INCONCLUSIVE case |

---

## Round 2 (re-review of revised design)

**Input**: Revised `experiments/hotpotqa/prompt_coevolution/01_design.md` (v2)

### Verification of Round 1 concerns

| # | Status | Evidence |
|---|--------|----------|
| 1 | **RESOLVED** | `set_main_redis_db()` removed. `main_redis_db` is now a constructor parameter in `GigaEvoArchivePromptFetcher.__init__()` (line 159: `main_redis_db: int | None = None`). When provided, `_redis_main_sync` is initialized immediately (lines 185-195). `config/prompt_fetcher/coevolved.yaml` line 16 wires it as `main_redis_db: ${redis.db}`, which resolves to the main run's Redis DB. Verified: `set_main_redis_db` has zero references in the codebase. Smoke test criterion added in Confound #3: stats key existence + prompt archive fitness > 0.0. Open Question #7 documents the fix. |
| 2 | **RESOLVED** | `max_generations` changed to 25 throughout (Section 5 line 83, prompt run config line 121). Matches cold-start reference. Confound eliminated. |
| 3 | **RESOLVED** | Added as Confound #7 with explicit mitigation: "report per-generation success rates for the champion prompt to check whether its advantage persists into the stagnation phase." H1_mech limitation noted in Section 2 line 44. |
| 4 | **RESOLVED** | Section 7 line 141: "no formal hypothesis test achieves adequate power. Results are interpreted descriptively." Line 141 continued: "evidence is suggestive, requiring replication at n>=4." Line 141 concludes: "A POSITIVE verdict at n=2 warrants a follow-up confirmatory experiment at n>=4." The word "compelling" has been removed. |
| 5 | **RESOLVED** | Confound #5 mitigation (b) now includes explicit Redis key name match verification in the smoke test: "directly query both sides of the stats channel -- confirm that the key written by the main run's fetcher (`{prefix}:prompt_stats:{prompt_id}`) is readable by the prompt run's RedisPromptStatsProvider using the same prefix string." |
| 6 | **RESOLVED** | Section 5 line 78: "`hotpotqa_asi` (main runs only; prompt runs use `pipeline=prompt_evolution`)". |
| 7 | **RESOLVED** | Prompt run config line 120: "`max_elites_per_generation=5` (smaller archive is appropriate for the prompt space: 4 seed programs + LLM mutations; 5 elites avoids sparsity in the prompt_length behavior dimension)". |
| 8 | **RESOLVED** | INCONCLUSIVE case added to verdict table (Section 2 line 36). Fallback period stats gap added as Confound #8. |

### New concerns identified in Round 2

| # | Concern | Severity | Notes |
|---|---------|----------|-------|
| R2-1 | **Prompt run completion vs. main run continuation** | Minor | Section 10 line 197 says "prompt runs reach gen 25 OR the paired main run completes first" -- this covers the case where the main run finishes first. But the reverse (prompt run finishes first while main run continues) is not addressed. Since both are now at max_generations=25, and prompt runs are fast (no chain eval), the prompt run will almost certainly finish before the main run. After the prompt run reaches gen 25, the main run will continue fetching the cached champion (TTL=30s) -- effectively a frozen champion for the remaining main-run gens. This is acceptable behavior (the champion is the best the prompt run found), but should be stated explicitly. Not blocking. |
| R2-2 | **Reference SD uncertainty** | Minor | The 2sigma threshold of 61.58% uses SD=1.00pp from n=4. The sampling distribution of SD at n=4 is wide (chi-squared with df=3). The design does not acknowledge this uncertainty. If the true SD were 2pp, the 2sigma threshold would be 63.58%, and neither treatment run reaching 61.58% would cross it. This does not invalidate the design -- the threshold is pre-registered and internally consistent -- but the interpretation section should note that the 2sigma calibration is based on a point estimate of SD with substantial uncertainty. Not blocking. |

### Residual observations (not blocking)

1. The McNemar test (Section 8, Test 3) still compares against T2 specifically ("the strongest historical control"). This is a form of selective comparison -- but since it is labeled "exploratory" and does not feed into the verdict table, it is acceptable. The Phase 5 results should also report McNemar against the cold-start mean or median program for completeness.

2. The `main_redis_db: int | None = None` default in the constructor means that if someone accidentally uses `prompt_fetcher=coevolved` without providing `main_redis_db`, stats writes will silently fail. A `ValueError` on `None` would be safer engineering, but this is a code quality concern, not an experimental design concern. Note for the plan phase.

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**:

All 8 Round 1 concerns have been addressed. The critical infrastructure bug (`set_main_redis_db` lifecycle gap) is resolved at the code level: `main_redis_db` is now a constructor parameter wired directly from `${redis.db}` in Hydra config, and the broken lifecycle hook has been removed. The `max_generations` confound is eliminated by matching the cold-start reference at 25 gens. Statistical language is now appropriately cautious for n=2. The temporal autocorrelation of prompt fitness and the fallback stats gap are both elevated to the confound table with explicit mitigations. The Redis key pattern verification is in the smoke test checklist.

Two minor items remain (R2-1: prompt run completion asymmetry; R2-2: reference SD uncertainty). Neither blocks approval. Both should be addressed in the plan phase or acknowledged in Phase 5 results.

This is a well-designed exploratory experiment testing genuinely novel infrastructure. The n=2 limitation is real but honestly acknowledged. The mandatory 3-gen smoke test with explicit stats-flow verification is the correct safeguard for first-production-run infrastructure. The design is ready for pre-registration.

*The science demands nothing less.*
