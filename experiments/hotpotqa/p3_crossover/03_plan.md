# Pre-Registration: <Experiment Name>

**Date**: YYYY-MM-DD
**Pre-registration commit**: `<hash>` ← commit this file BEFORE any code changes
**Design doc**: `experiments/hotpotqa/p3_crossover/01_design.md`
**Review doc**: `experiments/hotpotqa/p3_crossover/02_review.md` (verdict: APPROVED)

---

## Hypothesis

**H₀**:
**H₁**:
**Primary metric**: <metric> at gen <N> on <val/test> set
**Significance threshold**: α =

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `llm_base_url` | Seed | Val set |
|-----|-------|------------|-----------|-----------|----------------|----------------|------|---------|

---

## Controlled Variables

| Field | Value |
|-------|-------|

---

## Success Criteria

---

## Monitoring Plan

- Gen 5: smoke check
- Gen 10: checkpoint eval
- Gen 25: midpoint checkpoint
- Gen 50: final evaluation

Early termination rule:

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|

Watchdog PID:
Launch commit: `<hash>`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

_(Add numbered entries here for any post-registration changes.)_
