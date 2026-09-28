# SOTA RAG for idea-card retrieval — design (no code)

Status: DESIGN ONLY, 2026-07-05. Implementation gated: V1 (PID 967271) / V2 (PID 967274) are STILL LIVE
at design time and import these prompts+code — no code/prompt edit lands until both are dead
(`kill -0` returns nonzero). This file is inert w.r.t. the live runs.

Grounding: `experiments/retrieval_fix_plan.md`, round-1/round-2 reports under
`/home/jovyan/gigaevo/outputs/memory_rebuild_polishcheck_2026-07-05/investigation/`,
`gigaevo/memory/storage/research.py`, `gigaevo/memory/read/{reader,shortlist,reputation,auction,render}.py`,
`gigaevo/memory/storage/{index,config}.py`, `gigaevo/prompts/retrieval_reflection/{system,user}.txt`,
NeighborSource Protocol at `gigaevo/memory/write/librarian.py:39`.

---

## 0. Causal chain (signal → behaviour → metric)

1. Today the reflector judges a **mid-JSON-truncated** slate (77–91% of calls; `_clip(payload, 12000)`
   at `research.py:324`), is **budget-blind** (no step counter; step-3 `continue` silently forfeits), and
   gets **no feedback** when it re-requests a card it already holds (`_retrieve` drops held ids at
   `research.py:304` → livelock; 54% of V1 continue-with-candidates calls).
   → Fix visibility + deadline + feedback → the reflector can actually finalize → **budget-death
   empties (40% of V empties) → ~0**.
2. The FIX-6 binary rule ("skip if parent already implements" + "empty hand is mandatory") turns
   semantic similarity — the very signal that ranked the candidates — into a disqualifier under
   population convergence (97% of explicit-empty rationales cite it).
   → Grade the rule (reject only true duplicates; partial overlap = select + state the delta)
   → **explicit empties 21.5% of reflector calls → near G's 0.5%**.
3. (1)+(2) restore the funnel: **non-empty selection rate 49–63% → ≥75%** at slate width 4–6.
4. Restored injection = more guided shots. Round 2 measured per-shot injection value ≈ 0
   (pooled-V coeff +0.0005, p=.32), so fitness is the **guardrail**, not the primary metric: new
   retrieval must be ≥ old and ≥ no-card on fitness delta, and win on funnel/ranking metrics.
5. SOTA layer (rerank + MMR + stats-aware ranking) then improves *which* cards fill the restored
   slots: higher outcome-labeled nDCG on replayed reads, more diverse slates, reputation and novelty
   visible to the reflector instead of the current pure-semantic shortlist feeding a
   pure-reliability auction (known gap: zero novelty pressure in card selection).

**Riskiest link: (4).** If per-shot injection value stays ≈ 0, a perfect retriever buys funnel
health but no fitness. That is exactly what the counterfactual experiment (§4b, arm C) measures;
ship/hold decisions key on funnel metrics with fitness as a no-harm gate.

---

## 1. P0 defect fixes (surgical, `research.py` + reflection prompts)

### P0-1 Truncation livelock → budget-aware `card_brief` rendering

Replace string-level `_clip(payload, _PAYLOAD_CLIP_CHARS)` in `ResearchAgent._reflect`
(`research.py:316–324`) with **whole-brief, budget-aware rendering**:

- `card_brief(card) -> dict`: successor of `_candidate_payload` with tighter clips —
  `description` ≤ 300 chars (single-spaced), `evidence_summary` ≤ 160, `task_description_summary`
  ≤ 100, keywords ≤ 6, `fitness` for program cards. Program `code` bodies stay out (they already
  are; briefs must keep it that way when stats lines are added in §3c). Target ≈ 450–600 chars/card.
- `_retrieve` keeps each candidate's **best (min) hit distance** (currently discarded,
  `research.py:303–311`) in the candidates map: `dict[str, tuple[Card, float]]`.
- Render briefs in relevance order (best-distance ascending; fused score once §3 lands). Emit whole
  briefs until a char budget (`ResearchConfig.reflect_payload_chars`, default 24000) is hit; drop
  the **tail whole**, never mid-JSON, and append a visible marker:
  `{"omitted": N, "omitted_ids": [...]}` so the reflector knows the slate is elided, with which ids.
- The payload is always valid JSON. No pagination in slice 1 (the budget at brief sizes covers
  ~40–50 cards, above the observed 30–57 pool only at the extreme; the omitted-marker handles the rest).

### P0-2 Budget-aware final step

`ResearchAgent.research()` (`research.py:236–268`) threads step awareness into the reflect call:

- `gigaevo/prompts/retrieval_reflection/user.txt` gains a `{step_status}` placeholder
  (prompts stay externalized; no inline literals in Python).
- Non-final steps: `step_status = "Retrieval step {k} of {n}."` (template line lives in `user.txt`).
- Final step: `step_status` is filled from a new snippet
  `gigaevo/prompts/retrieval_reflection/final_step.txt`:
  *"FINAL STEP — retrieval budget exhausted. mode MUST be \"final\": select the best-fitting
  CANDIDATES, or an empty hand only if nothing fits. \"continue\" forfeits every candidate."*
- Escape rule: any literal `{`/`}` in these .txt files doubled (`.format()` KeyError kills runs silently).

### P0-3 Held-card feedback (kill the re-query black hole)

After a `continue` decision, scan `decision.additional_queries` for exact substring matches of ids
currently in `candidates` (ids are `mem-<hex>` / `program-<hex>` tokens — exact match against the
known id set, no NLP). On the next step, append to the reflect request an observation block:

- `ALREADY HELD: [ids] — these cards are in CANDIDATES above; select or reject them, do not re-request.`
- When a step's `_retrieve` returns zero new ids: `NO NEW CARDS matched the follow-up queries.`

Both lines are template snippets in `gigaevo/prompts/retrieval_reflection/` (e.g. `observations.txt`),
formatted by `research.py`. This gives the loop the observation channel a ReAct-style agent needs;
today the reflector acts blind.

Each P0 item ships with a targeted unit test (brief renderer budget/ordering/omitted-marker; final-step
injection at `step == max_iters`; held-id detection).

---

## 2. Graded duplicate rule (P1 — FIX-6 rewrite, `retrieval_reflection/system.txt`)

Replace the binary skip-if-already-implemented + mandatory-empty-hand block with a **three-grade
redundancy judgment against the parent's actual code**:

| Grade | Definition | Action |
|---|---|---|
| DUPLICATE | Same mechanism AND no increment — no new parameter value, structural variation, or implementation detail beyond what the parent code already contains | Reject |
| INCREMENT | Same mechanism family but a concrete delta over the parent code (different schedule, extra term, changed operator, new parameter regime) | **Select**, and state the delta in `reasoning` |
| NEW | Mechanism absent from the parent code | Select on task/mechanism fit (existing rules) |

Accompanying prompt changes:

- **Program exemplars are compared at code level**: redundancy = "what does this exemplar's code do
  differently from the parent's code", never strategy-label overlap ("both do SA + grid init" is not
  a duplicate). This is the clause that un-poisons converged-population retrieval, where top-k
  exemplars *necessarily* share the parent's strategy family.
- Lineage stays an anti-redundancy signal but is demoted from "strongest — skip" to a tie-breaker
  between INCREMENT candidates.
- Empty hand: allowed, no longer framed as mandatory-first. *"When at least one candidate is
  task-fit at grade INCREMENT or NEW, select the sharpest 1–3; an empty hand is for slates with no
  task-fit candidate at all."*
- Continue-cap: *"If CANDIDATES is non-empty, prefer mode \"final\"; use \"continue\" only when a
  specific missing kind of evidence is named and the current step retrieved new cards."* (Backstop:
  P0-2 makes step-3 continue impossible anyway.)

Watch item (out of scope here): FIX-12's same-mechanism-only MERGE rule shares vocabulary with this
grading; after the rewrite, re-run the card-conflation spot-check so writer-side "same mechanism"
and reader-side "DUPLICATE" don't drift apart.

---

## 3. SOTA upgrades (config-gated, default OFF until offline eval wins)

Design rule: new implementations behind existing Protocol/`_target_` seams; Chroma remains the only
vector-search owner; no hand-rolled cosine outside `index.py` (already the single module that owns
embeddings); prompts stay under `gigaevo/prompts/`.

### 3a. Cross-encoder rerank behind the NeighborSource seam

- **Write path** (librarian dedup/merge): `RerankedNeighborSource` implementing
  `NeighborSource.nearest(text, k, kind)` (`librarian.py:39`) — wraps the existing Chroma-backed
  source: over-fetch `k × pool_mult` (default 4) from the base, score (query, card-document) pairs
  with a `sentence_transformers.CrossEncoder`, return top-k. Swapped in via Hydra `_target_`; the
  Librarian is untouched.
- **Read path**: a new `Reranker` seam inside the research loop — after `_retrieve`, before
  `_reflect`: re-score the aggregated candidate pool against the mutation-grounded request
  (`build_research_query` output, truncated to the encoder's max length) once per step; the fused
  score (§3c) orders briefs and picks the tail to omit under the P0-1 budget. A
  `NullReranker` (order by best hit distance) is the default, so slice 1 works without it.
- Model candidates: `cross-encoder/ms-marco-MiniLM-L-6-v2` (fast) vs `BAAI/bge-reranker-base`
  (stronger). Chosen by the offline harness (§4a), not by taste. Weights cached via the existing
  `ensure_writable_hf_cache()`; CPU inference with OMP capped ≤ 8 (shared box).
- Config: `ResearchConfig.rerank: {enabled: false, model: ..., pool_mult: 4, max_query_chars: ...}`.

### 3b. MMR diversity

- New method on `VectorIndex` (the sanctioned embedding owner): `mmr_order(scope, query_text,
  card_ids, lambda_)` — pulls the candidates' **stored** embeddings from the Chroma collection
  (`collection.get(ids=..., include=["embeddings"])`) plus the query embedding, and returns the MMR
  ordering (λ≈0.7 default; relevance term = rerank/fused score when available, else 1−distance).
  The pairwise-similarity math lives in `index.py` only.
- Applied at two points: (i) the brief ordering fed to the reflector (diverse slate to judge),
  (ii) never after the reflector — the reflector's selection is final; the auction stays the
  0..N reliability filter it is.
- Config: `ResearchConfig.mmr: {enabled: false, lambda: 0.7, scope: desc_expl}`.

### 3c. Card-stats-aware retrieval (reputation + novelty into ranking and briefs)

Today reputation enters only *after* the reflector (auction over `BetaBinomialReputation` /
`BDProximityReputation` posteriors, `reader.py:236–258`), and selection has **zero novelty
pressure**. Fold both into retrieval:

- **Stats line in briefs**: extend `card_brief` with one compact line resolved through the same
  authority the auction bids on (`ReputationModel.card_stats` → `block_from_events`,
  `reputation.py:62`): `stats: {intro_events} uses, P(help) lo20 {p_help_lo20:.2f}{" confident" if
  efficacy_confident}, median gain {IntroGain_best_median:+.4f}` — omitted for no-evidence cards
  (cold reads as cold, not as bad). The reflector's system prompt gains one rule: *"Use stats as
  supporting evidence among task-fit candidates; never select a task-mismatched card on stats, and
  treat missing stats as neutral."* (mirrors the existing fitness rule).
- **Fused ranking score** (orders briefs + tail-drop; consumed, not decided, by the reflector):
  `score = w_sem · sem + w_rep · p_help_lo20 + w_nov · novelty`
  - `sem` = cross-encoder score when rerank enabled, else `1 − normalized_distance`.
  - `p_help_lo20` — the pessimistic quantile, deliberately NOT `p_help_mean` (known loophole:
    posterior mean saturates ~0.9 and washes regressions); missing block → neutral 0.5.
  - `novelty` = decay in recent use: `1 / (1 + recent_events)` where `recent_events` counts the
    card's `gain_events` with `context.timestamp` in a trailing window — derivable from data the
    Card already carries (`gain_events`, `DecisionContext.timestamp`), no new plumbing. This is the
    first novelty axis in selection (addresses the ~79×-retry pathology).
  - Defaults `w_sem=1.0, w_rep=0.25, w_nov=0.25`, tuned ONLY on the offline harness's tuning split.
- Auction unchanged: `ThompsonAuctioneer`/budgeter still gate injection; this layer fixes what the
  reflector *sees and prefers*, the auction keeps vetoing confidently-harmful cards.

---

## 4. OFFLINE eval protocol

Two components: a replay harness over the four existing run banks, then counterfactual mutation
experiments for the causal read. All offline; no live evolution runs.

### Data inventory (verified on disk)

| Run | Dir | Assets |
|---|---|---|
| V1, V2 | `/home/jovyan/gigaevo/outputs/memory_rebuild_polishcheck_2026-07-05/V{1,2}/` | `memory/cards.json` (terminal bank incl. `gain_events`), `memory/chroma/` (persisted arctic-embed-m-v1.5 vectors + fingerprint), `memory/memory_events.jsonl` (MEMORY_RESEARCH steps, MemoryReadSelection with candidate/auction/selected ids + slates), `memory/write_ledger.jsonl` (timestamped card births/merges/evictions), `llm_io/memory.jsonl` (full planner/reflector transcripts incl. REQUEST text), `storage/heilbron/programs/*.json` (V1: 379 children with `memory_injected_idea_ids`, `memory_base_id`, `memory_base_metrics.fitness`) |
| G1, G2 | `/home/jovyan/gigaevo/outputs/memory_rebuild_full_nogate_2026-07-04/G{1,2}/` | same layout |

Safety: V dirs are being written by live runs at design time — the harness operates on **read-only
snapshot copies** (rsync into the experiment scratch dir once V1/V2 stop; G dirs are complete and
copyable now). Opening a copied `memory/chroma` requires the identical `EmbedConfig`
(fingerprint guard in `index.py` fails loudly otherwise) — replay config mirrors the run config.

### 4a. Replay harness (held-out reads, old vs new)

**Episode reconstruction.** One episode per historical `MemoryReadSelection`: the REQUEST
(mutation-grounded query) recovered from the `llm_io/memory.jsonl` reflector/planner transcripts
(join on `decision_id`), plus the episode timestamp. **Time-faithful candidate universe without
rebuilding banks**: pass `exclude_ids = {cards whose first write_ledger row postdates the episode}
∪ historical exclude_ids` to `VectorIndex.query` — the store's own exclusion mechanism hides
future-born cards. (Caveat logged per episode: merged/evicted card *text* is terminal-state;
episodes whose historical candidate ids are no longer in the terminal bank are flagged and dropped
from scoring rather than papered over.)

**Splits.** Per run, episodes split by iteration blocks (first/second half alternating) into
TUNE (weight/λ/model selection, §3) and HELD-OUT (reported). Nothing is tuned on held-out.

**Tier 1 — no-LLM ranking metrics** (cheap, every candidate config):
- Outcome labels: from `storage/*/programs/*.json`, a (card, episode-context) pair is POSITIVE when
  the card was injected into a child whose fitness delta (child − `memory_base_metrics.fitness`)
  > 0, NEGATIVE when < 0; context matching by parent MAP-Elites cell (same bucketing as
  `BDProximityReputation`) with global fallback.
- Score old ranking (raw distance order) vs new (fused/MMR order) on held-out episodes:
  nDCG@5, Recall@10 against positives, slate diversity (mean pairwise stored-embedding distance,
  computed in `index.py`), and duplicate-pressure proxy (share of top-5 that are program exemplars
  from the parent's own lineage).
- Honesty note: labels are off-policy (only historically injected cards have outcomes) — Tier 1 is
  a **tuning signal**, not the ship decision; §4b is the causal check.

**Tier 2 — LLM reflector replay** (defect metrics; the direct test of §1/§2):
- Re-run the reflection loop offline on ~200 held-out episodes × {old prompts+renderer, new
  prompts+renderer}, same candidates, proxy Qwen (`qwen_instruct` memory-llm config,
  `http://10.232.89.98:4000/v1`, `OPENAI_API_KEY` from `/home/jovyan/gigaevo/.env`,
  `NO_PROXY` includes `10.232.89.98`). ≈ 800–1200 structured calls total.
- Metrics per arm: reflect-calls-on-truncated/elided slate %, held-id re-query rate, budget-death
  rate, explicit-empty-on-populated-slate rate, non-empty selection rate, slate width, and
  selection overlap with the historical G decisions (sanity anchor).

### 4b. Counterfactual mutation experiments (causal, ~30 parents)

- **Parents**: ~30 sampled from G/V `storage/heilbron/programs/*.json` snapshots — valid,
  iteration ∈ [50, 300] (warm bank), stratified by run (V1/V2/G1/G2) × base-fitness quartile.
  Each parent brings its own run's bank+chroma snapshot and its recorded mutation context.
- **Arms** (same parent, same mutation scaffold, only the memory block differs):
  - **A** old retrieval: current prompts + current `research.py` → reader → rendered cards.
  - **B** new retrieval: P0+P1 (+ any §3 layer that won Tier 1/2) → rendered cards.
  - **C** no cards: empty memory block (`NullMemoryProvider`-equivalent path).
- **Execution**: 3 mutations per parent per arm (LLM stochasticity) → 270 mutations. Mutation LLM =
  `Qwen3-235B-A22B-Thinking-2507` via the proxy (mirrors the live runs verbatim — same
  `llm_base_url`/`model_name` overrides); retrieval agents on `qwen_instruct`. Reuse the existing
  mutation-agent + provider seams (`gigaevo/memory/provider.py`, `MemoryContextStage` inputs)
  rather than a bespoke prompt builder — the harness drives the same code path the engine does.
- **Evaluation**: each child scored by the heilbron evaluator (`problems/heilbron/validate.py` +
  `metrics.yaml` through the standard evaluation stage), OMP/MKL capped ≤ 8. Primary outcome:
  fitness delta (child − parent).
- **Analysis** (mirrors round 2 so results are comparable): OLS `delta ~ base_fit + arm` on valid
  children; paired per-parent arm means (Wilcoxon, A vs B, B vs C); jump rate (delta > +0.002);
  plus per-arm injection funnel stats for A/B. Power honesty: n≈90/arm resolves only effects
  ≳0.003 — round 2's measured injection effect is +0.0005, so the **decision rule** is:
  ship if B ≥ A and B ≥ C on fitness delta (no-harm guardrail, one-sided) AND B beats A on the
  funnel/ranking metrics; a B-vs-C fitness win is upside, not a requirement.

### Prediction table

| # | Metric (held-out / counterfactual) | Old (measured V1/V2) | Predicted new | Falsified if |
|---|---|---|---|---|
| 1 | Reflect calls on truncated/elided slate | 77–91% | <5% (elided-with-marker only) | >20% |
| 2 | Held-id re-queries per continue-w/-candidates | 54% (V1 191/356) | <5% | >20% |
| 3 | Budget-death empties (share of empties) | 40% | ~0% | >10% |
| 4 | Explicit empty on populated slate (share of reflector calls) | 21.5% | <3% (G: 0.5%) | >8% |
| 5 | Non-empty selection rate (MEMORY_RESEARCH) | 49% / 63.5% | ≥75% (G: ~92%) | <70% |
| 6 | Non-empty slate width (mean) | 2.4 | 4–6 | <3 |
| 7 | Held-out nDCG@5 vs outcome labels | old baseline | ≥ +10% relative | new < old |
| 8 | Slate diversity (mean pairwise distance), MMR on | old baseline | ≥ +15% at nDCG non-inferior | nDCG drops >5% |
| 9 | Counterfactual fitness delta, B vs A (OLS arm coeff) | — | ≥ 0 (guardrail) | B < A at p<.05 |
| 10 | Counterfactual fitness delta, B vs C | — | ≥ 0; wash plausible (round-2 prior) | B < C at p<.05 |

---

## 5. Slicing (minimum-viable first)

1. **Slice 1 (P0+P1)**: brief renderer + budget + omitted-marker; `{step_status}`/final-step;
   held-card feedback; graded duplicate rule. No new models, no new deps. Targeted unit tests.
   Validated by Tier-2 replay on G snapshots + V snapshots (post-stop). This alone is expected to
   clear predictions 1–6.
2. **Slice 2**: replay harness Tier 1 + stats line in briefs (`card_stats` reuse, no ranking change).
3. **Slice 3**: cross-encoder rerank + MMR + fused score, config-gated default-off; tuned on TUNE
   split, reported on HELD-OUT; enabled only if predictions 7–8 hold.
4. **Slice 4**: counterfactual mutation experiment (§4b) → go/no-go for a live V3/V4 polish-check
   re-run pair (fresh dirs, same config as V1/V2, fixes on).

Non-goals: no cache-version salts; no changes to auction/budgeter semantics; no writer-side changes
(FIX-12 spot-check tracked separately); no new memory arms — everything rides the existing
`memory=full` recipe seams.
