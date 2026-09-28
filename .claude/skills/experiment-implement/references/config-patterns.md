# Config Patterns Reference

## Pipeline Selection Rules

| validate.py return type | Pipeline | Examples |
|---|---|---|
| Plain dict `{"fitness": 0.5}` | `pipeline=standard` | `chains/hover/static_soft` |
| Tuple `(metrics_dict, failures_list)` | `pipeline=hover_feedback` or `pipeline=hotpotqa_asi` | `chains/hover/static`, `chains/hotpotqa/static` |
| Prompt evolution (no chain) | `pipeline=prompt_evolution` | `prompt_evolution_hover` |

**Rule**: The pipeline must match what `validate.py` returns. A mismatch causes silent failures — the DAG runner receives unexpected types and either crashes or produces zero fitness.

## prompts_dir Configuration

When using custom prompts, `prompts_dir` must appear in **both** pipeline YAML blocks:

```yaml
# In the pipeline YAML (e.g. config/pipeline/my_pipeline.yaml)
evolution_context:
  prompts_dir: ${prompts.dir}
  # ... other fields

mutation_operator:
  prompts_dir: ${prompts.dir}
  # ... other fields
```

**Why both?** `evolution_context` uses prompts for lineage/insights summaries; `mutation_operator` uses prompts for the actual mutation prompt. If either is missing, that component silently falls back to default prompts — a common source of null experiment results.

## Hydra Config Patterns

### Config group selectors vs leaf overrides

- **Config group selector** (no dot): `pipeline=hover_feedback` — selects `config/pipeline/hover_feedback.yaml`, resolves to `_target_` classes in cfg dump. Cannot be matched literally in config output.
- **Leaf key override** (with dot): `prompt_fetcher.prompt_prefix=X` — sets a specific value, can be matched literally.

### extra_overrides in experiment.yaml

Each `extra_overrides` entry becomes a Hydra CLI override appended to the run command. Common patterns:

```yaml
runs:
  - label: T1
    extra_overrides:
      - "evolution.max_elites=10"
      - "+evolution_context.main_run_sources=[{db: 9, prefix: 'chains/hover/static'}]"
```

**Gotcha**: Overrides with `+` prefix (append syntax) contain complex YAML values (lists, dicts). Never use string matching to verify these — use OmegaConf/Hydra's OverridesParser.

### Config preview (no execution)

```bash
python run.py problem.name=<name> pipeline=<pipeline> [overrides] --cfg job
```

This prints the resolved Hydra config without launching the run. Use it to verify overrides are applied correctly.

## Common Config Mistakes

1. **Wrong pipeline for validate.py return type** — causes silent zero fitness
2. **Missing prompts_dir in one of two blocks** — silently uses default prompts
3. **Stale task_description.txt** — copy-paste from another problem with wrong references
4. **Hydra CWD** — launch.sh must `cd "$PROJ"` before `nohup` commands; Hydra resolves `problem.dir` relative to CWD
5. **LiteLLM proxy** — all experiments use the single proxy at `10.232.30.185:4000`; never hardcode per-server URLs
