# Fused gemini+qwen CARL tool-diff report — build plan

**Directive (user, 2026-07-04):** wait for both qwen runs to finish → fuse gemini + qwen into
ONE full report; the qwen section must carry the **same illustrations as gemini** (lineage DAG,
winning-chains table, held-out test) → run a couple of review iterations via **subagents + codex**
for readability/clarity/crispness → when converged, send the PDF to Telegram.

## Current state (at plan time)
- Live runs: `runs/armA_qwen` (PID 765414), `runs/armB_qwen` (PID 765443), target `max_mutants=250`.
  At plan time: A 224/250, B 193/250, both ~0.5 prog/min → ETA ~2h for B (slower).
- Background watcher: Bash task `bj19x815e` — exits (and re-invokes me) when BOTH PIDs die.
- Gemini run storage = `runs/armA_shuf` / `runs/armB_shuf` (NOT report_full250; that's the report dir).
- Gemini report to mirror: `report_full250/report.tex` (532 lines) + its figures.
- Qwen interim assets already built: `qwen_snapshot/{report.tex,report.pdf,*.png,*.json, make_*.py, build_pareto_data.py, extract_tokens.py}`.

## Post-completion pipeline (run in order, from repo root, PY=/home/jovyan/.mlspace/envs/evo/bin/python3)

### 0. Confirm completion
- Both PIDs gone; `find runs/arm{A,B}_qwen/storage/chains_hover_full7/programs -name '*.json' | wc -l` ≈ 251 each.
- Grab final winners + IDs: `gigaevo -r <storage_path>` top, or analyze_ab. Record armA/armB best id+fitness.

### 1. Regenerate qwen final figures (in qwen_snapshot/, at 250/arm)
- `extract_tokens.py` → mutation_tokens*.json (fresh)
- `build_pareto_data.py` (uses pareto_build_qwen.json — ADD test_points once held-out done, step 3)
- `analyze_ab.py` → ab_stats.json
- `make_figures.py` → ab_overview / ab_nsteps / ab_tokens
- `make_pareto.py` → ab_pareto / ab_waste
- All from ONE consistent live pull (regen back-to-back).

### 2. Qwen held-out test eval (the panel the interim omitted)
- Build `report_fused/test_eval_spec_qwen.json`: baseline seed + armA winner + armB winner + armB
  lineage (gen1..genN). run_dir = runs/armA_qwen / runs/armB_qwen, id = program uuid prefix.
- Copy `report_full250/test_eval.py` → run it (reuses frozen full7/test.py machinery; needs
  `source /home/jovyan/gigaevo/.env`, NO_PROXY incl 10.232.89.98, HOVER_CHAIN_URL/MODEL). Writes test_metrics_qwen.json.
- Feed the winner test coverages back into pareto_build_qwen.json test_points → re-run step 1 pareto
  so the qwen Pareto right-panel gets a held-out axis like gemini.

### 3. Qwen lineage DAG viz (the "dag etc" illustration)
- Walk parent_id back from armB_qwen winner → base. Extract each program to
  `report_fused/viz_qwen/lineage_NN_*.json` in the format
  `{label,id,parents,generation,mutation,fitness,n_steps,n_tool_steps,spec,llm_diff}`.
  (llm_diff = arm-B CARL diff operator's stated change, from program metadata/stage output.)
- Copy `make_lineage_viz.py` → `report_fused/make_lineage_viz_qwen.py`, update `HERE/VIZ` to viz_qwen,
  update FILES list (filenames, labels, qwen fitness per gen). Produce lineage_graph_qwen.png (+ dags/diffs/matrix).

### 4. Qwen winning-chains table
- Extract armA_qwen best + armB_qwen best step lists (type/tool/deps) for the step-by-step table
  (mirror gemini §"The winning chains"). Note whether qwen arms converge (gemini's did).

### 5. Assemble fused report `report_fused/report.tex`
Structure:
- Shared front: Title (both mutators), Abstract (cross-model thesis), Motivation, Setup (both mutators), Diff language (+ELI5).
- **Part I — gemini-3.5-flash (mid-tier mutator):** validity funnel, fitness, held-out vs feedback baselines,
  token cost (reasoning-instrumentation caveat), cost/quality frontier, structural, winning chains, lineage DAG. (all from report_full250, verbatim numbers.)
- **Part II — Qwen3-235B-Thinking (top-tier mutator):** SAME subsections + SAME illustrations
  (validity, fitness, held-out, tokens [proxy no-reasoning N/A], cost frontier, structural, winning chains, lineage DAG).
- **Cross-model synthesis:** malformed-rate ladder llama ~40% → gemini 38% → qwen 11.5% (model quality
  cuts it ~3×, only schema →0); fitness/cost MARGIN shrinks with mutator strength; validity/legibility/
  exploration hold at every strength. B genuinely better even under strong mutator (0 malformed, $0 waste,
  −18% input, typed diffs, tied ceiling + wider exploration); A leads only mean (B's exploration tax) + cost-to-winner (only because A now wastes little).
- **Engineering deliverable** (usage.py token accounting) — shared, once.
- **Verdict** — the scaling thesis.
- Build via tectonic (conda pdflatex BROKEN). `[H]`+float near longtables. Keep gemini preamble/colors/eli5.

### 6. Review loop (couple iterations)
- Subagents: dispatch 2-3 reviewers (general-purpose / docs-guardian) for readability, clarity, crispness,
  + one correctness/consistency pass (numbers match tables/figures, no gemini↔qwen mixups).
- Codex: run codex CLI review pass on report.tex for prose crispness.
- Apply edits, rebuild, re-review until converged (diminishing returns / no substantive notes).

### 7. Send
- `tools.telegram_notify.send_document(report_fused/report.pdf, caption, parse_mode="")`, HTTPS_PROXY set.

## Constraints
- Commits HELD pending explicit user approval (this + all prior uncommitted work).
- Don't change imports while runs live (moot after completion, but generation scripts import gigaevo — fine post-run).
- Honest numbers; interim→final (qwen becomes final 250 numbers, not the 185/179 interim).
- Cap OMP/MKL/OPENBLAS=8 for any eval; source .env + NO_PROXY for proxy.
- tectonic at ~/.local/bin/tectonic.

## AUDIT FINDINGS 2026-07-04 (MUST be folded into the fused report — rewrites Part I §4.1 narrative)

### F1 — Arm A "malformed JSON" is ~94% a harness artifact, NOT model fragility
Classified every penalty child by content:
- armA_shuf (gemini): 93 penalties = 87 python_emission (`def entrypoint():...`, valid Python!)
  + 2 json_truncated + 1 bad_escape + 1 control_char + 2 valid-JSON-but-penalty.
  TRUE document-syntax breakage: 4/242 ≈ 1.7%, not 38%.
- armA_qwen: 29 penalties = 28 fragment emissions ('steps', 'system_prompt', mid-document
  starts — degenerate/truncated code fields) + 1 valid-JSON-but-penalty. Also not syntax breakage.
ROOT CAUSE: shared MutationStructuredOutput.code Field description says "complete mutated
Python source code... NEVER put JSON" (gigaevo/llm/agents/mutation.py ~line 164) while the
full7 prompt says "code is one COMPLETE wire-format JSON document — not Python". Model obeys
the schema description ~36% (gemini) / ~12% (qwen) of the time. The §4.1 claim "defect scales
with document complexity, not model IQ / strong models don't outgrow it" is FALSIFIED as
attributed; correct claim: the stock rewrite path AS SHIPPED wastes 38%/12% on JSON-genome
problems due to an avoidable schema/prompt contradiction; intrinsic free-rewrite JSON
breakage is ~2% (gemini). Waste dollars remain real as measured; attribution must change.
Malformed-ladder story (llama 40 → gemini 38 → qwen 12 → schema 0) DIES in its current form.
Fix for future runs (NOT while live): problem-appropriate structured-output model (typed
document field or corrected description). Arm B's "0 malformed by construction" still stands.

### F2 — Arm B gemini's 3 completed-invalids are exec_runner infra crashes (exit=1), genome JSON parses fine
Penalty -1000 conflates bad-genome with eval-infra failure; taxonomy note for report. B's
genome-defect count in completed evals: 0.

### F3 — Diff-mode contiguity hack (user question)
Hack = _slots_contiguous post-validator + _compact_payload SILENT slide-left repair
(problems/chains/tool_chain_diff.py:59,123). Could a small schema change kill it?
- prefixItems (the natural fix) explicitly non-portable: schema_compat.py "prefixItems is
  flagged but has no rewrite — avoid it at model level". Correctly ruled out.
- Portable alternatives exist but are NOT small: (a) cons-list nesting (optional `next` per
  slot; pure objects/optionals, portable; 7-deep nesting, applier+render+describe rework,
  legibility risk); (b) top-level anyOf over 7 exact-length variants (portable, but ~4x slot
  instances in schema; input tokens already +46% vs arm A). Verdict: shipped flat-slots
  design defensible; NOT fixable by a *small* schema change under portability constraints.
- REAL FLAW: repair path has ZERO logging — gap-emission frequency unobservable post-hoc.
  Future fix: log+counter in _compact_payload. Blast radius in practice ≈2 pre-persist
  schema errors / 259 calls (gemini); qwen 0 penalties.
- Report wording must disclose silent-repair semantics (non-contiguous emission is
  reinterpreted, not rejected), alongside "only contiguity left to a validator".

### F4 — Fitness-eval stochasticity biases best-fitness comparison
Executor temperature=0.6/top_p=0.95 → fitness is a noisy draw. Gemini pair: B had 239 valid
draws vs A 149 → best-of-N inflation favors B; mean/median safer; held-out single-draw noise
band ~3.7pt discrete vs 4.3pt winner gap = thin margin. Qwen pair (197 vs 199 draws) is the
clean comparison — and it's a tie. Fold into caveats + synthesis.

## RE-RUN DECISION 2026-07-04 (user-ordered, supersedes parts of F1/F3 handling)

User verdict on F1: the schema/prompt contradiction "violates both gemini and qwen arm A
experiment" → fix + re-run, don't just re-attribute in prose.

**Fixes applied (live-safe, user-authorized):**
1. `gigaevo/llm/agents/mutation.py` `MutationStructuredOutput.code` description now
   format-agnostic (any source format, never a fragment/diff/template).
2. `problems/chains/tool_chain_diff.py` `build_schema.validate` logs a WARNING with the
   filled-slot list whenever `_compact_payload` repairs a gap (F3's silent-repair flaw).
Both lint-clean, 93 targeted tests green.

**New runs:** armA_fixed (gemini, pid 885246) + armA_qwen_fixed (qwen 235B, pid 885249),
250 mutants each. Arm B runs stay as-is (unaffected by the fix).

**Report consequences (REPLACES the earlier F1 rewrite plan):**
- Part I = armA_fixed vs armB_shuf; Part II = armA_qwen_fixed vs armB_qwen.
- Regenerate ALL Part I artifacts too: analyze_ab + extract_tokens + make_figures +
  build_pareto_data + make_pareto + held-out test eval for the NEW armA_fixed winner
  (report_full250 scripts, gemini prices). report_full250/ stays frozen as the
  pre-fix record.
- The old armA_shuf/armA_qwen runs become a REPORTED ARTIFACT STUDY: a short section
  documenting the schema/prompt contradiction, the 87/91 + 28/29 python_emission
  decomposition, and the before/after malformed rate once armA_fixed data exists —
  this is now a *finding about structured-output harness hygiene*, not the headline.
- Fresh arm A runs also carry tokens_reasoning + per-candidate executor tokens
  (post-instrumentation-fix), so Part I token section loses its dagger caveats for A.
- Timing caveat to disclose: armB runs predate armA_fixed runs by days; same configs,
  stochastic executor unchanged; acceptable for this report, note in methods.

**Pipeline now gated on FOUR runs:** armB_qwen (finishing), armA_fixed, armA_qwen_fixed
(both fresh), armA_qwen (old — about to finish, no longer load-bearing).
