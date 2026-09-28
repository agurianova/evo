# Phase 2: Adversarial Review — ColBERT + Rich Feedback
<!-- Reviewer: Prof. Andrei Volkov (reviewer-2-adversary) -->
<!-- Date: 2026-03-10 -->

---

## Summary of Design

This experiment tests whether replacing BM25s retrieval with ColBERTv2 and enriching failure
feedback (full "Title | passage text" for missing gold documents, instead of titles only)
can push GigaEvo's mean test EM above the cold-start BM25 ceiling (59.58%) and toward GEPA
(62.3%), using n=4 independent cold-start replications of the new `static_colbert_f1_600`
problem variant against the F1+600 fitness configuration from PR #75.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| C1 | Wrong pipeline specified throughout the design document | **Critical** | Change every instance of `pipeline=hotpotqa_asi` to `pipeline=hotpotqa_colbert` |
| C2 | `COLBERT_INDEX_DIR` path does not exist at runtime; index build is incomplete | **Critical** | Resolve the path discrepancy and confirm full index build before any Phase 3 code changes |
| M1 | ColBERT `batch_retrieve` is sequential (one query at a time); latency at 600 samples is uncharacterized and the design's latency fallback is under-specified | **Major** | Pre-register a latency benchmark criterion and specify a fallback val N with a revised comparison baseline |
| M2 | t_beta value for MDE is 1.250 (= t(0.85, df=3)), not the correct 0.978 (= t(0.80, df=3)); stated MDE is overstated by 8.1% | **Major** | Correct MDE figures to 1.666pp (SD=1pp) and 3.331pp (SD=2pp); confirm decision thresholds are unaffected |
| M3 | Appendix A item 5 preflight check verifies the wrong thing: uses a hardcoded directory listing instead of the shared_config.py-resolved path, and checks "contains > 1 file" rather than confirming all 210 chunk files are present | **Major** | Specify the Python-import-based check command and require chunk-file count to match plan.json `num_chunks` |
| m1 | BORDERLINE verdict row in Section 2 spans only 0.02pp — indistinguishable from binomial noise on 300 samples | **Minor** | Collapse BORDERLINE into POSITIVE |
| m2 | The 4-exec_runner-per-run architecture loads the ColBERT index 4 times per host concurrently; GPU VRAM contention with vLLM is possible but no Amendment-0 trigger is pre-registered for this specific failure mode | **Minor** | Add a pre-registered halt criterion: if any exec_runner fails to load the ColBERT index, halt and reduce num_workers to 2 before resuming |
| m3 | `run_test_eval.sh` is stubbed with `exit 1`; the test eval must use the ColBERT problem variant, not any BM25 variant | **Minor** | Add to Appendix A: implement and verify `run_test_eval.sh` before launch |
| m4 | Retrieval recall@7 is listed as a secondary DV with no pre-registered threshold or verdict table | **Minor** | Either pre-register a minimum recall threshold or move this to Section 12 risks |

---

## Concern Detail

### C1 — Critical: Wrong pipeline specified throughout

The design document specifies `pipeline=hotpotqa_asi` in Section 5 (Controlled Variables), the
Run Design Table (Section 6), and Appendix A items 4 and 5. This is **experiment-invalidating**
if used as written.

The `hotpotqa_asi` pipeline uses `ASIPipelineBuilder` (from `static_a/pipeline.py`), which
instantiates `HotpotQAASIFormatter` — a formatter that provides title-only feedback for missing
gold documents. Using `pipeline=hotpotqa_asi` entirely negates the richer-feedback component of
the bundled intervention. If this pipeline is used, the experiment tests ColBERT retrieval with
BM25-style title-only feedback. The feedback-depth IV is silently zeroed out with no error,
no warning, and no way to detect it post-hoc from logs alone.

The correct pipeline is `pipeline=hotpotqa_colbert`, which uses `ColBERTPipelineBuilder` (from
`static_colbert_f1_600/pipeline.py`) with `HotpotQAColBERTFormatter`. This pipeline was
explicitly built for this experiment and exists at `config/pipeline/hotpotqa_colbert.yaml`. The
YAML comment in that file reads: "NEVER use pipeline=standard or pipeline=hotpotqa_asi for this
variant. hotpotqa_asi uses HotpotQAASIFormatter (title-only) not HotpotQAColBERTFormatter."

Appendix A item 4 compounds the error by instructing the researcher to "Confirm
`HotpotQAASIFormatter` in the pipeline calls the new failure formatter correctly." This is
impossible: `HotpotQAASIFormatter` is a separate class that does not delegate to
`HotpotQAColBERTFormatter`. This instruction must be replaced with one that verifies
`ColBERTPipelineBuilder` is active.

**Required fix**: Replace every instance of `pipeline=hotpotqa_asi` with
`pipeline=hotpotqa_colbert` in Sections 5, 6, 9 (confound row for `pipeline=standard`), and
Appendix A items 4 and 5. Revise Appendix A item 4 to confirm that `--cfg job` output shows
`_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder`.

### C2 — Critical: COLBERT_INDEX_DIR path does not exist at runtime; index is incomplete

`shared_config.py` computes:

```python
_REPO_ROOT = _BASE_DIR.parent.parent.parent   # problems/chains/hotpotqa -> repo root
COLBERT_INDEX_DIR = str(_REPO_ROOT / "experiments" / "colbert_index")
```

This resolves to `/workspace-SR008.fs2/mathemage/gigaevo-core/experiments/colbert_index`. That
path **does not exist**. The `_ensure_colbert_initialized` function in `retrieval.py` checks
`if not index_dir.exists(): raise FileNotFoundError(...)` before calling the Searcher. Every
run will fail immediately at first retrieval call.

The actual index currently lives at `experiments/hotpotqa/indexes/colbert_index/`. That
directory contains only `plan.json` — no `.pt` chunk files, no `doclens`, no `ivf.pid.pt`, no
`centroids.npy`. The `plan.json` itself reports `"num_chunks": 210`, meaning 210 chunk files
are required to make the index searchable. The index build is incomplete and ColBERT cannot
retrieve anything.

There is a subtlety the design partially captures: the ColBERT `Searcher` constructed with
`Run().context(RunConfig(nranks=1, experiment="hotpotqa"))` resolves the physical index location
as `root/experiment/indexes/index_name` — which maps correctly to
`experiments/hotpotqa/indexes/colbert_index/`. However, the guard `if not index_dir.exists()`
in `_ensure_colbert_initialized` operates on `COLBERT_INDEX_DIR` (= `experiments/colbert_index`,
which does not exist), not on the Run-context-resolved path. The guard fails before the Searcher
is ever constructed.

Two distinct blockers must both be resolved in Phase 3, before any code changes:

1. Fix `COLBERT_INDEX_DIR` in `shared_config.py` so that the path it resolves to exists on disk
   and allows `_ensure_colbert_initialized` to proceed to the Searcher call. One correct
   approach: keep the current `experiments/colbert_index` value but create that directory as a
   symlink or copy of the actual index, verifying the Searcher's Run-context resolution still
   works end-to-end. An alternative: change `COLBERT_INDEX_DIR` to the fully resolved path
   `experiments/hotpotqa/indexes/colbert_index` and adjust the Searcher `root` argument
   accordingly (confirming `index_dir.parent` is then `experiments/hotpotqa/indexes`, not
   `experiments/`). Either fix requires end-to-end retrieval verification, not just path
   existence checks.

2. Confirm the index build completes and all 210 chunk files are present. The design flags this
   as Risk 1 but does not tie it to a mandatory gate that blocks Phase 3 code changes. It must
   be a hard blocker.

The preflight check in Appendix A item 5 ("Assert `COLBERT_INDEX_DIR` directory exists and
contains > 1 file (not just `plan.json`)") will pass incorrectly once the directory is created
but before the chunk files are generated. "More than one file" can be satisfied by a
two-file directory. The check must verify chunk-file count, not mere non-emptiness.

### M1 — Major: ColBERT batch_retrieve is sequential; latency fallback is under-specified

`ColBERTRetriever.batch_retrieve` in `retrieval.py` iterates queries sequentially in a Python
`for` loop (one `_colbert_searcher.search(query, k=k)` call per query). At 600 samples per
validation, with two retrieval steps (hop-1 and hop-2), the validator makes 1200 sequential
calls per evaluation pass. Depending on index size and hardware, each call may take 50–500ms,
yielding 60–600s per hop or 120–1200s total for retrieval alone — before any LLM inference.

The design acknowledges this as Risk 2 and proposes: "if eval time > 2000s per 600 samples,
increase stage_timeout to 9000 and dag_timeout to 12000 via Amendment 0." This is insufficient
on two counts:

First, the trigger threshold ("eval time > 2000s") is not operationally defined. The benchmark
script `verify_colbert.py` measures single-query latency and a small batch of test queries, but
does not run a full 600-sample eval pass. The design must specify what benchmark run produces
the "eval time" measurement that triggers Amendment 0.

Second, the fallback from 600 to 300 val samples, if triggered, invalidates the comparison
baseline. The BM25 cold-start reference (mean 59.58%, SD 1.00pp) was computed at 600 samples.
A 300-sample run may produce different expected mean and variance, and the pre-registered
POSITIVE threshold (62.00%) is calibrated against the 600-sample reference. If the fallback is
triggered, the design must pre-register what reference distribution and what POSITIVE threshold
apply in the 300-sample case. The cold-start PR #75 runs were all at 600 samples; there is no
BM25 300-sample reference for the same F1+cold-start condition.

**Required fix**: (a) Pre-register in Section 12 the exact benchmark that triggers the fallback:
specify the script, the sample count, and the per-sample latency threshold (e.g., if
`verify_colbert.py` batch test reports > X ms/query, Amendment 0 is filed). (b) Pre-register
what comparison baseline and POSITIVE threshold apply if 300-sample fallback is used. If no
adequate 300-sample BM25 reference exists, acknowledge this as a consequence of the fallback
and specify that a POSITIVE verdict would require a concurrent 300-sample BM25 control run,
or be capped at SUGGESTIVE pending replication under matched conditions.

### M2 — Major: MDE formula uses incorrect t_beta (inherited from cold_start)

The design states t_beta = t(0.80, df=3) = 1.250 and computes MDE = (2.353 + 1.250) × 1.0 /
sqrt(4) = 1.80pp at SD=1pp. The value 1.250 is t(0.85, df=3), not t(0.80, df=3). The correct
value for 80% power at df=3 is t(0.80, df=3) = 0.978. This error was first identified in the
cold_start design review, "corrected" in the cold_start revision by substituting 1.250 (which
is the wrong critical value), and is now propagated here unchanged.

Correct figures:
- t_beta = 0.978 (= t(0.80, df=3))
- MDE at SD=1pp: (2.353 + 0.978) × 1.0 / sqrt(4) = 1.666pp
- MDE at SD=2pp: (2.353 + 0.978) × 2.0 / sqrt(4) = 3.331pp

The error is conservative (the stated MDE of 1.80pp overstates the correct 1.666pp by 8.1%;
actual power at the stated MDE exceeds 80%). No decision threshold is affected: the POSITIVE
threshold of 2.42pp clears the corrected MDE of 1.666pp by 0.754pp. The conclusion that "the
experiment is adequately powered for H1 at the expected variance level" remains valid. However,
the design document must state correct figures.

**Required fix**: Replace t_beta = 1.250 with t_beta = 0.978. Update MDE values to 1.666pp
(SD=1pp) and 3.331pp (SD=2pp). Explicitly state that the POSITIVE threshold (2.42pp above
reference) exceeds the corrected MDE at SD=1pp by 0.754pp.

### M3 — Major: Appendix A item 5 preflight check is insufficient

Appendix A item 5 states: "Assert `COLBERT_INDEX_DIR` directory exists and contains > 1 file
(not just `plan.json`)." Two problems:

First, a shell-level `ls` or `ls -la` command hardcoding the directory path may check a
different directory than what `shared_config.py` resolves at runtime. The runtime path is
computed from `_BASE_DIR.parent.parent.parent` — a calculation that must be evaluated from
within Python, not reconstructed manually in a shell script.

Second, "contains > 1 file" is not a meaningful criterion. A directory with 2 files (e.g.,
`plan.json` and one incomplete chunk) would pass. The correct criterion is that the number of
`.pt` files in the directory equals `num_chunks` from `plan.json` (currently 210). At that
point, the searcher initialization test (Appendix A item 3's `verify_colbert.py` run) provides
end-to-end confirmation.

**Required fix**: Revise item 5 to: (a) print `COLBERT_INDEX_DIR` using
`python -c "from problems.chains.hotpotqa.shared_config import COLBERT_INDEX_DIR; print(COLBERT_INDEX_DIR)"`
and store the result; (b) count `.pt` files in that directory and assert the count equals the
`num_chunks` value from `plan.json`.

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The hypothesis structure is well-formed. The POSITIVE threshold at +2.42pp above the
59.58% reference (= 62.00%) is pre-registered and correctly positioned above the noise floor.
The verdict table hierarchy (STRONG POSITIVE > POSITIVE > SUGGESTIVE > NULL > NEGATIVE) is
exhaustive and internally consistent. Both Test 1 (vs. BM25 cold-start reference) and Test 2
(vs. GEPA) are pre-registered with appropriate direction. Test 3 is correctly classified as
exploratory and does not modify the primary verdict.

The BORDERLINE row ([61.98%, 62.00%)) is 0.02pp wide. The binomial SE for a proportion near
0.62 on 300 samples is approximately 2.8pp. A 0.02pp interval is entirely within measurement
noise and operationally indistinguishable from POSITIVE. This row should be collapsed (minor).

The two-sided 95% CI formula (mean +/- 3.182 x SD/2) is correct for df=3.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (no other differences between conditions)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Unaddressed confounds**:

The bundled-intervention confound is the design's primary structural limitation and is explicitly
acknowledged. The justification for bundling is scientifically sound: ColBERT retrieval changes
which documents are missing, making "richer feedback on missing titles from a degraded retriever"
a degenerate comparison. The null-is-interpretable argument (bundled null rules out the most
natural parity condition with GEPA) is valid. I accept the bundling.

The cross-condition comparison rests on the BM25 cold-start reference being a valid control for
the ColBERT treatment. This is valid: the test set is identical (fixed 300-sample HotpotQA_test.jsonl,
EM scoring, thinking Qwen3-8B), the val set is fixed-600 sequential in both conditions, and the
F1 fitness metric is consistent. The BM25 reference is appropriate as the control distribution.

One implicit confound deserves explicit naming: `static_colbert_f1_600/validate.py` imports
`COLBERT_INDEX_DIR` from `shared_config.py`, but `shared_config.py` also defines `BM25S_INDEX_DIR`
and `CORPUS_PATH`, and the `load_context` function still returns these BM25 keys in its output
dict. If any code path in `static_colbert_f1_600` falls back to BM25 retrieval on failure (e.g.,
exception in `_ensure_colbert_initialized` swallowed upstream), it would silently revert to BM25
with no error. The run-invalidation criterion 7 ("ColBERT retrieval confirmed non-functional")
partially addresses this, but only post-hoc. An active preflight check is stronger mitigation.
This is low severity but is not currently named as a confound.

The server-load asymmetry (U1/U2 on host A, U3/U4 on host B) is correctly identified and
mitigated with the pre-registered 3pp host-stratified mean diagnostic from PR #75. Adequate.

---

## Statistical Validity

- [x] Sample size is justified
- [x] Statistical test is appropriate for the data
- [x] Significance threshold is pre-specified
- [x] Multiple comparison correction applied if testing multiple hypotheses

**Notes**: The one-sample t-test (Test 1) against the BM25 cold-start reference mean of 59.58%
is appropriate: the reference is a fixed external value, not an estimate from this experiment's
data, making a one-sample test correct. df=3 with one-sided alpha=0.05 and t_critical=2.353 is
correct.

Test 2 (against GEPA 62.3%) uses the same colbert_mean and colbert_SD, constituting two tests
on the same data. No multiple-comparison correction is applied, but this is acceptable: the two
tests form a strict hierarchy (STRONG POSITIVE requires Test 2 to reject, which is a subset of
the region where Test 1 also rejects at the given effect sizes), and the primary adoption verdict
is anchored to Test 1. The pre-registered hierarchy prevents post-hoc cherry-picking.

The power analysis error is addressed in M2. The POSITIVE threshold (2.42pp) still exceeds the
corrected MDE at SD=1pp (1.666pp), so the adequacy-of-power conclusion holds.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: Primary metric (test EM, 300-sample held-out test set, best-by-val program, thinking
Qwen3-8B) is identical to the BM25 cold-start reference evaluation protocol from PR #75. The
`static_colbert_f1_600/validate.py` computes both F1 (fitness) and EM (secondary) and returns
`(metrics, failures)`, populating `valid_frontier_em` in Redis (confirmed by code inspection).
Val fitness (F1) trajectory and val EM are both reported, consistent with prior experiments.
Thinking mode is explicitly required throughout and is enforced via run-invalidation criterion 1.

---

## Required Changes Before Approval

1. **[C1 — Critical]** Replace every instance of `pipeline=hotpotqa_asi` with
   `pipeline=hotpotqa_colbert` in Sections 5, 6, 9, and Appendix A items 4 and 5. Revise
   Appendix A item 4 to confirm `--cfg job` output shows
   `_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder`,
   not `HotpotQAASIFormatter`.

2. **[C2 — Critical]** Add a mandatory hard gate before any Phase 3 code changes: (a) confirm
   `COLBERT_INDEX_DIR` as resolved by `shared_config.py` points to an existing directory on
   disk; (b) confirm that directory contains the full set of chunk files matching `plan.json`'s
   `num_chunks` (currently 210 `.pt` files); (c) confirm end-to-end retrieval by running
   `verify_colbert.py` successfully after (a) and (b) pass. State this gate explicitly in
   Section 12 and in Appendix A as a pre-code-change requirement, not merely a "risk."

3. **[M1 — Major]** Pre-register a latency benchmark criterion and fallback specification. Add
   to Section 12: specify the exact benchmark that triggers Amendment 0 (e.g., single-query
   latency > X ms in `verify_colbert.py`). Pre-register what comparison baseline and POSITIVE
   threshold apply if val N is reduced to 300 samples. If no adequate 300-sample BM25 reference
   exists for the F1+cold-start condition, acknowledge that a POSITIVE verdict under the 300-sample
   fallback requires either a concurrent BM25 control run or is capped at SUGGESTIVE.

4. **[M2 — Major]** In Section 7, correct t_beta from 1.250 to 0.978 (= t(0.80, df=3)). Update
   MDE at SD=1pp to 1.666pp and at SD=2pp to 3.331pp. Add a sentence confirming the POSITIVE
   threshold (2.42pp above reference = +0.754pp above corrected MDE at SD=1pp) remains adequate.

5. **[M3 — Major]** Revise Appendix A item 5 to: (a) print `COLBERT_INDEX_DIR` from within
   Python by importing `shared_config` (not by hardcoding the path in a shell command); (b)
   count `.pt` files in the resolved directory and verify the count equals `num_chunks` from
   `plan.json`.

---

## Verdict

**[x] NEEDS REVISION** — address required changes 1–5 above, then re-submit for review.

The scientific rationale of this experiment is sound. The bundling justification is well-argued
and the null-is-interpretable claim is correct. The statistical test structure is appropriate,
the decision hierarchy is properly pre-registered, the confound table is thorough, and the team
clearly understands the failure-mode landscape from prior experiments. The code infrastructure
— `ColBERTPipelineBuilder`, `HotpotQAColBERTFormatter`, `hotpotqa_colbert.yaml` — is already
implemented and appears correct.

What makes this document currently unapprovable is a mismatch between the code that exists
and the document describing how to use it. The design specifies `pipeline=hotpotqa_asi`, which
uses `HotpotQAASIFormatter` (title-only feedback) and silently removes the richer-feedback
half of the bundled treatment. Had this been launched as written, the experiment would have
tested ColBERT retrieval with BM25-style feedback across 4 runs and 25 generations, with no
error, no warning, and no post-hoc detectability from logs. The resulting null result would
have been uninterpretable: it would not distinguish between "ColBERT + rich feedback does not
help" and "ColBERT alone does not help," because the rich feedback was never applied.

The ColBERT index incompleteness (C2) is the second hard blocker: the experiment cannot be
launched at all until the index build finishes and the path discrepancy is resolved. The design
acknowledges this correctly as Risk 1 but does not enforce it as a gate on Phase 3 code changes.
Given that the path fix must touch `shared_config.py` (shared with all BM25 problem variants),
that fix deserves explicit pre-registration before any file is edited.

All five required changes are corrections or additions that do not alter the experimental design
itself. A single revision cycle should resolve them. Minor concerns m1–m4 may be addressed
alongside or noted as Phase 5 documentation items.

*The science demands nothing less.*

---

## Re-Review (2026-03-10)

### Verification Against Required Changes

**[C1 — Critical: Wrong pipeline] — RESOLVED.**

Every instance of `pipeline=hotpotqa_asi` has been replaced with `pipeline=hotpotqa_colbert`
throughout the document. Section 5 (Controlled Variables) explicitly names `hotpotqa_colbert`
and adds a prominently boxed rationale explaining why `hotpotqa_asi` is experiment-invalidating.
Section 6 (Run Design Table) shows `hotpotqa_colbert` for all four runs. Section 9 (Confounds)
now has a dedicated row for the pipeline choice, with the invalidation consequence stated
explicitly. Appendix A item 4 correctly instructs verification that `--cfg job` output shows
`_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder`
and explicitly warns against seeing `HotpotQAASIFormatter`. Code inspection confirms
`config/pipeline/hotpotqa_colbert.yaml` exists, targets `ColBERTPipelineBuilder`, and carries
the warning "NEVER use pipeline=standard or pipeline=hotpotqa_asi for this variant."

**[C2 — Critical: COLBERT_INDEX_DIR path / incomplete index] — RESOLVED.**

Section 12 now elevates this from a "risk" to a mandatory hard gate with three explicit
sub-conditions before any Phase 3 code changes: (a) `COLBERT_INDEX_DIR` resolved via Python
import exists on disk, (b) all 210 `.pt` chunk files are present (verified by counting against
`plan.json`'s `num_chunks`), (c) `verify_colbert.py` succeeds end-to-end. The gate is restated
at the top of Appendix A as a prerequisite to every item that follows. Section 9 adds a
dedicated confound row for the path mismatch with the exact fix path. The index-incompleteness
confound row explicitly calls out the 210-chunk requirement.

**[M1 — Major: Latency fallback under-specified] — RESOLVED.**

Section 12 now contains a fully pre-registered "Amendment 0 trigger — latency criterion" with
an operationally defined threshold: single-query latency > 500ms averaged over the `verify_colbert.py`
test batch. The 500ms threshold is arithmetically justified (600 samples × 2 hops × 500ms =
600s retrieval alone, approaching the 6000s stage_timeout). The 300-sample fallback path is
fully pre-specified: the pre-registered POSITIVE threshold (62.00%) no longer applies; a
POSITIVE verdict under 300-sample fallback requires a concurrent BM25 control run at 300
samples; without such a run, the maximum attainable verdict under the fallback is SUGGESTIVE.
Amendment 0 must be filed before launch if the trigger fires.

**[M2 — Major: Incorrect t_beta] — RESOLVED.**

Section 7 now uses t_beta = 0.978 = t(0.80, df=3) throughout. MDE at SD=1pp is stated as
1.666pp; at SD=2pp as 3.331pp. The margin over the POSITIVE threshold (2.42pp above reference
= +0.754pp above corrected MDE at SD=1pp) is explicitly stated. A correction note acknowledges
the prior error and confirms no decision threshold is affected. The arithmetic in the displayed
calculations is correct: (2.353 + 0.978) × 1.00 / sqrt(4) = 3.331 × 0.500 = 1.666pp. Both
values verified.

**[M3 — Major: Appendix A item 5 preflight insufficient] — RESOLVED.**

Appendix A item 5 now specifies the Python-import-based check command that prints
`COLBERT_INDEX_DIR` from within Python (not a hardcoded shell path). It separately requires
counting `.pt` files and asserting the count equals `num_chunks` from `plan.json`. The exact
multi-line Python snippet is provided verbatim. The "contains > 1 file" criterion has been
replaced by the `assert pt_count == num_chunks` assertion.

**[m1 — Minor: BORDERLINE row 0.02pp wide] — RESOLVED.**

The BORDERLINE row has been removed. Section 2 now contains a note: "The previous draft
included a BORDERLINE row spanning [61.98%, 62.00%), a 0.02pp interval that is entirely within
binomial measurement noise on 300 samples (SE ~2.8pp). This row has been collapsed into
POSITIVE, per reviewer concern m1." The verdict table in Section 2 no longer contains the
spurious 0.02pp interval.

**[m2 — Minor: exec_runner GPU VRAM contention] — RESOLVED.**

Section 9 now has a dedicated confound row: "ColBERT per-worker GPU memory contention," with
the pre-registered halt criterion explicitly stated — if any exec_runner fails to load the
ColBERT index, halt the affected run and reduce `num_workers` from 4 to 2 before resuming
(Amendment required). Section 10 (Stop Criteria) also includes this as an early termination
criterion.

**[m3 — Minor: run_test_eval.sh stubbed] — RESOLVED.**

Appendix A item 3 explicitly requires implementing and verifying `run_test_eval.sh` before
launch, specifying that the test eval must use `static_colbert_f1_600` (not any BM25 variant)
and must pass a dry-run test against 1–5 samples to confirm the ColBERT pipeline is active.
The stub remains `exit 1` in the repository — correctly, since this is a Phase 3 engineering
task; the design document correctly names it as a pre-launch requirement.

**[m4 — Minor: recall@7 DV lacks pre-registered threshold] — RESOLVED.**

Section 4 now shows recall@7 at gen 0 with a pre-registered minimum threshold of >= 0.40,
with an explicit verdict: "if observed recall@7 < 0.40 at gen 0 across all 4 runs, ColBERT
retrieval is considered defective and runs are invalidated per criterion 7." Section 10 (Run
Invalidation Criteria) carries this as criterion 7, and the same language appears in Section 10
early termination criteria (empty results at gen 0 → halt immediately).

---

### New Issues Introduced by the Revision

**[Documentation imprecision — not a blocker]**: Section 5 and Appendix A item 1 state that
`RETRIEVER = "colbert"` must be set in the new problem variant's shared config (or a local
override). Code inspection of `static_colbert_f1_600/validate.py` reveals that the ColBERT
retriever is hardcoded via direct imports of `COLBERT_INDEX_DIR` and `ColBERTRetriever` —
the `RETRIEVER` switch in `shared_config.py` (which remains set to `"bm25"` and governs
`get_retriever()`) is not used by this variant's validate.py at all. The preflight assertion
in Appendix A item 5 — "Assert `RETRIEVER == 'colbert'` in the new problem variant's config"
— therefore checks a flag that does not control retrieval in this variant. If a Phase 3
engineer executes the preflight literally, they may either: (a) set `shared_config.RETRIEVER =
"colbert"` globally (breaking all BM25 variants), or (b) find the assertion trivially
impossible to satisfy without code changes.

This is a documentation imprecision, not an experimental design flaw. The actual retrieval
mechanism is already correct: `validate.py` in `static_colbert_f1_600` directly constructs
`ColBERTRetriever(COLBERT_INDEX_DIR, ...)`. The more robust preflight would be to inspect that
validate.py's import list includes `ColBERTRetriever` and `COLBERT_INDEX_DIR` directly, or to
confirm via the `--cfg job` output that `ColBERTPipelineBuilder` is active. The
`verify_colbert.py` end-to-end check (gate (c)) is the authoritative functional verification.
The RETRIEVER assertion is redundant noise that could mislead. Since this does not affect the
experiment's validity — the retriever is correctly wired in code — and the functional check
subsumes it, I flag it as a documentation note for Phase 3 engineers, not a required revision.

**[Verdict table: p < 0.05 AND mean >= 62.3% row ordering] — Negligible.**

Test 1's verdict table lists the STRONG POSITIVE row (p < 0.05, >= 62.3%) after the POSITIVE
row (p < 0.05, >= 62.00%). Since 62.3% >= 62.00%, any result satisfying STRONG POSITIVE also
satisfies POSITIVE, but the table's row ordering implies STRONG POSITIVE is a special case of
POSITIVE. A note clarifies this ("special case of POSITIVE"). The hierarchy is unambiguous.
No action required.

---

### Assessment of Residual Design Quality

The revised design document is well-structured and the five required changes have been
addressed completely. The scientific rationale, statistical test hierarchy, and confound table
are sound. The experiment correctly uses `pipeline=hotpotqa_colbert`, which is confirmed to
exist in the codebase and to target `ColBERTPipelineBuilder`. The power analysis now uses
correct t-table values. The latency fallback is operationally defined with a pre-registered
consequence for comparison baseline. The index completeness check is now a blocking gate, not
a risk.

Two genuine technical risks remain that Phase 3 must manage but are correctly pre-registered
as engineering prerequisites, not design flaws:

1. The `COLBERT_INDEX_DIR` path in `shared_config.py` still resolves to
   `experiments/colbert_index/` (does not exist). This must be fixed in Phase 3 before any
   run. The mandatory hard gate in Section 12 and Appendix A enforces this correctly.
2. The ColBERT index build is still in progress (only `plan.json` present at review time).
   The 210-chunk completeness check in Appendix A item 5(b) enforces this as a launch blocker.

Neither of these is a design document deficiency — both are correctly acknowledged and gated.

---

### Verdict

**[x] APPROVED**

All five required changes (C1, C2, M1, M2, M3) and all four minor concerns (m1–m4) have been
adequately addressed. The documentation imprecision regarding the `RETRIEVER` switch is a
Phase 3 engineering note, not a design blocker — the actual retrieval code is correct. The
experimental design is internally consistent, the comparison baseline is valid, the decision
gates are exhaustive and pre-registered, and the pre-launch checklist is thorough. The
mandatory hard gate on ColBERT index completeness is the right structural choice: it converts
the most dangerous infrastructure risk from a launch-time surprise into a pre-code-change
blocker with explicit verification steps.

Phase 3 may proceed. Pre-registration commit of `03_plan.md` must occur before any code
changes to `shared_config.py`, `static_colbert_f1_600/`, or any other problem directory.

*The science demands nothing less.*
