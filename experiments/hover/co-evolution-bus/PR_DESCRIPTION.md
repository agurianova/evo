# exp: hover/co-evolution-bus

**Status**: 🟢 Complete
**Branch**: `exp/hover-co-evolution-bus`
**Tracking issue**: #110

## Design

See `experiments/hover/co-evolution-bus/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| B1 | 9 | Treatment: soft fitness + bus co-evolved prompts | standard | 663547 |
| B2 | 10 | Treatment: soft fitness + bus co-evolved prompts | standard | 663641 |
| B3 | 11 | Treatment: soft fitness + bus co-evolved prompts | standard | 663810 |
| PM | 12 | Prompt meta-evolution run (bus hub for B1+B2+B3) | prompt_evolution_multi | 663947 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 4 | 2026-03-22T18:28:44.652861+00:00 | Early checkpoint (~16-20% progress). All 4 runs healthy. Disk full on FUSE mount, top programs saved to /home/jovyan/gigaevo-checkpoints/. |
| 1 | 2026-03-22T19:23:36.061864+00:00 | Checkpoint after relaunch. All 4 runs healthy at gen 0-1. Early stage — no test eval or analyst needed yet. |
| 3 | 2026-03-22T20:18:37.698030+00:00 | Checkpoint 2: All 4 runs healthy at gen 3-4. B2 leads at 77.1%. PM at gen 3 (50.0%) - traceback from ValidateCodeStage is normal mutant rejection, process alive. |
| 5 | 2026-03-22T21:16:48.436321+00:00 | Checkpoint 3: All 4 runs healthy, ~20-24% progress. B2 leads at 77.3%. All treatment checks pass (co-evolved prompts active). PM stagnating at 55.6% (MINOR). Chain servers busy but responsive. |
| 7 | 2026-03-22T22:17:18.514787+00:00 | Checkpoint 4: All 4 runs healthy at ~28% progress. B runs improving: B1 78.0%, B2 78.4%, B3 77.7%. PM stagnating at 53.3% (MINOR). B2 invalidity at 16% (SyntaxErrors in mutants — normal). Treatment active: 12-15 prompt_stats keys per B run, PM archive at 37 prompts. |
| 8 | 2026-03-22T23:17:05.758341+00:00 | Checkpoint 5: All 4 runs healthy at ~33% progress. B runs stable: B1 78.0% (gen 7), B2 78.4% (gen 8), B3 77.7% (gen 10). PM recovered to 57.1% (gen 8), archive at 43 prompts. B3 showing strategy rejections (14) — frontier getting harder to improve. Approaching 50% gate for test eval. |
| 9 | 2026-03-23T00:16:53.153154+00:00 | Checkpoint 6: All 4 runs healthy at ~37% avg progress. B runs in extended plateau: B1 78.0% (gen 8), B2 78.4% (gen 9), B3 77.7% (gen 11). Strategy rejections climbing (B1:14, B3:18) — frontier hard to improve. PM stagnating at 50.0% (gen 9), archive at 46 prompts. B3 at gen 11, 2 gens from 50% test eval gate. |
| 10 | 2026-03-23T01:16:52.164619+00:00 | Checkpoint 7 (50% gate): B3 at gen 13 triggered mid-run test eval. B runs plateaued at ~78% for 7+ gens. Strategy rejections high (19-25). PM archive at 51 prompts. Test eval running in background. |
| 13 | 2026-03-23T03:12:01.115409+00:00 | Checkpoint 8: B2 broke plateau to 79.2% (gen 13). B3 at gen 16 (64%). Strategy rejections climbing (B1:34, B2:30, B3:39). PM archive at 65 prompts. Mid-run test eval + analyst already completed at CP7. |
| 13 | 2026-03-23T03:15:14.650244+00:00 | Checkpoint 9: No gen advance since CP8 — runs mid-generation (val cycles 30-40min). All 4 runs healthy. B1:12, B2:13, B3:16, PM:13. Strategy rejections: B1:34, B2:30, B3:39, PM:24. |
| 15 | 2026-03-23T04:15:19.240356+00:00 | Checkpoint 10: All runs advanced 1 gen since CP8. B1 new rank02 at 76.8%. B3 at gen 17 (68%). Plateau persists: B1 78.0% (6+ gens), B2 79.2% (1 gen), B3 77.7% (10+ gens). All 4 runs healthy, 0 critical. |
| 16 | 2026-03-23T05:16:48.871783+00:00 | Checkpoint 11: B3 at gen 19 (76%), approaching completion. B2 gen 16, B1 gen 14, PM gen 15. Fitness plateau continues: B1 78.0%, B2 79.2%, B3 77.7%, PM 50.0%. Diagnose CRITICAL on B1 is false positive (SyntaxError from mutant, not crash — PID alive, log active). All runs healthy. |
| 17 | 2026-03-23T06:16:34.109844+00:00 | Checkpoint 12: B3 at gen 21 (84%), approaching completion. B2 gen 18, B1 gen 16, PM gen 17. Fitness plateau persists: B1 78.0% (9+ gens), B2 79.2% (5+ gens), B3 77.7% (14+ gens). B1 CRITICAL false positive (SyntaxError mutant). All runs healthy. |
| 19 | 2026-03-23T07:16:34.675735+00:00 | Checkpoint 13: B3 at gen 22 (88%), 3 gens from completion. B2 gen 19, B1 gen 17, PM gen 18. PM recovered to 55.6% (was 50.0%). Fitness plateau: B1 78.0%, B2 79.2%, B3 77.7%. All 4 runs healthy, 0 critical. B3 ETA ~3 hours. |
| 20 | 2026-03-23T08:16:48.917529+00:00 | Checkpoint 14: B3 at gen 23 (92%), 2 gens from completion. B2 improved to 79.56% (broke 79.22% plateau at gen 20). B1 gen 18, PM gen 19. All 4 runs healthy, 0 critical. Approaching closeout — B3 first, then B2, B1, PM. |
| 21 | 2026-03-23T09:16:44.900723+00:00 | Checkpoint 15: B3 COMPLETED at gen 25/25 (final fitness 77.78%). B2 gen 21 (84%), B1 gen 19 (76%), PM gen 20 (80%). B2 holds at 79.56%. All remaining runs healthy. First run complete — awaiting B1, B2, PM before closeout. |
| 22 | 2026-03-23T10:17:22.032102+00:00 | Checkpoint 16: B3 complete (25/25). B2 gen 23 (92%), B1 gen 21 (84%), PM gen 22 (88%). B2 holds at 79.56%. PM at 55.0%. All runs healthy. B2 should complete next (~2h), then B1, PM. |
| 23 | 2026-03-23T11:16:17.312974+00:00 | Checkpoint 17: B3 complete. B2 at gen 24 (96%), 1 gen from completion. B1 gen 21 (84%), PM gen 22 (88%). All healthy. B2 finishes next (~1h). |
| 24 | 2026-03-23T12:16:55.290073+00:00 | Checkpoint 18: B2+B3 COMPLETE (25/25). B1 at gen 23 (92%), 2 gens remaining — last treatment run. PM at gen 24 (not blocking closeout). Final B2: 79.56%, B3: 77.78%. B1 ETA ~2h. Ready for closeout once B1 finishes. |
| 24 | 2026-03-23T13:16:48.427113+00:00 | Checkpoint 19: B2+B3+PM all COMPLETE. B1 at gen 24 (96%), 1 gen remaining — final treatment run. B1 ETA ~1h. Ready for closeout once B1 finishes. |

## Baseline

Reference: `hover/feedback_softfit` (mean=54.37, metric=test_retrieval_coverage_discrete)

## Archives

_(pending)_
