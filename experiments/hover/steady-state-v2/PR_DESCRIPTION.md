# exp: hover/steady-state-v2

**Status**: 🟢 Complete
**Branch**: `exp/hover-steady-state-v2`
**Tracking issue**: #141

## Design

See `experiments/hover/steady-state-v2/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| V1 | 3 | control | standard | 63934 |
| V2 | 4 | control | standard | 63935 |
| V3 | 5 | treatment | standard | 63936 |
| V4 | 6 | treatment | standard | 63937 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 0 | 2026-03-28T02:18:10.767630+00:00 | Initial checkpoint ~1h after launch. All 4 runs alive, evaluating initial programs. No generations completed yet — expected with 300-sample thinking-mode chain eval (~50min/program). |
| 0 | 2026-03-28T03:18:52.218953+00:00 | Relaunch #2 with 8-endpoint LB. V3/V4 relaunched (zsh loop mangled Hydra overrides). All 4 alive, evaluating initial programs. |
| 0 | 2026-03-28T03:33:12.276245+00:00 | Relaunch #3 with 8 separate vLLM endpoints + litellm LB. First program eval ~9min (was 50min). All runs producing fitness. |
| 1 | 2026-03-28T04:18:07.204430+00:00 | Hourly cron checkpoint. All 4 runs healthy. Treatment (V3/V4) leading at ~81% vs control ~78%. 0% invalid for control, 14-25% for treatment. ~22min/program eval. |
| 1 | 2026-03-28T04:20:35.838738+00:00 | Hourly cron. All healthy. Control gen=2 ~78%, treatment gen=0 ~81%. Val ~22min/program. |
| 1 | 2026-03-28T05:17:56.240754+00:00 | Control at gen 3, treatment still epoch 0 but fitness climbing. All healthy, 0% invalid for control, 7-12% for treatment. |
| 2 | 2026-03-28T06:18:00.572110+00:00 | Control gen=4, treatment epoch=1. Treatment leads ~2pp. Invalid rate increasing (10-18%) — dynamic topology producing more complex/invalid chains as evolution progresses. |
| 3 | 2026-03-28T07:18:02.881721+00:00 | Control gen=5 (20%). Treatment epoch=1. Fitness stable — control ~80%, treatment ~81-82%. V4 invalid rate high (28%). |
| 3 | 2026-03-28T08:18:07.210624+00:00 | Post max_in_flight=8 relaunch. V3/V4 restarted from scratch. V1/V2 at gen 6, fitness 81.2%/80.4%. |
| 0 | 2026-03-28T09:20:39.527860+00:00 | First fitness after final relaunch. All healthy, 0% invalid. Treatment eval faster (463s vs 616s control). max_in_flight=8 + HTTP_PROXY stripped. |
| 1 | 2026-03-28T10:18:19.806910+00:00 | ~1h after final relaunch. Treatment 5x mutation rate, 2-3x throughput. Fitness competitive (~80% all runs). Plots updated. |
| 2 | 2026-03-28T10:20:43.456062+00:00 | V3 treatment reached epoch 2 — advancing faster with max_in_flight=8. Fitness competitive across all runs. |
| 3 | 2026-03-28T11:17:54.480225+00:00 | Control gen=5, treatment epoch=2. Fitness converging ~80-81%. Invalid rate: control 46-47%, treatment 25-27% (lower!). |
| 3 | 2026-03-28T12:19:10.957701+00:00 | Control gen=5 (20%), treatment epoch=2 (8%). All runs healthy. Fitness ~80-81% across all. Treatment 2-3x mutation rate, lower invalidity (32-35% vs 52-53%). |
| 3 | 2026-03-28T12:21:20.288794+00:00 | V2 advanced to gen 6. Fitness stable ~80-81%. Treatment still at epoch 2 but evaluating 2x more programs. All healthy. |
| 5 | 2026-03-28T13:18:41.350782+00:00 | V1 82.9%, V2 81.4% — control pulling ahead. Treatment epoch 4, fitness 80-81%. Invalid% dropping across all runs (26-45%). Throughput: treatment still 2x programs evaluated. |
| 5 | 2026-03-28T13:21:09.789550+00:00 | Steady state, no gen changes since last checkpoint. V1 82.9%, V2 81.4%, V3 80.9%, V4 80.2%. Invalid% still dropping (V1 40%, V4 26%). All healthy. |
| 5 | 2026-03-28T14:18:21.725381+00:00 | Treatment catching up: V3 81.6%, V4 81.8% (was 80.9/80.2). Control V1 gen7 82.9%, V2 gen8 81.4%. Invalid% dropping fast (24-35%). All 4 runs converging toward baseline. |
| 5 | 2026-03-28T14:21:00.830522+00:00 | No gen changes. Invalid% still dropping (V4 23%). All runs 81.4-82.9%. Runs mid-evaluation. |
| 6 | 2026-03-28T15:18:18.501436+00:00 | V2 caught V1 at 82.89%. V3 advanced to epoch 6. Treatment V4 81.8% at baseline. Control gen 8-9 (32-36%), treatment epoch 4-6 (16-24%). Invalid% all below 32%. |
| 6 | 2026-03-28T15:20:59.404069+00:00 | No gen changes since last checkpoint. All runs mid-evaluation. Fitness stable: control 82.9%, treatment 81.6-81.8%. |
| 0 | 2026-03-28T16:24:47.140276+00:00 | Clean restart with flushed DBs. All 4 runs evaluating initial programs. No generations completed yet. |
| 1 | 2026-03-28T17:18:26.467476+00:00 | First data from clean restart. V3 treatment leading at 83.3%. Control V1 78.1%, V2 79.6%. V4 78.7%. All healthy, clean DBs. |
| 1 | 2026-03-28T17:21:03.454483+00:00 | No gen changes — all runs mid-evaluation. V3 83.3%, V2 79.6%, V4 78.7%, V1 78.1%. |
| 2 | 2026-03-28T18:18:28.750707+00:00 | V4 jumped to 82.4%. Treatment both above baseline (83.3/82.4%). Control 79-80%. Discard rate ~5% for treatment (down from 31%), 0-29% control. Clean data. |
| 2 | 2026-03-28T18:21:03.308836+00:00 | No gen changes — mid-evaluation. Treatment V3 83.3%, V4 82.4%. Control V2 80.2%, V1 79.2%. |
| 3 | 2026-03-28T19:18:27.795920+00:00 | Control advancing: V1 gen 6, V2 gen 5 (80.4%). Treatment epoch 1, still leading (83.3/82.4%). Invalid% dropping across all runs. |
| 3 | 2026-03-28T19:21:02.818087+00:00 | No changes — mid-evaluation. Treatment 83.3/82.4%, control 79.2/80.4%. |
| 4 | 2026-03-28T20:18:27.813646+00:00 | V1 control jumped to 83.0% — now matching treatment V3 (83.3%). V3/V4 advanced to epoch 3. All runs above or near baseline. Control gen 6-7, treatment epoch 3. |
| 4 | 2026-03-28T20:21:03.206022+00:00 | No changes — mid-evaluation. V1 83.0%, V3 83.3%, V4 82.4%, V2 80.4%. |
| 5 | 2026-03-28T21:18:26.636501+00:00 | V3 treatment new high 85.2%! V1 gen 8, V2 gen 7. Invalid% rising (V1 55%, V2 42%) — evolution producing more complex/risky chains. Treatment invalid also up (V3 21%, V4 31%). |
| 5 | 2026-03-28T21:21:02.572999+00:00 | No gen changes. Invalid% rising: V1 59%, V2 53%, V4 33%, V3 23%. Fitness stable: V3 85.2%, V1 83.0%, V4 82.4%, V2 80.4%. |
| 6 | 2026-03-28T22:18:29.008034+00:00 | V3/V4 epoch 3->5. V1 gen 9, V2 gen 8. Fitness stable. Invalid% high (55-60% control, 31-37% treatment) — evolution exploring aggressive mutations. Treatment still lower invalid. |
| 6 | 2026-03-28T22:21:07.608361+00:00 | No changes — mid-evaluation. V3 85.2%, V1 83.0%, V4 82.4%, V2 80.4%. Invalid% stable at 31-60%. |
| 7 | 2026-03-28T23:18:34.611011+00:00 | V1 gen 10 (40%), V2 gen 9 (36%). Approaching 50% test eval gate. Fitness stable. Invalid% converging across conditions (39-58%). V3 still leading at 85.2%. |
| 7 | 2026-03-28T23:21:04.896918+00:00 | No changes — mid-eval. V1 gen 10 (40%), V2 gen 9 (36%), V3/V4 epoch 5 (20%). Fitness stable. |
| 7 | 2026-03-29T00:18:35.027003+00:00 | V2 control jumped 80.4->82.4%! V1 gen 11 (44%), nearing 50% gate. All runs above baseline now. Invalid% rising across all (48-65%). |
| 7 | 2026-03-29T00:21:02.668815+00:00 | V2 gen 10. All above baseline. V3 85.2%, V1 83.0%, V2/V4 82.4%. Invalid% 48-65%. |
| 8 | 2026-03-29T01:18:28.402882+00:00 | V3 epoch 5->7 (28%). Invalid% rising everywhere (51-68%). Fitness stable. V1 gen 11 (44%) — 2 gens from 50% gate. |
| 8 | 2026-03-29T01:21:09.079932+00:00 | No changes — mid-eval. V1 gen 11, V2 gen 10, V3 epoch 7, V4 epoch 5. Fitness stable. |
| 9 | 2026-03-29T02:18:29.492692+00:00 | V1 gen 12 (48%) — 1 gen from 50% test eval gate! V2 gen 11, V4 epoch 7. All above baseline. |
| 9 | 2026-03-29T02:21:04.373756+00:00 | No changes — mid-eval. V1 gen 12 (48%), 1 gen from gate. Fitness stable. |

## Baseline

Reference: `hover/dynamic-topology` (mean=81.78, metric=soft_fractional_val_coverage)

## Archives

_(pending)_

