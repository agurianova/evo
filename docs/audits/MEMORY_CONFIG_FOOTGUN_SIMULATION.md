# Memory config — "new user shoots self in the leg" simulation

**Date:** 2026-06-13 · **Against:** current memory config (pre-unification) · **Method:**
real Hydra compose (`register_resolvers()` + `compose`), evidence inline. This is the
motivation + acceptance bar for the one-`MemorySystem` refactor: **every shot below must
become impossible (or loud) in the new config.**

I played a naive user who has read the README once and wants to (a) run with memory,
(b) save money, (c) tweak a component. Here is where the current config let me hurt myself
*silently* — no error, just wrong or expensive behaviour.

---

## Shot 1 — "I'll set `memory=none` to save money." 💸 (the expensive one)

```
memory=none ideas_tracker=default pipeline=intra_extra_memory
  reader provider = NullMemoryProvider     WRITER tracker = IdeaTracker
```

`memory=` is only the **reader**. The **writer** is a *different* knob (`ideas_tracker=`).
`memory=none` turns the reader off; the gemini-flash writer keeps running and **bills
OpenRouter ~8 h/dataset for cards nobody reads.** This is not hypothetical — it already
happened to the entire 10-dataset nomem campaign (`NOMEM_BASELINE_WRITER_LEFT_ON.md`).
A new user cannot guess that "memory = none" still spends money on memory.

## Shot 2 — "I'll set `ideas_tracker=default` to turn the writer on." (forgot `memory=local`)

```
ideas_tracker=default
  tracker = IdeaTracker   admitter=None   evictor=None   dedup=None
```

The tracker instantiates, but its admitter / evictor / deduplicator are **all silently
`None`**, because every functional field of `ideas_tracker` is `${ref:memory.*}` — its
behaviour secretly depends on the *other* knob. One switch, no error, a quietly lobotomised
writer. (This footgun is currently *encoded as expected behaviour* in a test:
`test_ideas_tracker_admitter_null_without_memory`.)

## Shot 3 — "I'll change the dedup threshold." (which of the two copies?)

```
config/memory/dedup/llm.yaml      : ['top_k_per_query: 10', 'final_top_n: 10', 'min_final_score: 0.05']
config/memory/backend/local.yaml  : ['top_k_per_query: 10', 'final_top_n: 10', 'min_final_score: 0.05']
```

The same five dedup numbers live in **two files**. Edit one and the other silently wins on
whichever code path you hit (`LLMDeduplicator.config` vs the backend factory's `dedup`),
reconciled by hand-sync glue in `shared_memory/memory.py`. There is no single source of truth.

## Shot 4 — "I'll swap the memory LLM to qwen." (where even is it?)

```
config/memory/local.yaml defaults:
  - override /memory/backend@_global_.memory.backend: local
  - override /llms@_global_.memory_llm: gemini_flash_openrouter
```

There is **no `memory/llm=` knob.** The writer/reader LLM is mounted by an `@_global_`
override buried in `memory/local.yaml`'s defaults list. To change it a new user has to
reverse-engineer Hydra's global-package injection — not discoverable from `--help` or `--cfg job`.

## Shot 5 — "These look like four independent reputation knobs."

`${ref:memory.reputation}` is referenced from **4 files** (provider, admitter, evictor,
ideas_tracker) but is **one object**. It looks editable per-consumer; it isn't. Worse: add a
new component and forget the ref, and it silently falls back to a *different default*
reputation — a divergence with no error.

---

## Why these are all the same bug

Every shot is the config faking **object sharing** that Python does natively, via a
`${ref:}` singleton-resolver web across ~18 files. The wiring is data; the user edits data;
the data silently disagrees with itself. Nothing is loud because nothing is *assembled* —
it's referenced.

## Acceptance bar for the refactor (one `MemorySystem`)

| Shot | New config makes it… |
|---|---|
| 1 (money) | one knob `memory={none,reader,writer,full}` — "no memory" is literally `none`; you cannot leave the writer on by accident |
| 2 (silent degrade) | components are assembled inside `MemorySystem`, not `${ref}`'d — a writer always has its admitter/evictor/dedup or it isn't a writer |
| 3 (dedup ×2) | one `CardUpdateDedupConfig`, threaded in Python; no second copy to edit |
| 4 (hidden LLM) | a plain `memory/llm=` group (`gemini`, `qwen_instruct`) — `--cfg job` shows it |
| 5 (fake knobs) | reputation built once, passed by reference; impossible to half-wire |

Plain wiring, same ergonomics as the rest of the config groups.
