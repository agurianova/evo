# GigaEvo

GigaEvo is a **general-purpose, LLM-based optimization meta-framework** — an evolutionary loop (MAP-Elites) where the LLM proposes and mutates candidate Python programs and each task supplies its own fitness. It is **domain-agnostic by design**: tasks live under `problems/` and span tabular regression, spherical codes, heilbron, antenna selection, kissing number, and ~25 more (incl. the HoVer / HotpotQA chain tasks). Treat any new optimization problem as first-class — nothing here is specialized to one domain, and the framework, not the task, is the product.

## Environment

Python: `/home/jovyan/.mlspace/envs/evo/bin/python3`. Entry point: `python run.py problem.name=<name> [overrides]`. Preview config: `--cfg job`.
CLI: `gigaevo` (`pip install -e .`). Run `gigaevo --help` for commands. `-r` accepts `prefix@db[:label]` or a disk storage path `/path/to/storage[:label]` (storage=disk runs).

## Canonical Documentation

Each user-facing surface has exactly one authoritative doc. Keep these in sync **in the same PR** that changes the underlying behavior — never as a follow-up. CI does not catch doc drift; humans rely on these to discover features.

| Surface | Canonical doc |
|---|---|
| Top-level overview, install, quickstart | `README.md`, `docs/QUICKSTART.md` |
| End-to-end usage flows | `docs/USAGE.md` |
| Architecture / package layout | `docs/ARCHITECTURE.md` |
| Contribution workflow | `docs/CONTRIBUTING.md` |
| **`gigaevo` CLI subcommands + every script under `tools/`** | **`tools/README.md`** (Redis data model also lives here) |
| Manifest schema + experiment state machine | `gigaevo/experiment/README.md` |
| Server inventory | `experiments/infrastructure.yaml` |
| Program/iteration vocabulary | `gigaevo/programs/README.md` |

**Rule:** if a PR adds/renames/removes a CLI subcommand, a script in `tools/`, a config field a user touches, or a public symbol cited in any of the above — the same PR must update the canonical doc. Audit `tools/README.md` whenever you touch `gigaevo/cli/` or `tools/`.

⚠️ **The codebase is young and moving fast — assume the docs above and the `gigaevo` / `tools/` CLI help are PARTLY STALE until you check.** Before relying on or citing a doc, diff it against the code (`gigaevo --help`, script `--help`, the actual symbols). When you touch a surface, *polish* its canonical doc to match reality — rewrite drift, don't just append. Stale example commands and removed flags are a known hazard; keeping these current is part of the task, not a follow-up.

## Workflow

State machine: `preregistered → implemented → running → complete` (or `→ invalid`). Hard gate: `gigaevo -e "$EXP" manifest gate <status>`.
Redis: 16 DBs (0-15). Flush: `gigaevo flush --db N --confirm`.
Testing: **always use `/run-tests`** — never pytest directly. Linting: `ruff check . && ruff format --check .`

## Communication — Telegram is the primary out-of-band channel

**Push every key decision and the data behind it to Telegram.** The user runs experiments away from the terminal; Telegram is how they stay in the loop and how they approve or veto. Use `tools.telegram_notify`:

- **Decisions / approvals** — `gate_design_approval`, `gate_launch_confirmation`, `gate_results_signoff`, `wait_for_approval`: block on the user's call for any irreversible or load-bearing step (launch, gate transition, merge, flush).
- **Data / artifacts** — `send_photo` (trajectory & lifecycle figures), `send_document` (PDF reports, CSVs): when a long run finishes or a decision turns on the numbers, send the numbers, not just a summary. Auto-send the PDF report on experiment completion.
- **Status** — `notify(msg)`, `post_fitness_update`, `post_anomaly_alert`: build-phase transitions, smoke pass/fail, launch confirmations, anomalies during runs, completion.

Pass `parse_mode=""` when a message has markdown special characters that aren't deliberate formatting. Use sparingly for purely conversational replies — reserve for things the user would want to see if away from the terminal.

## Working Style

- Surface assumptions and tradeoffs before coding; if something's unclear, stop and ask.
- Minimum code that solves the problem — no speculative abstractions or unrequested config/flags.
- Surgical diffs: every changed line traces to the request; match existing style; don't refactor what isn't broken or delete pre-existing dead code unasked.
- Turn tasks into verifiable goals (esp. bug fixes → a failing test first) and loop until the check passes.
