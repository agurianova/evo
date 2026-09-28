# Memory-rebuild fix batch — proposed commit series (2026-07-05)

Status: VERIFICATION DRY (round 3, 2026-07-05) — round-2 findings (5) fixed
test-first; round-3 refutation review returned no MAJOR, and its 3 cosmetic
MINORs (rq5 retire-row bucketing, digest marker pluralization, librarian
docstring precision) were closed too. Gate: lint clean, 839 passed / 2 skipped
over tests/memory+llm+integration. Every commit held for explicit approval;
push to PR #294 stays HELD.

Grouping rule: one commit per fix (or tight pair sharing files). Each commit
leaves the tree green (its tests ride with it).

| # | Commit (conventional title) | Files | Fix IDs |
|---|---|---|---|
| 1 | `fix(memory): ledger row for novelty rejections; DISCARDED writes no row` | write/admission.py, tests/…/test_admission.py | FIX-2 |
| 2 | `fix(memory): founding events ride NEW admits only; exact-twin dedup bumps provenance` | write/librarian.py, write/admission.py (retire_twin), tests/…/test_librarian.py | FIX-3 + FIX-10 + R2 Docs-F2/W1/W2 (same seam: librarian routing + gate surface) |
| 3 | `refactor(memory): ReputationModel protocol; founding never prices the EV bid` | read/reputation.py, read/reader.py, tests/…/test_reputation.py, tests/…/test_reader.py, tests/memory/read/conftest.py, tools/analyze_bandit_health.py | M1 + FIX-4 + FIX-5 (strict-sign docs in code) + R3 rq5 retire-row bucketing |
| 4 | `feat(memory): anti-redundancy criteria in retrieval reflector; drop dead memory_selector prompt` | prompts/retrieval_reflection/system.txt, prompts/memory_selector/ (D), prompts/__init__.py, tests/llm/test_memory_prompt_guards.py | FIX-6 |
| 5 | `feat(memory): planner bank digest — newest digest_max_cards cards (default 50)` | read/shortlist.py, tests/…/test_shortlist.py, config/memory/full.yaml, config/memory/reader.yaml | FIX-7 (top-K redesign per user decision 2026-07-05) + R2 read-side MINORs (ValueError guard, naive-stamp UTC pin, plural header) |
| 6 | `fix(memory): inline consolidation scoped to freshly added ids` | write/consolidation.py, tests/…/test_consolidation.py | FIX-8 (+ zero-merge cancel log test) |
| 7 | `fix(memory): tombstone harm-evicted exemplars; eviction judges usage only` | write/eviction.py, tests/…/test_eviction.py | FIX-9 (+ founding-strip docstrings) |
| 8 | `fix(memory): restamp drops gain events with no banked card` | write/stats.py, tests/…/test_stats.py | FIX-11 |
| 9 | `fix(prompts): merge only same-mechanism cards, never contradictions` | prompts/consolidate/system.txt, prompts/reconcile/system.txt | FIX-12 + R2 W4 ("Three hard rules" count) |
| 10 | `fix(memory): per-record ingest timeout attribution + sink banks partial results` | write/writer.py, write/librarian.py (sink param), tests/…/test_writer.py | FIX-13 + F1 (tight pair: same seam) |
| 11 | `refactor(memory): freeze extraction models` | write/extraction.py, tests/…/test_extraction.py (frozen pin) | step 6 + R2 W3 |
| 12 | `test(memory): pin novelty gate default off in yaml and signature` | tests/memory/test_config_defaults.py | FIX-1 pin |
| 13 | `docs(memory): sync README + docs/memory.md + reputation report to shipped defaults` | docs/memory.md, gigaevo/memory/README.md, docs/reports/memory_reputation_auction.tex | FIX-14 + R2 docs MAJOR (multi-island fail-fast wording) + MINORs (digest wording, admission_novelty path) |

Ordering note: commit 2 and 10 both touch librarian.py — commit 2 carries the
routing/founding/twin logic, commit 10 carries only the `sink` parameter and its
threading. If the hunks interleave badly, collapse 2+10 into one commit rather
than hand-splitting hunks.

Out of this series (separate concerns, remain uncommitted):
- experiments/static_lever_prompt_baseline/* (issues log, FINDINGS, analyze/make_figures) — static-lever closeout series
- docs/reports/memory_write_system.tex + docs/reports/memwrite_make_figures.py — write-side report, own commit when finalized
- experiments/memory_rebuild_defect_fix_plan.md + this file — plan artifacts; commit last as `docs(experiments)` or leave per user preference
- experiments/memory_rebuild_full_ab/ — live A/B artifacts

Declined items recorded for commit-message notes:
- analyze_bandit_health rq5 test: no tools test infra — declined
- RemoteMemoryStore removal: by-design skeleton — declined
- removal tests: deleted on user veto ("I hate removal tests")
