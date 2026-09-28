# SOTA RAG Retrieval Design — Literature Review for Idea-Card Retrieval (2024–2026)

**Date:** 2026-07-05
**Purpose:** Ground the memory-rebuild card-retrieval redesign in current retrieval literature.
**Our setting (recap):** bank of ~60 short "idea cards" (strategy/insight snippets with reputation/gain stats: IntroGain, p_help posterior, use counts); per-read k≤5; query = parent program/mutation context; downstream reward = child fitness delta. Known failure modes from our own audits: novelty gate caused a fitness regression when too strict, but card selection has ZERO novelty pressure (one card injected 60–120×), p_help posterior saturates ~0.9 (over-injects neutral cards), mutator use-rate ~4%, cards ~89% prior-redundant.

**Framing that matters before any technique:** our problem is NOT web-scale RAG. With N≈60 candidates, recall is a solved problem — every "retriever" can score the *entire bank* exhaustively per read. The literature's recall-stage machinery (ANN indexes, hybrid recall, multi-hop search) is mostly irrelevant; what transfers is the **ranking objective** (utility vs similarity), **set composition** (diversity/redundancy), **explore–exploit** (feedback-aware selection), and **packing** (order in prompt). The closest literature lineage is not classic RAG but (a) in-context exemplar selection, (b) agent experience memory (ReasoningBank, Dynamic Cheatsheet, Memento), and (c) context design inside evolutionary LLM loops (AlphaEvolve/ShinkaEvolve).

---

## 1. Agentic / iterative retrieval (Search-R1 family, RL agentic search)

**What it is.** The model interleaves reasoning with search actions over multiple rounds: it decides *when* to retrieve, reformulates queries, and stops when evidence suffices. Search-R1 and R1-Searcher train this behavior with outcome-reward RL; 2025–2026 extensions add process rewards, adaptive search depth (AutoSearch), multi-tool retrieval (MARAG-R1), and token-efficiency (TeaRAG). A comprehensive survey: *RL-based Agentic Search* ([arXiv:2510.16724](https://arxiv.org/abs/2510.16724)).

**Evidence.** Consistent multi-hop QA gains over fixed single-shot retrieval (Search-R1, ReSearch); the 2026 wave focuses on reducing over-searching (AutoSearch, [arXiv:2604.17337](https://arxiv.org/pdf/2604.17337)) because naive agentic loops burn tokens for marginal accuracy.

**Applicability to us.** Weak. The value of agentic retrieval comes from decomposing complex information needs over large corpora across hops. Our need is single-hop over 60 items; there is nothing to "hop" to. The one transferable idea is the *decide-whether-to-retrieve* action (see §6 adaptive retrieval) — given our memory-inert findings, "inject 0 cards" should be a first-class action, not a failure.

**Verdict: SKIP** (except the retrieve-or-not decision, folded into §6).

---

## 2. Rerankers: cross-encoders and LLM (listwise) rerankers

**What it is.** Two-stage ranking: cheap recall then precise scoring. Cross-encoders (monoT5, bge-reranker-v2-m3, mxbai-rerank-v2, Qwen3-Reranker) jointly encode query+doc. LLM rerankers do zero-shot pointwise/pairwise/listwise ranking (RankGPT), or distill it into open models (RankVicuna → RankZephyr); RankLLM packages these reproducibly ([arXiv:2505.19284](https://arxiv.org/html/2505.19284v1)).

**Evidence.** Wang et al.'s RAG best-practices ablation found reranking one of the highest-leverage modules; monoT5 best avg-score/latency tradeoff ([arXiv:2407.01219](https://arxiv.org/abs/2407.01219)). RankZephyr ≈ RankGPT-4 on several tasks. The EMNLP-2025 empirical analysis ([arXiv:2508.16757](https://arxiv.org/pdf/2508.16757)) tempers the hype: LLM rerankers shine on *familiar* query patterns, degrade on novel ones, and lightweight cross-encoders are often comparable at far lower cost. Model size ≠ quality: 150M-class rerankers (Ettin, gte-reranker-modernbert-base) match 1B+ models on Hit@1 ([Ettin reranker blog](https://huggingface.co/blog/ettin-reranker)).

**Applicability to us.** Strong, and unusually cheap: with N=60 we can cross-encode the *whole bank* against the parent context every read (60 pairs ≈ milliseconds on CPU-class budget) — no recall stage at all, no bi-encoder approximation error. This directly attacks a real weakness: our bi-encoder (arctic-embed-m-v1.5) scores card text against parent context independently; a cross-encoder reads them *jointly* and can judge "does this strategy apply to this program's current bottleneck", which is an entailment-like judgment, not a similarity one. An LLM listwise rerank is also viable (one call, 60 short cards fit trivially) but adds latency/cost per mutation and, per 2508.16757, is not reliably better than a good cross-encoder — and our queries (evolving programs) are exactly the "novel query" regime where LLM rerankers wobble. Caveat: off-the-shelf rerankers are trained on QA/passage relevance, not "strategy applies to code" — expect a modest, measurable gain, not a step change; validate on our retrieval-eval harness (the one used for the embedder sweep) before shipping.

**Verdict: ADOPT (cross-encoder full-bank scoring as the relevance leg; skip LLM listwise reranking for the hot path).**

---

## 3. Hybrid dense + sparse retrieval (BM25 + embeddings, RRF)

**What it is.** Run lexical (BM25/SPLADE) and dense retrieval in parallel, fuse via Reciprocal Rank Fusion or weighted scores. Failure modes are complementary: BM25 anchors exact identifiers/terms; dense handles paraphrase.

**Evidence.** Robust, boring, consistently positive at corpus scale: RRF hybrid beats both constituents across metrics (e.g., +8.1pp Recall@5 on TAT-DQA, [arXiv:2604.01733](https://arxiv.org/html/2604.01733v1)); widely recommended as the minimum viable baseline for RAG deployments ([hybrid search reference](https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026)); Wang et al. recommend Hybrid (±HyDE) as the retrieval module ([arXiv:2407.01219](https://arxiv.org/abs/2407.01219)).

**Applicability to us.** Marginal. Hybrid's value is *recall* insurance at scale; at N=60 with exhaustive scoring, there is no recall problem to insure. The residual argument: cards mention concrete code tokens (function names, ops like `np.linalg.eigh`, "annealing schedule") where exact lexical match against the parent source is a genuinely different signal than embedding similarity — a BM25 score over 60 docs costs nothing and can be one feature in the final ranking blend. But if we adopt a cross-encoder (§2), it largely subsumes this.

**Verdict: SKIP as an architecture; optionally keep BM25-over-bank as one cheap feature in the score blend if we build a multi-signal ranker anyway.**

---

## 4. MMR / diversity-aware set selection

**What it is.** Select the retrieved *set*, not top-k independently: MMR greedily picks items by relevance minus max-similarity-to-already-picked. Modern variants: Dartboard / *relevant information gain* — maximize a probabilistic measure of total query-relevant information in the set, from which diversity emerges without a λ knob ([arXiv:2407.12101](https://arxiv.org/abs/2407.12101), SOTA on the RGB benchmark vs explicit relevance+diversity objectives); AdaGReS does redundancy-aware greedy selection under a token budget ([arXiv:2512.25052](https://arxiv.org/pdf/2512.25052)); for in-context exemplars, MMR-selected demos beat pure nearest-neighbor by covering multiple aspects.

**Evidence.** Gains are consistent wherever top-k items are mutually redundant — which is precisely the small-corpus, semantically-clustered regime. For k≤5 from a bank whose cards are ~89% prior-redundant and cluster heavily (our own finding), independent top-k is near worst-case: it returns 5 paraphrases of the bank's densest cluster.

**Applicability to us.** Direct and high-leverage. This is the *selection-side* answer to our novelty findings: the admission-side novelty gate regressed fitness when it blocked writes (gate-off A/B closed 2026-07-05), but read-side diversity costs nothing at write time — the bank keeps everything, and each read composes a non-redundant slate. It also structurally caps the "one card injected 60–120×" pathology when combined with §5 exploration: a dominant card can anchor the slate, but its paraphrase-neighbors can't fill the remaining slots. Implementation is trivial at N=60: MMR over cached card embeddings, or Dartboard's information-gain objective if we want knob-free. This composes with reputation: run MMR over utility-weighted scores (§5), not raw similarity.

**Verdict: ADOPT (highest confidence / lowest cost of everything in this review).**

---

## 5. Utility / feedback-aware retrieval — retrieval that learns from downstream reward

**What it is.** Replace "semantically similar" with "useful for the downstream task" as the ranking objective, using downstream signal as supervision. Lineages:
- **Retriever training from LM feedback:** REPLUG (answer-likelihood as passage utility), LLM-R (reward model on LLM feedback → distill into bi-encoder; +consistent gains across 30 tasks, [arXiv:2307.07164](https://arxiv.org/abs/2307.07164) / EACL 2024), RA-DIT, LLM-Embedder, Reward-RAG ([arXiv:2410.03780](https://arxiv.org/html/2410.03780v1)), DRO/direct retrieval-augmented optimization (2025).
- **Utility beyond single-passage relevance:** SCARLet (EMNLP 2025 main, [aclanthology 2025.emnlp-main.33](https://aclanthology.org/2025.emnlp-main.33.pdf)) estimates passage utility via *perturbation-based attribution* on shared contexts, explicitly modeling inter-passage interactions; consistently improves RALM performance across ten datasets vs similarity-trained retrievers.
- **Learned retrieval *policies* over experience memory:** Memento ([arXiv:2508.16153](https://arxiv.org/abs/2508.16153)) is the standout 2025 result — an agent with a growing Case Bank whose case-*retrieval* policy is trained online with RL (Q-function over cases) from episode reward, no LLM fine-tuning; top-1 GAIA validation (87.88% Pass@3), +4.7–9.6pp absolute on OOD tasks attributable to case-based memory.
- **Bandit selection:** contextual bandits / Thompson sampling for choosing prompts/examples/arms from downstream reward is standard 2024–2025 practice; the key documented pitfall is overconfident premature commitment without exploration ([arXiv:2403.15371](https://arxiv.org/pdf/2403.15371)). ShinkaEvolve (§9) validates bandit selection *inside an evolutionary code loop* specifically.

**Evidence.** This is the most consistently positive family in the review: every method that swaps similarity supervision for utility supervision reports gains (REPLUG, LLM-R, SCARLet, Memento). The mechanism argument is also the strongest: similarity is a proxy; we *have* the true target signal (fitness delta of children whose mutation used the card).

**Applicability to us.** This IS our gain-stats design, and the literature says we are pointing the right way but executing the wrong estimator. Concrete mappings:
1. **Don't train a retriever — learn per-card values.** With 60 arms and repeated pulls, this is a contextual bandit, not a learning-to-retrieve problem. LLM-R/SCARLet-style retriever distillation needs thousands of labeled (query, passage, utility) triples; we have dozens of noisy pulls per card. Per-card posterior over "P(fitness gain | card injected)" + Thompson sampling is the sample-efficient equivalent — and we already have a Thompson-EV walkthrough (`experiments/thompson_ev_walkthrough.md`) and the calibrated-auction work.
2. **Fix the credit-assignment estimator, not the architecture.** Our p_help saturation (~0.9, washing out 31/32 parent regressions) is exactly the naive-utility failure SCARLet identifies: single-item attribution ignores set effects and baseline rates. The fixes that transfer: (a) *counterfactual/baseline-relative* reward — score a card by child-fitness delta **vs the same-parent no-card / other-card rate** (SCARLet's perturbation attribution ≈ our A/B within parent lineage; REPLUG's likelihood-vs-prior ≈ IntroGain, which our audit already found to be the honest signal); (b) attribute to the *slate*, then distribute (Shapley-lite: leave-one-out over the k≤5 slate is 5 extra evaluations only when a slate wins big — or cheaper, uniform within-slate credit with slate-level baseline).
3. **Exploration is mandatory, not optional.** The 60–120× single-card injection is textbook greedy-bandit collapse. Thompson sampling over the per-card gain posterior gives principled decay of over-pulled arms (posterior tightens → sampled advantage shrinks) and automatic exploration of low-count cards — solving both repeat-injection and the "reputation ignored by selection" finding in one mechanism.
4. **Memento's blend is the architecture to copy:** final score = α·relevance(query, card) + (1−α)·learned value(card [, context features]) — non-parametric leg for cold cards, parametric leg once counts accumulate.

**Verdict: ADOPT (the centerpiece — Thompson-sampled utility posterior blended with cross-encoder relevance, with baseline-relative slate-level credit assignment).**

---

## 6. Self-RAG / CRAG-style reflection and adaptive retrieval

**What it is.** Self-RAG trains reflection tokens: retrieve-or-not, is-passage-relevant, is-output-supported ([OpenReview](https://openreview.net/forum?id=hSyW5go0v8), ICLR 2024). CRAG bolts on a lightweight retrieval evaluator that grades retrieved evidence and triggers corrective action (re-retrieve, fall back, discard) when it is poor. Google's *Sufficient Context* (ICLR 2025, [arXiv:2411.06037](https://arxiv.org/abs/2411.06037)) shows a 93%-accurate autorater for "does this context suffice", and that sufficiency+confidence-gated *selective generation* improves correct-answer fraction by 2–10% across Gemini/GPT/Gemma.

**Evidence.** A 2025 MDPI benchmark across 12 RAG variants: Self-RAG lowest hallucination (5.8% vs 12–14% standard); CRAG best practicality (one added classifier, P@5 0.69, 10.5% hallucination at 240ms). Solid, but the wins are on *factual grounding* metrics, not generation quality for creative tasks.

**Applicability to us.** Partial. Full Self-RAG (training reflection tokens) is out of scope — we don't control mutator model weights. What transfers is the **CRAG-shaped cheap gate on the read path**: score the best-available card slate for *applicability to this parent* and allow the outcome "inject nothing" (or fewer than k) when the bank has nothing relevant — cards-as-noise is a live risk given the 4% mutator use-rate and dilution findings on heilbron. Concretely: a threshold on the §2 cross-encoder score (or a tiny LLM applicability check, but that adds a call per mutation) under which the memory section is omitted from the prompt entirely. This is the read-side, non-destructive cousin of the admission novelty gate that failed: it never blocks writes, only skips useless injections. Risk: another gate = another regression vector; must A/B with the gate as the *only* delta, and the threshold must be permissive (target: cut the bottom ~20–30% of injections, not median).

**Verdict: PARTIAL ADOPT (CRAG-style inject-or-skip threshold on the read path; skip Self-RAG training and output-critique loops).**

---

## 7. Context-window packing, ordering, truncation

**What it is.** Where retrieved items sit in the prompt changes how much the model uses them. Lost-in-the-middle (U-shaped attention; start/end favored) persists in 128K-window 2025 models; *Found in the Middle* traces it to positional attention bias; RoPE long-distance decay is implicated. Mitigations: reorder so the best content sits at the edges ("position engineering"), calibration, order-invariant architectures (RoToR, [arXiv:2502.08662](https://arxiv.org/pdf/2502.08662)). Do-RAG-systems-suffer-positional-bias ([arXiv:2505.15561](https://arxiv.org/html/2505.15561v1)) adds nuance: magnitude/direction of the bias is model-family-dependent (Qwen-2.5 stronger bias than Llama-3 — relevant: our production mutators are Qwen). Compression (LLMLingua/LongLLMLingua, ECoRAG, EXIT) prunes redundant context; LongLLMLingua couples query-aware compression with document reordering.

**Evidence.** Wang et al.'s ablation: **reverse repacking** (most relevant item closest to the query/instruction end) beat forward and sides orderings ([arXiv:2407.01219](https://arxiv.org/abs/2407.01219)). Compression papers report up to 23% downstream improvement — but on long, noisy retrieved passages.

**Applicability to us.** Ordering: yes, free. Our k≤5 cards land inside a long mutation prompt (task description, parent code, metrics, insights) — the cards' position within that prompt, and the order of cards within the memory block, are currently unexamined. Adopt the reverse-repacking rule: memory block adjacent to the mutation instruction, cards ordered worst→best so the highest-utility card is last/nearest the instruction. Given Qwen's stronger positional bias, this is plausibly a piece of the 4%-use-rate story and costs one line to change. Compression: no — cards are already distilled snippets; compressing them is anti-goal (and our feedback rules forbid regex-scrubbing/rewriting LLM content downstream). Truncation handling: with k≤5 short cards, a token budget guard (drop lowest-utility card first, never mid-card truncation, AdaGReS-style budget-aware selection if budgets tighten) is all that's warranted.

**Verdict: ADOPT ordering (reverse repacking + block placement near instruction); SKIP compression.**

---

## 8. Agent experience memory (the closest lineage to idea cards)

**What it is.** Banks of distilled experience retrieved into agent context — structurally identical to our cards:
- **ReasoningBank** (Google, 2025; [blog](https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/)): memory items = {title, description, distilled reasoning/insight}; distilled from BOTH successes and **failures** (counterfactual pitfall items: "always verify X before Y"); embedding retrieval into context; +8.3pp WebArena / +4.6pp SWE-Bench-Verified success with Gemini-2.5-Flash, ~3 fewer steps per task; memory-aware test-time scaling (parallel trajectories + self-contrast distillation) adds a further ~3pp.
- **Dynamic Cheatsheet** (Suzgun et al., EACL 2026; [arXiv:2504.07952](https://arxiv.org/abs/2504.07952)): black-box model + persistent evolving memory of strategies/code snippets, curated at inference time with *no ground-truth labels*; Claude 3.5 Sonnet +27% AIME'24 / +30% AIME'25, +9% GPQA-Diamond. Key design: memory is actively *rewritten/curated* (merge, generalize, evict), not append-only.
- **ExpeL / AWM:** cross-task insight extraction and workflow-level memory without parameter updates — the 2024 baseline generation.
- **Memento** (§5): adds the learned retrieval policy over the case bank.
- **Evo-Memory** ([arXiv:2511.20857](https://arxiv.org/pdf/2511.20857)) benchmarks self-evolving memory; the lifelong-adaptation literature (e.g., [arXiv:2605.09315](https://arxiv.org/pdf/2605.09315)) documents degradation/forgetting risks in exactly our setup.

**Evidence.** The strongest end-to-end numbers of any family here (DC's +27–30pp; ReasoningBank on SWE-Bench, the closest benchmark to code mutation). Two design deltas vs our system stand out: (1) **failure-derived cards** — our bank distills what worked; ReasoningBank shows pitfall/anti-pattern items from failed trajectories carry unique signal (and our error-driven-authoring recommendation from the triviality analysis independently converged on this); (2) **active curation** — DC's merge/generalize/evict loop attacks prior-redundancy (our 89% figure) at the bank level rather than filtering at admission (which regressed) or read (MMR, §4). Note curation partially overlaps the "cloud collapse" phase already planned in the memory refactor.

**Applicability to us.** This family is our system's actual peer group; treat it as the design baseline the redesign is measured against. Adopt failure-distilled cards and periodic LLM curation passes; both are writer-side and compose with everything above.

**Verdict: ADOPT (failure-derived pitfall cards + periodic merge/generalize curation pass).**

---

## 9. Retrieval/context design inside evolutionary LLM loops (domain-matched)

**What it is.** How AlphaEvolve/FunSearch-lineage systems compose mutation-prompt context: FunSearch uses best-shot prompting from island populations; AlphaEvolve samples "inspiration" programs from a program database into each mutation prompt; **ShinkaEvolve** ([arXiv:2509.19349](https://arxiv.org/abs/2509.19349), Sakana 2025) is the most instructive — three mechanisms, all selection-side: (1) adaptive parent sampling balancing exploration/exploitation, (2) **novelty rejection-sampling** on proposals (embedding similarity + LLM-as-novelty-judge) so compute isn't spent re-generating near-duplicates, (3) **bandit-based ensemble selection** (of LLMs, by contribution to fitness improvement). Result: circle-packing SOTA in ~150 evaluations — orders of magnitude fewer samples than prior frameworks; ~2.3% mean ALE-Bench gain.

**Evidence & applicability.** ShinkaEvolve is proof-in-domain that (a) bandit selection driven by *fitness-improvement contribution* works inside exactly our loop type — the same math transfers from "which LLM" to "which card"; (b) novelty pressure pays when applied as *rejection/selection*, not as hard admission blocking — mirroring our gate-off finding. AlphaEvolve's inspiration-sampling is the direct analogue of card injection: inspirations are sampled for quality *and* diversity from the database, per-prompt, not fixed top-k.

**Verdict: ADOPT as design precedent (validates §4 + §5 in-domain; no separate mechanism to build).**

---

## Adoption summary

| # | Technique | Verdict | Cost | Expected effect on known failure modes |
|---|---|---|---|---|
| 1 | Agentic/iterative retrieval | SKIP | — | n/a (no multi-hop need) |
| 2 | Cross-encoder full-bank rerank | ADOPT | low (60 pairs/read) | better applicability judgment than bi-encoder; feeds §6 gate |
| 3 | Hybrid dense+sparse | SKIP (opt. BM25 feature) | ~0 | subsumed by §2 |
| 4 | MMR / info-gain set selection | **ADOPT** | ~0 | kills redundant slates; read-side novelty w/o blocking writes |
| 5 | Utility posterior + Thompson sampling | **ADOPT** | low | fixes 60–120× repeat-injection, p_help saturation, reputation-ignored-by-selection |
| 6 | CRAG-style inject-or-skip gate | PARTIAL | low | stops cards-as-noise dilution; must A/B in isolation |
| 7 | Reverse repacking / block placement | ADOPT | ~0 | plausibly lifts 4% use-rate (Qwen positional bias) |
| 8 | Failure-derived cards + curation pass | ADOPT | med (writer-side LLM calls) | attacks 89% prior-redundancy at the bank level |
| 9 | Evolutionary-loop precedents | reference | — | in-domain validation of 4+5 |

**Composition (one coherent read path):** cross-encoder scores all ~60 cards against parent context (§2) → blend with Thompson-sampled per-card gain posterior (§5) → MMR/info-gain slate selection for k≤5 (§4) → skip injection entirely if top blended score under threshold (§6) → pack memory block adjacent to mutation instruction, ascending utility order (§7). Writer side, independently: failure-distilled pitfall cards + periodic merge/curation (§8). Each stage is independently ablatable; per our variance-floor and single-delta A/B conventions, ship §4+§5 first (cheapest, largest expected effect, in-domain precedent), then §7 (free), then §2, then §6.

---

## Sources

- Search-R1 / RL agentic search survey: https://arxiv.org/abs/2510.16724 ; AutoSearch https://arxiv.org/pdf/2604.17337 ; TeaRAG https://arxiv.org/html/2511.05385v1 ; MARAG-R1 https://arxiv.org/pdf/2510.27569
- RankLLM https://arxiv.org/html/2505.19284v1 ; LLM-reranker empirical analysis https://arxiv.org/pdf/2508.16757 (EMNLP 2025 Findings: https://aclanthology.org/2025.findings-emnlp.305.pdf) ; Ettin rerankers https://huggingface.co/blog/ettin-reranker ; cross-encoder landscape https://aimultiple.com/rerankers , https://www.analyticsvidhya.com/blog/2025/06/top-rerankers-for-rag/
- RAG best practices (reranking/repacking/hybrid ablations): https://arxiv.org/abs/2407.01219 (EMNLP 2024: https://aclanthology.org/2024.emnlp-main.981/) ; hybrid evidence https://arxiv.org/html/2604.01733v1 , https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026
- MMR/diversity: Dartboard relevant-information-gain https://arxiv.org/abs/2407.12101 ; AdaGReS https://arxiv.org/pdf/2512.25052 ; MMR-for-exemplars discussion https://arxiv.org/pdf/2503.09249
- Utility/feedback-aware: LLM-R https://arxiv.org/abs/2307.07164 (EACL 2024: https://aclanthology.org/2024.eacl-long.105/) ; SCARLet https://aclanthology.org/2025.emnlp-main.33.pdf ; Reward-RAG https://arxiv.org/html/2410.03780v1 ; Memento https://arxiv.org/abs/2508.16153 ; LLM in-context exploration failure https://arxiv.org/pdf/2403.15371
- Self-RAG https://openreview.net/forum?id=hSyW5go0v8 ; Sufficient Context https://arxiv.org/abs/2411.06037 (blog: https://research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/)
- Position bias: RAG positional bias https://arxiv.org/html/2505.15561v1 ; RoToR https://arxiv.org/pdf/2502.08662 ; Attention Instruction https://arxiv.org/pdf/2406.17095 ; LongLLMLingua https://arxiv.org/html/2310.06839v2
- Experience memory: ReasoningBank https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/ ; Dynamic Cheatsheet https://arxiv.org/abs/2504.07952 (EACL 2026: https://aclanthology.org/2026.eacl-long.333/) ; Evo-Memory https://arxiv.org/pdf/2511.20857 ; lifelong degradation https://arxiv.org/pdf/2605.09315
- Evolutionary loops: ShinkaEvolve https://arxiv.org/abs/2509.19349 (https://sakana.ai/shinka-evolve/) ; CodeEvolve https://arxiv.org/html/2510.14150v2 ; AlphaEvolve overview https://towardsdatascience.com/googles-alphaevolve-getting-started-with-evolutionary-coding-agents/
