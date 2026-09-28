# exp: hover/steady-state-validation

**Status**: 🟢 Complete
**Branch**: `exp/hover-steady-state-validation`
**Tracking issue**: #139

## Design

See `experiments/hover/steady-state-validation/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| S1 | 6 | control | standard | 2633941 |
| S2 | 7 | control | standard | 2633942 |
| S3 | 8 | treatment | standard | 2730469 |
| S4 | 9 | treatment | standard | 2730470 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 1 | 2026-03-26T19:23:21.892503+00:00 | Checkpoint #1 (~1h after launch). All 4 runs healthy, 0% invalid. S3 treatment leading at 81.1%. Control S1 at 81.3%. Steady-state epoch 0 still completing for treatment runs. |
| 1 | 2026-03-27T00:23:55.775087+00:00 | Launch #5 after PR #135 rebase. All 4 runs alive. Treatment runs approaching epoch 0 refresh — critical test of scoped drain fix. |
| 3 | 2026-03-27T01:24:31.176055+00:00 | Treatment runs survived epoch 0 refresh — scoped drain from PR #135 working. S3 epoch 1, S4 epoch 1. Controls at gen 5. |
| 3 | 2026-03-27T02:23:10.632378+00:00 | All stable. S4 at epoch 2 — multiple epoch refreshes survived. Controls at gen 6. No issues. |
| 5 | 2026-03-27T03:23:20.787659+00:00 | S4 at epoch 3. Controls at gen 7-8 (28-32%). All healthy. S1 leading at 83.4%. |
| 5 | 2026-03-27T04:22:08.133254+00:00 | S4 treatment at 82.4% — now competitive with controls. S2 at gen 9. All healthy, no issues. |
| 6 | 2026-03-27T05:22:25.801849+00:00 | S3 81.8%, S4 82.7% — both treatment runs above baseline (81.78%). S4 epoch 4. All healthy. |
| 7 | 2026-03-27T06:22:32.558926+00:00 | S2 at 84.9% — new high. Controls at gen 10-11 (40-44%). Treatment S4 epoch 5, S3 epoch 3. All healthy. |
| 6 | 2026-03-27T07:28:36.159969+00:00 | Treatment runs S3/S4 restarted with latest main (no drain timeout). S2 at gen 13 (52%) — test eval triggered but deferred until treatment runs have data. Controls continuing normally. |
| 6 | 2026-03-27T08:24:16.076811+00:00 | Treatment runs relaunched again — previous launch had wrong model_name (deepseek instead of Qwen) after rebase on main. Fixed with explicit model_name override. S3/S4 bootstrapping. Issue #11 logged. |
| 7 | 2026-03-27T09:23:52.006043+00:00 | Treatment S3/S4 ~1h in, approaching epoch 0 (4/8 and 3/8 done). Code verified up to date with main. S4 at 80.2%. Controls S1 gen 15, S2 gen 15. All healthy. |
| 8 | 2026-03-27T10:23:54.959226+00:00 | S3 drain completed (1020s, no timeout). S4 draining (1200s+). Controls S1 gen 16, S2 gen 17 (68%). No-timeout drain working as intended — old code would have lost 2 programs per epoch. |
| 9 | 2026-03-27T11:22:50.812437+00:00 | S3/S4 epoch 1 reached — no-timeout drain worked. S3 epoch 0 in 3447s, S4 in 3563s. No programs lost. Controls S1 gen 17 (68%), S2 gen 18 (72%). All healthy. |
| 10 | 2026-03-27T12:23:02.101173+00:00 | S3 epoch 1 done in 2781s (46 min, down from 57 min epoch 0). S2 gen 19 (76%). Controls nearing completion. All healthy. |
| 11 | 2026-03-27T13:22:10.113477+00:00 | Controls at gen 20 (80%). S3 epoch 3 at 79.8% — fitness climbing. All healthy, no issues. |
| 12 | 2026-03-27T14:22:21.514280+00:00 | Controls S1 gen 21 (84%), S2 gen 22 (88%). Treatment S3 epoch 3, S4 epoch 2. All healthy, steady progress. |
| 15 | 2026-03-27T17:24:45.946377+00:00 | Controls S1/S2 complete (gen 25). Treatment S3 epoch 6, S4 epoch 5. All healthy, no issues. Test eval running. |
| 16 | 2026-03-27T19:03:01.363549+00:00 | Controls complete (gen 25). S4 at 81.4% — approaching baseline. Checkpoint analyst: monitor to completion, no intervention needed. Mid-run test eval done (control 61.3%, treatment 59.8% at gen 5-6). |
| 16 | 2026-03-27T19:24:38.664316+00:00 | S4 treatment jumped to 84.1% at gen 7 — now competitive with controls (S1 83.4%, S2 84.9%). S3 still at 79.8%. All healthy. |
| 16 | 2026-03-27T20:24:29.322656+00:00 | S4 treatment holding at 84.1% (gen 8). S3 at 79.8% (gen 9). Treatment runs at 32-36%. All healthy, no issues. |
| 17 | 2026-03-27T21:24:37.812829+00:00 | Treatment at 40-44%. S4 84.1% (gen 10), S3 79.8% (gen 11). S3 fitness flat since gen 6 — may be stuck in local optimum. S4 competitive with controls. All healthy. |
| 18 | 2026-03-27T22:24:45.844904+00:00 | S3 broke plateau — 80.1% (was 79.8% for 5 epochs). S4 holding 84.1% (gen 11). Treatment at 44-48%. All healthy. |
| 18 | 2026-03-27T23:24:32.648509+00:00 | S3 past 50% (gen 13). S4 at gen 11. S3 80.1%, S4 84.1%. Both treatment runs healthy, steady epoch progression. |
| 19 | 2026-03-28T00:24:31.283233+00:00 | Both treatment runs past 50%. S3 gen 14 (56%), S4 gen 13 (52%). Fitness stable: S3 80.1%, S4 84.1%. All healthy. |
| 20 | 2026-03-28T01:24:25.061231+00:00 | S3 climbing: 80.9% at gen 15 (60%) — up from 80.1%. S4 holding 84.1% at gen 13 (52%). Treatment mean now 82.5% vs control 84.2%. All healthy. |
| 20 | 2026-03-28T02:24:21.965198+00:00 | S3 gen 16 (64%), S4 gen 15 (60%). S3 80.9%, S4 84.1%. Treatment mean 82.5% vs control 84.2%. Steady progress, all healthy. |
| 21 | 2026-03-28T03:24:16.746672+00:00 | S3 gen 18 (72%), S4 gen 17 (68%). S3 80.9%, S4 84.1%. Nearing completion — ~5-6h remaining. All healthy. |
| 21 | 2026-03-28T04:24:58.634733+00:00 | S3 81.0% at gen 19 (76%) — still climbing. S4 84.1% at gen 17 (68%). Treatment mean 82.6% vs control 84.2%. Gap: 1.6pp. ~4-5h to completion. |
| 22 | 2026-03-28T05:24:20.869071+00:00 | S3 81.6% at gen 20 (80%) — biggest jump in 10 epochs (+0.6pp). S4 84.1% at gen 19 (76%). Treatment mean 82.8% vs control 84.2% — gap narrowed to 1.4pp. ~3h remaining. |
| 22 | 2026-03-28T06:24:32.307092+00:00 | Final stretch. S3 81.6% gen 21 (84%), S4 84.1% gen 20 (80%). Treatment mean 82.8% vs control 84.2%. ~2h to completion. |
| 23 | 2026-03-28T07:24:34.962044+00:00 | S3 gen 22 (88%), S4 gen 21 (84%). S3 81.6%, S4 84.1%. 3-4 epochs remaining each. Treatment mean 82.8% vs control 84.2%. |
| 23 | 2026-03-28T08:24:33.759658+00:00 | S3 gen 24 — 1 epoch from completion! S4 gen 22 (88%). S3 81.6%, S4 84.1%. S3 should finish within ~1h, S4 in ~3h. |
| 24 | 2026-03-28T09:24:23.896768+00:00 | S3 gen 25 COMPLETE (81.6%). S4 gen 23 (92%, 84.1%). S4 has 2 epochs remaining (~2h). All runs will be done soon — ready for closeout after S4 finishes. |
| 25 | 2026-03-28T10:24:25.994004+00:00 | S3 COMPLETE (gen 26, 81.6%). 3 of 4 runs done. S4 gen 24 — last epoch in progress. Ready for closeout once S4 finishes (~1h). |
| 25 | 2026-03-28T11:23:59.717871+00:00 | ALL 4 RUNS COMPLETE. Final: Control mean 84.2% (S1 83.4%, S2 84.9%), Treatment mean 82.8% (S3 81.6%, S4 84.1%). Gap: 1.4pp. S4 treatment beat S1 control. Ready for /experiment-closeout. |

## Baseline

Reference: `hover/dynamic-topology` (mean=81.78, metric=soft_fractional_val_coverage)

## Archives

_(pending)_
