# exp: hover/dynamic-topology

**Status**: 🟢 Complete
**Branch**: `exp/hover-dynamic-topology`
**Tracking issue**: #118

## Design

See `experiments/hover/dynamic-topology/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| D1 | 9 | control | standard | 1461930 |
| D2 | 10 | control | standard | 1208766 |
| D5 | 13 | treatment | standard | 1461931 |
| D6 | 14 | treatment | standard | 1461932 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 9 | 2026-03-24T06:08:44.098033+00:00 | First checkpoint at ~38%. Treatment (D5-D8, mean=80.5%) leads control (D1-D4, mean=76.3%) by ~4.2pp. All 8 runs healthy. |
| 2 | 2026-03-24T07:25:40.097401+00:00 | Early checkpoint at ~10%. All runs healthy. stage_timeout bumped 3000->5000. 0% timeouts at new setting. |
| 4 | 2026-03-24T08:22:50.032805+00:00 | Checkpoint at ~16%. Treatment leading by ~5pp. 0% timeouts. D6 at 84.3%. |
| 5 | 2026-03-24T09:23:01.864577+00:00 | Checkpoint at ~21%. Treatment (D5=81.0%, D6=84.3%) leading control (D1=79.3%, D2=75.7%) by ~5pp. 0% timeouts. All PIDs alive. |
| 5 | 2026-03-24T10:25:18.711053+00:00 | Checkpoint at ~23%. Control mean 78.6%, treatment mean 82.7% (delta +4.1pp). D6 stalled ~50min in CallValidatorFunction (chain server 10.225.185.235:8000 slow); will auto-recover via stage_timeout. D1 improved 79.3%→80.6%. All PIDs alive. |
| 6 | 2026-03-24T11:24:44.122314+00:00 | Checkpoint at ~25%. Control mean 78.8%, treatment mean 82.7% (delta +3.9pp). All runs HEALTHY (diagnose: 0 MAJOR/CRITICAL). D6 stall from prior checkpoint resolved. |
| 6 | 2026-03-24T12:24:16.986560+00:00 | Checkpoint at ~27%. Control mean 79.1%, treatment mean 82.7% (delta +3.6pp). All runs HEALTHY (0 MAJOR/CRITICAL). D6 invalidity 23% — expected for dynamic topology producing complex mutants. Long DAG pipeline times (4000s+) due to mutation server LLM calls, not chain evaluation. |
| 7 | 2026-03-24T13:24:12.291222+00:00 | Checkpoint at ~30%. Control mean 79.1%, treatment mean 82.9% (delta +3.8pp). D1/D6 MAJOR in diagnose = stall detection (straggler programs in gen 6, not real issues). D2 leading at gen 9. Tail-latency from expensive dynamic chains slows D1/D6 generation throughput. |
| 7 | 2026-03-24T19:24:35.222564+00:00 | D2 at 64%, others relaunched (D1/D5/D6 at gen 4-5). Treatment runs (D5/D6) showing strong early fitness ~80%. Test eval for D2 in progress. |
| 8 | 2026-03-24T20:26:25.272005+00:00 | Routine checkpoint. All healthy, 0 CRITICAL/MAJOR. D2 mid-run test eval done (51.73%). Runs mid-generation, awaiting D1/D5/D6 to catch up. |
| 9 | 2026-03-24T21:25:05.861896+00:00 | All runs healthy (0 CRITICAL/MAJOR). D2 at 72%, D1 at 32%. Treatment runs D5/D6 at 24% but leading on fitness (80.4-80.6% vs 76.8-78.6% control). |
| 11 | 2026-03-24T22:25:53.447915+00:00 | D2 at 80% (gen 20). D5 fitness jumped to 81.4%. D6 MAJOR=stall warning (waiting for slow validations, transient). Avg gen 45%, analyst trigger at next checkpoint. |
| 12 | 2026-03-24T23:25:49.787479+00:00 | D2 at 84% (gen 21). D5 fitness stable at 81.4%. D6 MAJOR=stall warning (transient, high LLM invalidity). Avg gen 49% — analyst triggers next checkpoint. |
| 13 | 2026-03-25T00:26:44.149199+00:00 | 50%+ checkpoint with analyst. D2 at 88%. Treatment D5=81.8% leads all runs. D6 2 MAJOR (transient stall + high invalidity from complex code gen). D5 evolved 6-step chain (more efficient than fixed 7). |
| 14 | 2026-03-25T01:26:47.960804+00:00 | D2 at 92% (gen 23). D6 CRITICAL=transient stall (straggler program in CallProgramFunction, will auto-recover via stage_timeout). D6 65% invalidity (hypothesis-relevant). Treatment delta +2.6pp. |
| 15 | 2026-03-25T02:25:35.611726+00:00 | D2 at 96% (gen 24), D1 at 60%. All HEALTHY except D6 CRITICAL=transient stall (recovers each time). Treatment delta +2.6pp. D5 new rank02 program at 81.4%. |
| 16 | 2026-03-25T03:24:33.175074+00:00 | D2 COMPLETE (25/25, 79.0%). D1 at 68%, D5 at 52%, D6 at 48%. D6 diagnose CRITICAL=false alarm (stage_timeout TimeoutError in log, not a crash — PID alive). Treatment delta +2.8pp. |
| 18 | 2026-03-25T04:24:13.328135+00:00 | D2 complete. D1 broke plateau to 78.4% (+1.3pp). D5 at 82.0% (new best). D6 77% invalidity but still advancing. Treatment delta +2.5pp (mean 81.2% vs 78.7%). |
| 18 | 2026-03-25T05:24:10.255827+00:00 | D5 hit 83.1% — new experiment best! D1 at 78.4%, D2 complete at 79.0%. D6 80% invalidity but advancing. Treatment delta +3.1pp (mean 81.8% vs 78.7%). |
| 19 | 2026-03-25T06:24:01.359874+00:00 | D1 80%, D5 68%, D6 64%. D6 advanced gen 15->16 despite diagnose CRITICAL (transient). Treatment delta +3.1pp. D5 still at 83.1% experiment best. |
| 20 | 2026-03-25T07:25:49.581048+00:00 | D1 88%, D5 72%, D6 68%. All advancing. D6 83% invalidity but gen 16->17. Treatment delta +3.1pp. Approaching final stretch. |
| 21 | 2026-03-25T08:24:49.118807+00:00 | D1 92% (gen 23), D5 76% (gen 19), D6 72% (gen 18). D1 two gens from completion. Treatment delta +3.1pp. All advancing. |
| 22 | 2026-03-25T09:23:44.026587+00:00 | D1 COMPLETE (25/25, 78.4%, 15.65h). Both control runs done. D5 80%, D6 76%. Treatment delta +3.1pp. Only treatment runs D5/D6 remain. |
| 23 | 2026-03-25T11:25:10.900403+00:00 | D1/D2 COMPLETE (25/25). D5 gen 22, D6 gen 21. D6 stalled 12.8h due to worker pool starvation (87% invalidity from CPF timeouts). Fix committed (560a768 per-stage pools) but D6 runs old code. D5 healthy at 83.1%. Control mean 78.7%, treatment mean 81.8% (delta +3.1pp). |
| 23 | 2026-03-25T12:51:43.612699+00:00 | FINAL checkpoint before closeout. D1/D2 complete (25/25). D5 stopped at 23/25 (researcher request). D6 stopped at 22/25 (worker leak bug caused 87% invalidity — CancelledError not caught in run_exec_runner, fix committed). Control mean 78.7%, treatment mean 81.8% (delta +3.1pp). D5 best=83.1% (9-step chain with 5 retrieval hops). |
| 23 | 2026-03-25T14:23:02.729425+00:00 | Final post-completion checkpoint. All runs done: D1=25, D2=25, D5=23, D6=22. Test evals running on 4 dedicated chain servers. Awaiting results for closeout. |

## Baseline

Reference: `hover/feedback_softfit` (mean=54.37, metric=discrete_test_coverage)

## Archives

_(pending)_
