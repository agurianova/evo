# exp: hover/memory

**Status**: 🟢 Complete
**Branch**: `exp/hover-memory`


## Design

See `experiments/hover/memory/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| R1 | 4 | Control: no memory | structural_metrics | 1358888 |
| R2 | 5 | Control: no memory | structural_metrics | 1358889 |
| R3 | 6 | Treatment: memory enabled | structural_metrics | 1358890 |
| R4 | 7 | Treatment: memory enabled | structural_metrics | 1358891 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 0 | 2026-04-04T07:29:01.680067+00:00 | Post-restart checkpoint (gen 0-2). Experiment relaunched with new config: evolution=steady_state, scheduling=lpt_chain, algorithm=topology_3d_ret. Treatment adds memory=local. All 4 runs alive and evaluating. Seeds look healthy (78-81%). |
| 4 | 2026-04-04T09:19:01.127913+00:00 | Early checkpoint at gen 4/25 (16%). All runs healthy, all PIDs alive. Diagnose: all CRITICALs/MAJORs are false positives (LiteLLM proxy HTTP 400, config group merge detection). Strategy rejection expected with MAP-Elites. Fitness 79.9-81.0% vs 85.1% baseline. Test eval deferred (not at 50% yet). |
| 4 | 2026-04-04T09:28:50.784297+00:00 | Gen 4/25 (16%). All alive+healthy. Seeds tight: 79.9-81.0%. No frontier improvements since gen 0-1 (0% acceptance across all runs). Treatment rejections slightly higher (36-38 vs 28-32). Normal early plateau. |
| 4 | 2026-04-04T09:48:48.930572+00:00 | Gen 4/25 (16%). R4 improved 79.9%→80.2%. Total programs: R1=59, R2=65, R3=55, R4=60. Archives: R1=15, R2=10, R3=7, R4=5. All healthy. Diagnose: known false positives only. |
| 6 | 2026-04-04T11:28:54.982465+00:00 | Gen 6/25 (24%). All alive. R3 (treatment) now leads at 81.4%, first time treatment surpasses all controls. R1 improved gen 4 (+1.1pp). R4 improved gen 4 (+0.3pp). R2 still plateau. Controls 81.1% vs treatment 80.8% — gap nearly closed (-0.3pp). |
| 8 | 2026-04-04T11:50:12.146389+00:00 | Gen 8/25 (32%). All runs progressing well (gen 4→8 since last formal checkpoint). R3 Treatment leads at 81.4%. Total programs: R1=95, R2=96, R3=89, R4=90. Archives: R1=14, R2=13, R3=9, R4=5. Diagnose: HEALTHY (known false positives only). Test eval deferred (32%, need 50%). |
| 10 | 2026-04-04T13:29:31.521146+00:00 | Gen 10/25 (40%). R4 (treatment) surged +2.9pp at gen 9 to 83.1% — largest single-gen improvement this experiment. Both treatment runs now lead both controls. Treatment mean 82.3% vs control 81.2% (+1.2pp). R2 still at seed (81.0%, 0% acceptance in 128 programs). |
| 10 | 2026-04-04T13:48:37.109326+00:00 | Gen 10/25 (40%). R4 Treatment jumped to 83.1% (+2.9pp since gen 8). Both treatment runs (R3=81.6%, R4=83.1%) outperform both controls (R1=81.3%, R2=81.0%). Treatment mean=82.3% vs Control mean=81.2% — +1.1pp treatment effect emerging. Programs: R1=136, R2=140, R3=131, R4=131. Diagnose: HEALTHY. Test eval at 50% (gen 13, ~19:00 MSK). |
| 14 | 2026-04-04T15:39:44.384611+00:00 | Gen 14/25 (56%). 50% GATE CROSSED — test eval triggered. No fitness changes since gen 10 (R1=81.3%, R2=81.0%, R3=81.6%, R4=83.1%). Treatment still leads: 82.3% vs 81.2% (+1.2pp). All in extended plateau phase. |
| 16 | 2026-04-04T17:29:01.016494+00:00 | Gen 16/25 (64%). Deep plateau continues — no fitness changes since gen 9-10 (7+ gens stagnation). R2 flagged for stagnation (0% in 200 programs). All alive, consistent with analyst forecast. 9 gens remaining. |
| 16 | 2026-04-04T17:49:02.852317+00:00 | Gen 16-18/25 (64-72%). R1 test eval complete: 59.0% ± 1.3%. R2-R4 test eval in progress. Val fitness: R4 Treatment leads at 83.1%, Treatment mean=82.3% vs Control mean=81.2% (+1.1pp). Frontiers stable since gen 10. Archives: R1=20, R2=15, R3=16, R4=7. Diagnose: HEALTHY. Checkpoint-analyst deferred until test eval completes. |
| 20 | 2026-04-04T19:28:49.907018+00:00 | Gen 20/25 (80%). No fitness changes since gen 9-10 (11+ gens stagnation). 5 gens remaining. ~230 valid programs per run. Experiment approaching natural completion. |
| 20 | 2026-04-04T19:48:36.080378+00:00 | Gen 20/25 (80%). Test eval: R1=59.0%±1.3%, R2=59.7%±1.5% (controls complete). R3+R4 treatment test in progress. Control test mean=59.4%. Val frontiers unchanged since gen 10 — deep plateau (10+ gens). R2 seed (gen 2) has 30 children. Archives: R1=21, R2=18, R3=16, R4=9. All alive. Checkpoint-analyst deferred until all test evals complete. |
| 22 | 2026-04-04T21:29:11.105395+00:00 | Gen 22/25 (88%). R1 (control) broke 12-gen plateau at gen 20 (+0.4pp to 81.8%). R4 (treatment) still leads at 83.1%. Updated standings: control 81.4% vs treatment 82.3% (+0.9pp gap, was +1.2pp). 3 gens remaining. |
| 23 | 2026-04-04T21:49:02.016402+00:00 | Gen 22-24/25 (88-96%). R1 broke plateau: 81.3%→82.4% (new best at gen 6 discovered at gen 22). Test eval: R1=59.0%, R2=59.7%, R3=58.9% (controls=59.4%, treatment R3=58.9%). R4 test in progress (~40min remaining). Val: R4 Treatment=83.1% still leads. R2 seed gen-2 champion has 33 offspring. Nearing natural completion. Checkpoint-analyst deferred until R4 test completes. |
| 26 | 2026-04-04T23:28:00.923639+00:00 | NEAR-FINAL: R1/R2/R4 completed (gen 26, DEAD). R3 at gen 24 (ALIVE, completing). R1 had late surge: +0.7pp at gen 22 (81.8->82.4%). Final standings: control 81.7% vs treatment 82.3% (+0.6pp). R4 still best at 83.1%. |

## Baseline

Reference: `hover/7step-dynamic` (mean=85.1, metric=fitness)

## Archives

_(pending)_

