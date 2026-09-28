# Literature Brief: Heilbronn Baseline Replication

## Prior Work

Two GigaEvo adversarial co-evolution experiments have been completed on the Heilbronn triangle problem. The heilbron-prover experiment (PR #183) introduced adversarial co-evolution with GAN and soft-fitness update mechanisms, establishing a Constructor baseline of mean actual_fitness = 0.03464 from N=2 pairs. A follow-up experiment, adversarial-dynamic-updates (PR #197), tested per-program fingerprint archive re-evaluation with 4 treatment and 4 control runs. That experiment found all cells -- including controls with no dynamic re-evaluation -- scoring below the 0.03464 baseline, raising the question of whether the original measurement was an outlier.

## Replication Rationale

The baseline claim of 0.03464 rests on N=2 independent pairs, which is underpowered for reliable estimation. With only two data points, the sample mean is highly sensitive to run-level variance (seed effects, stochastic LLM outputs, archive initialization). Before designing further mechanism experiments that compare against this baseline, we need to confirm it is stable. This replication uses N=4 pairs (doubling the sample size) under identical conditions to establish statistical reliability.

## Recommendation

Exact replication: no mechanism changes, no hyperparameter adjustments. Use the same problem configuration, pipeline, LLM endpoints, and generation budget as heilbron-prover (PR #183). The only change is increased sample size (N=4 vs N=2). The novel contribution is the baseline estimate itself -- a reproducible reference point for all future Heilbronn adversarial experiments.
