# S4 capability-envelope report

`report.pdf` is the deliverable. Figures are **not** committed (the repo ignores `*.png`)
— they are regenerated from the committed `viz/*.json` by the scripts here, so the PDF is
reproducible without the raw run directories.

## Rebuild the figures and the PDF

From this directory, with the project environment active:

```bash
python make_figures.py          r101:"replica 101" r202:"replica 202" r303:"replica 303"
python make_neighbour_figure.py r101:"replica 101" r202:"replica 202" r303:"replica 303"
python make_test_panel_figure.py r101:"replica 101" r202:"replica 202" r303:"replica 303"
for arm in r101 r202 r303; do python make_lineage_viz.py "$arm"; done
python make_invalid_table.py    r101:"replica 101" r202:"replica 202" r303:"replica 303"
python make_numbers.py          r101:rA r202:rB r303:rC
python make_memory_report_assets.py mem_r101 r101 r202 r303
tectonic report.tex
```

`make_numbers.py` emits every number the prose quotes as a LaTeX macro, so the report
cannot drift from the data. `make_invalid_table.py` emits `invalid_table.tex`.

## Regenerate `viz/` from raw run directories

Only needed if the runs are re-executed. `$RUN` is a replica's Hydra run dir (the launcher
writes `dag_tab_s4/r101` etc.), and the scripts must be run from a checkout that can import
`problems.dag_tab` with `GIGAEVO_TABULAR_DATA` set.

```bash
python build_run_stats.py             $RUN r101
python classify_invalid.py            $RUN r101 .
python extract_lineage.py             $RUN r101
python analyze_neighbour_features.py  $RUN r101
python score_finalists.py             $RUN r101 . 10
```

For a Memory V2 run, use the same reducers plus the causal-ledger reducer:

```bash
python build_run_stats.py        $MEM_RUN mem_r101
python build_memory_analysis.py  $MEM_RUN mem_r101
python extract_lineage.py        $MEM_RUN mem_r101
python score_finalists.py        $MEM_RUN mem_r101 . 1
```

`analyze_neighbour_features.py --selftest` runs the classifier's four controls — two of
them check that a variable merely *named* `knn`, and an `argsort` with no distance, are
**not** counted as neighbour features.

`pre_g3f_neighbour.json` / `pre_g35_neighbour.json` are the two pre-refactor shakedown runs
classified by the same detector, which is what makes the "0 neighbour features in 200
children" baseline a measurement rather than a recollection.
