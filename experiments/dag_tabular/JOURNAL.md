# DAG-tabular experiment journal

Append-only master log for all estimator-controlled FeatureGraph baselines.
Detailed historical journals, reports, raw runs, plans, and frozen winners are
preserved under `artifacts/`.

## 2026-07-16 — `dag_tab` Gemini shakedowns

- Initial 100-mutation Gemini 3 Flash run: seed CV R2 `0.848628` to `0.862303`; held-out RMSE `0.4290` to `0.4082`.
- A dependency-description treatment increased feature composition but did not materially improve fitness; held-out RMSE was `0.4063`.
- Switching MAP-Elites to the two tabular behavior axes produced 28 occupied cells and substantially more composed graphs, again without a clear fitness gain.
- Complete raw runs, reports, and the original journal: `artifacts/campaigns/dag_tab_gemini100_20260716/`.

## 2026-07-21 — PR 306 California shakedown

- Gemini 3 Flash: 76/100 valid, best CV R2 `0.857602`, held-out RMSE `0.415698`.
- Gemini 3.5 Flash with high reasoning: 100/100 valid, best CV R2 `0.862133`, held-out RMSE `0.406858`.
- The kNN capability audit found no neighbor feature in the preceding 200 mutations, while a handwritten supervised kNN graph reached CV R2 `0.865573`; this triggered the capability-envelope refactor.
- Report, investigation, and journal: `artifacts/campaigns/dag_tab_pr306_california_20260721/`.

## 2026-07-22 — capability-envelope S4

- Three no-memory Gemini 3.5 Flash replicas produced 296 completed programs, 288 valid programs, and 66 supervised-neighbor graphs; a neighbor graph won every replica.
- CV champions had held-out RMSE `0.3937`, `0.3988`, and `0.3893`; the best predeclared finalist panel result was `0.3880`.
- The leakage-prior prompt correction removed the dominant own-target-leakage failure in its validation run; best CV R2 was `0.870972` and held-out RMSE `0.391116`.
- Raw runs, launchers, report, and reduced analysis: `artifacts/campaigns/dag_tab_envelope_s4_20260722/`.

## 2026-07-22 — Memory V2 run

- One California/Gemini 3.5 Flash run used Qwen Instruct for Memory V2 and completed 100 mutations.
- CV champion `777c20fb`: CV R2 `0.881017`, fold SD `0.004434`, held-out RMSE `0.376746`.
- Best explicitly card-assisted genome `c1fbe7ff`: held-out RMSE `0.373895`.
- The run produced 52 cards and 94 randomized proposals. There was no global treated-versus-control gain advantage, though cards were more useful on weaker parents.
- Dynamic MAP-Elites cells moved during the run, while Bayesian selection used stable semantic coordinates; all 93 valid terminal measurements carried nonzero evaluator-derived uncertainty.
- No cards retired, so bank growth remains an operational concern.

## 2026-07-22 — TabM-backed feature evolution

- Exploratory 100-mutation run with Gemini 3.5 Flash mutations and Qwen Instruct memory.
- Raw TabM graph RMSE `0.424920`; frozen three-node, 33-feature winner RMSE `0.382592` (`9.96%` reduction).
- This run used revision `5295e008` with FP16 autocast before the merged BF16 hardening, so it remains exploratory.
- Frozen graph, test metrics, comparison, and report: `artifacts/campaigns/dag_tabm_california_g35_qwen_20260722/`.

## 2026-07-22 — archive consolidation

- All available DAG-tabular campaign artifacts were copied into this persistent directory: five campaign directories, six plans, the research report, all available raw runs, reports, journals, and frozen genomes.
- Archive size at creation: approximately 376 MB.

## 2026-07-23 — estimator-baseline campaign launched

- Started one 100-mutation California run each for RealMLP-TD, TabICLv2,
  TabPFN v3, LightGBM 4.6, and XGBoost 2.1 at 02:02 Moscow time.
- All runs use Gemini 3.5 Flash mutation, Qwen Instruct Memory V2,
  `tabular/2d_local_ood`, a ten-node FeatureGraph limit, separate Hydra
  directories, and the production three-fold evaluator.
- CatBoost and TabM were excluded because their California campaigns already
  exist. The new public config form is `experiment=tabular_dag/<model>`.
- The launcher started before the implementation commit, so its immutable
  `commit` field records the launch-time parent `5295e008`. All 70 recorded
  source hashes were verified against implementation commit `1b6c0184`; the
  campaign manifest now records both facts explicitly. No restart was needed.
- Manifest, source hashes, neutral checks, live status, logs, and run outputs:
  `artifacts/campaigns/tabular_baselines_california_g35_qwen_20260723/`.

## 2026-07-23 — estimator-baseline campaign completed

- All five runs completed 100 mutations and exited successfully. Valid yields
  were 91/101 for RealMLP, 98/101 for TabICL, 96/101 for TabPFN, 97/101 for
  LightGBM, and 95/101 for XGBoost, including each neutral seed.
- Every CV-selected champion improved its own evaluator's five-seed held-out
  RMSE over the raw graph: RealMLP 13.31%, TabICL 6.75%, TabPFN 3.92%,
  LightGBM 10.39%, and XGBoost 11.64%.
- TabPFN had the best diagonal held-out result: RMSE `0.363973 ± 0.000636`
  and R² `0.898404 ± 0.000355`.
- Frozen champions, exact per-seed outputs, launch command, and complete tables:
  `findings/california_20260723/`.

## 2026-07-23 — seven-model graph-transfer matrix

- Completed the full seven-graph by seven-evaluator California test matrix
  over estimator seeds 0–4. The artifact contains 49 engineered cells, seven
  raw controls, and 280 seed-level records; 42 missing cells were evaluated
  locally without evolution or LLM calls.
- Every engineered graph improved every evaluator over raw on all five matched
  seeds.
- The CatBoost graph won five rows and ranked top-three in all seven. The
  compact TabPFN graph won LightGBM and XGBoost and had the highest mean
  reduction on foreign evaluators.
- Exact output-name overlap was small (3.1% median pairwise Jaccard), while
  semantic analysis showed convergence on geography, household ratios, and
  spatial target summaries. Graphs differed principally in capacity
  allocation and composition.
- Frozen graphs, all per-seed results, derived CSVs, colored figures, and the
  nine-page TeX/PDF report:
  `findings/california_transfer_20260723/`.

## 2026-07-23 — TabFM California evolution and matrix extension

- Completed a 100-mutation TabFM 1.0 California run with Gemini 3.5 Flash,
  Memory V2, and Qwen Instruct. The CV-selected four-node, seven-feature graph
  improved CV R² from `0.892570` to `0.892727`.
- The frozen graph improved five-seed held-out TabFM RMSE from
  `0.359967 ± 0.000220` to `0.358948 ± 0.000148`.
- Extended the transfer study to eight graphs by eight evaluators. The TabFM
  graph improved all seven older evaluators over raw on every seed, but ranked
  last within every older engineered-graph row. Conversely, all seven older
  graphs worsened TabFM relative to raw on every seed.
- The complete artifact now contains 64 engineered cells, eight raw controls,
  and 360 seed-level test records:
  `findings/california_transfer_20260723/`.

## 2026-07-23 — Higgs-small CatBoost/TabM transfer matrix

- Froze the CV-selected winners from the two 100-mutation Memory V2 Higgs
  campaigns and evaluated raw, CatBoost-evolved, and TabM-evolved inputs with
  both estimators over seeds 0–4 (30 fresh test fits).
- The TabM graph won both rows. It raised CatBoost test accuracy from
  `0.727282 ± 0.000831` to `0.740102 ± 0.000714`, and paper-tuned Higgs
  TabM-mini accuracy from `0.737695 ± 0.001130` to
  `0.748710 ± 0.001611`.
- The graph names have zero literal output overlap, but code and Spearman
  analysis recover four shared mechanisms. TabM additionally builds a distinct
  longitudinal-centrality and momentum-closure block that transfers strongly
  to CatBoost.
- Exact graphs, all seed-level records, derived tables, colored figures, and
  the six-page TeX/PDF report:
  `findings/higgs_transfer_20260723/`.
