# DAG-tab S4 campaign

Persistent raw runs live at:

```text
/home/jovyan/gigaevo/experiments/dag_tab_envelope_s4_20260722/runs/
  no_memory/<dataset>/<model>/<run-set>/
  memory_v2/<dataset>/<model>/<run-set>/
```

`reference/` contains the runs used by `report/report.pdf`: three no-memory
replicas and one Memory V2 replica on California with Gemini 3.5 Flash. New
launcher runs receive a timestamped `<run-set>` automatically.

```bash
./experiments/dag_tab_envelope_s4_20260722/launch_s4_dag_tab.sh 1 1 1
DATASET=california MUTATION_LLM=gemini35_flash \
  ./experiments/dag_tab_envelope_s4_20260722/launch_s4_dag_tab_memory_v2.sh 1 1 1
```

The CV champion's complete stored program is
`runs/memory_v2/california/gemini35_flash/reference/r101/storage/dag_tab/programs/777c20fb-143c-4f3a-ae0a-c41aa77e9bdd.json`.
