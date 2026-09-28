# Launch Preview — heilbron/d-tanh-no-lineage

**Generated:** 2026-04-27T19:04:47.951783+00:00
**Task group:** heilbron  (config/experiment/heilbron.yaml)
**Status:** PASS (54 pin assertion(s), 0 failed)

## Per-Run Resolved Config

### Run A1_G (db=1)

| Path | Task group | shared_overrides | extra_overrides | Resolved | Pinned? | Match |
|------|------------|--------------|-----------------|----------|---------|-------|
| pre_step_hook.drift_cap | — | — | — | 100000 | 100000 | PASS ✓ |
| pre_step_hook.sync_every_n_epochs | — | — | — | 1 | 1 | PASS ✓ |
| inner_iterations | — | 1 | 1 | 1 | 1 | PASS ✓ |
| n_opponents | — | 1 | 1 | 1 | 1 | PASS ✓ |
| source_prompt_k | — | 1 | 1 | 1 | 1 | PASS ✓ |
| num_parents | 1 | — | 1 | 1 | 1 | PASS ✓ |
| max_elites_per_generation | 8 | — | 8 | 8 | 8 | PASS ✓ |
| max_mutations_per_generation | — | — | 8 | 8 | 8 | PASS ✓ |
| mutation_mode | — | — | rewrite | rewrite | rewrite | PASS ✓ |
| max_generations | — | — | 200 | 200 | 200 | PASS ✓ |
| pipeline_builder.lineage_filter.min_shared | — | — | — | 1 | 1 | PASS ✓ |
| pipeline_builder.lineage_filter.inject_shared_evidence | — | — | — | true | true | PASS ✓ |
| pipeline_builder.disable_lineage_on_improver | — | — | — | false | false | PASS ✓ |
| aggregator | — | — | heilbron_constructor | {'_target_': 'gigaevo.programs.metrics.aggregators.ConfigurableAggregator', 'metrics_context': '<ref:metrics_context>', 'outputs': {'is_valid': {'_target_': 'gigaevo.programs.metrics.aggregators.ConstantSpec', 'value': 1.0}, 'n_opponents': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'count'}, 'actual_fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.IntrinsicSpec', 'key': 'actual_fitness'}, 'quality': {'_target_': 'gigaevo.programs.metrics.aggregators.IntrinsicSpec', 'key': 'quality'}, 'resistance': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'resistance_score'}, 'mean_improvement': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'delta'}, 'best_post_improvement': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'max', 'field': 'post_q'}, 'fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.LinearSpec', 'terms': [{'coeff': 0.5, 'source': 'intrinsic', 'key': 'quality'}, {'coeff': 0.5, 'source': 'output', 'key': 'resistance'}]}}, 'invalid_defaults': {'is_valid': 0.0, 'n_opponents': 0.0, 'fitness': -1.0, 'actual_fitness': -1.0, 'quality': -1.0, 'resistance': -1.0, 'mean_improvement': -1.0, 'best_post_improvement': -1.0}} | — | — |
| evolution | — | steady_state | steady_state | — | — | — |
| stopper | — | max_generations | max_generations | {'_target_': 'gigaevo.evolution.engine.stopper.MaxGenerationsStopper', 'max_generations': 200} | — | — |
| opponent_redis_db | — | — | 2 | 2 | — | — |
| opponent_redis_prefix | — | — | heilbron_smooth_v1/pop_b | heilbron_smooth_v1/pop_b | — | — |
| feedback_mode | — | — | composition | composition | — | — |
| population_role | — | — | constructor | constructor | — | — |
| post_step_hook | — | — | ${composition_injection_hook} | {'_target_': 'gigaevo.adversarial.composition_injection.CompositionInjectionHook', 'd_provider': {'_target_': 'gigaevo.adversarial.opponent_provider.RedisOpponentArchiveProvider', 'host': 'localhost', 'port': 6379, 'sources': [{'db': 2, 'prefix': 'heilbron_smooth_v1/pop_b'}], 'island_id': 'fitness_island', 'cache_ttl': 30.0}, 'g_storage': '<ref:redis_storage>', 'dg_tracker': {'_target_': 'gigaevo.adversarial.dg_tracker.DGImprovementTracker', 'host': 'localhost', 'port': 6379, 'db': 1, 'prefix': 'heilbron_smooth_v1/pop_a', 'ttl_seconds': 86400}} | — | — |
| opponent_result_mode | — | — | exec | exec | — | — |
| opponent_sampling_mode | — | — | softmax | softmax | — | — |
| pipeline_builder.archive_reeval | — | — | false | false | — | — |
| pipeline_builder.per_opponent_timeout | — | — | ${stage_timeout} | 900 | — | — |
| problem.name | — | — | heilbron_smooth_v1/pop_a | heilbron_smooth_v1/pop_a | — | — |
| pipeline | — | — | heilbron_smooth_v1 | — | — | — |
| prompts | — | — | default | {'dir': None} | — | — |
| redis.db | — | — | 1 | 1 | — | — |
| stage_timeout | — | — | 900 | 900 | — | — |
| dag_timeout | — | — | 3600 | 3600 | — | — |
| model_name | — | — | Qwen3-235B-A22B-Thinking-2507 | Qwen3-235B-A22B-Thinking-2507 | — | — |
| llm_base_url | — | — | http://10.232.30.185:4000/v1 | http://10.232.30.185:4000/v1 | — | — |

### Run A1_D (db=2)

| Path | Task group | shared_overrides | extra_overrides | Resolved | Pinned? | Match |
|------|------------|--------------|-----------------|----------|---------|-------|
| pre_step_hook.drift_cap | — | — | — | 100000 | 100000 | PASS ✓ |
| pre_step_hook.sync_every_n_epochs | — | — | — | 1 | 1 | PASS ✓ |
| inner_iterations | — | 1 | 1 | 1 | 1 | PASS ✓ |
| n_opponents | — | 1 | 1 | 1 | 1 | PASS ✓ |
| source_prompt_k | — | 1 | 1 | 1 | 1 | PASS ✓ |
| num_parents | 1 | — | 1 | 1 | 1 | PASS ✓ |
| max_elites_per_generation | 8 | — | 8 | 8 | 8 | PASS ✓ |
| max_mutations_per_generation | — | — | 8 | 8 | 8 | PASS ✓ |
| mutation_mode | — | — | rewrite | rewrite | rewrite | PASS ✓ |
| max_generations | — | — | 200 | 200 | 200 | PASS ✓ |
| pipeline_builder.lineage_filter.min_shared | — | — | — | 1 | 1 | PASS ✓ |
| pipeline_builder.lineage_filter.inject_shared_evidence | — | — | — | true | true | PASS ✓ |
| pipeline_builder.disable_lineage_on_improver | — | — | true | true | true | PASS ✓ |
| engine_config.refresh_passes | — | — | 1 | 1 | 1 | PASS ✓ |
| aggregator | — | — | heilbron_improver | {'_target_': 'gigaevo.programs.metrics.aggregators.ConfigurableAggregator', 'metrics_context': '<ref:metrics_context>', 'outputs': {'is_valid': {'_target_': 'gigaevo.programs.metrics.aggregators.ConstantSpec', 'value': 1.0}, 'n_opponents': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'count'}, 'fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'score'}, 'actual_fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'max', 'field': 'post_q'}, 'mean_pre_quality': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'pre_q'}, 'mean_post_quality': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'post_q'}, 'max_post_quality': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'max', 'field': 'post_q'}, 'mean_improvement_raw': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'delta'}}, 'invalid_defaults': {'is_valid': 0.0, 'n_opponents': 0.0, 'fitness': -1.0, 'actual_fitness': -1.0, 'mean_pre_quality': -1.0, 'mean_post_quality': -1.0, 'max_post_quality': -1.0, 'mean_improvement_raw': -1.0}} | — | — |
| evolution | — | steady_state | steady_state | — | — | — |
| stopper | — | max_generations | max_generations | {'_target_': 'gigaevo.evolution.engine.stopper.MaxGenerationsStopper', 'max_generations': 200} | — | — |
| opponent_redis_db | — | — | 1 | 1 | — | — |
| opponent_redis_prefix | — | — | heilbron_smooth_v1/pop_a | heilbron_smooth_v1/pop_a | — | — |
| feedback_mode | — | — | composition | composition | — | — |
| population_role | — | — | improver | improver | — | — |
| opponent_result_mode | — | — | cached | cached | — | — |
| opponent_sampling_mode | — | — | top_k | top_k | — | — |
| pipeline_builder.archive_reeval | — | — | true | true | — | — |
| engine_config.refresh_order | — | — | generation_bucketed | generation_bucketed | — | — |
| problem.name | — | — | heilbron_smooth_v1/pop_b | heilbron_smooth_v1/pop_b | — | — |
| pipeline | — | — | heilbron_smooth_v1 | — | — | — |
| prompts | — | — | default | {'dir': None} | — | — |
| redis.db | — | — | 2 | 2 | — | — |
| stage_timeout | — | — | 900 | 900 | — | — |
| dag_timeout | — | — | 3600 | 3600 | — | — |
| model_name | — | — | Qwen3-235B-A22B-Thinking-2507 | Qwen3-235B-A22B-Thinking-2507 | — | — |
| llm_base_url | — | — | http://10.232.30.185:4000/v1 | http://10.232.30.185:4000/v1 | — | — |

### Run C1_G (db=5)

| Path | Task group | shared_overrides | extra_overrides | Resolved | Pinned? | Match |
|------|------------|--------------|-----------------|----------|---------|-------|
| pre_step_hook.drift_cap | — | — | — | 100000 | 100000 | PASS ✓ |
| pre_step_hook.sync_every_n_epochs | — | — | — | 1 | 1 | PASS ✓ |
| inner_iterations | — | 1 | 1 | 1 | 1 | PASS ✓ |
| n_opponents | — | 1 | 1 | 1 | 1 | PASS ✓ |
| source_prompt_k | — | 1 | 1 | 1 | 1 | PASS ✓ |
| num_parents | 1 | — | 1 | 1 | 1 | PASS ✓ |
| max_elites_per_generation | 8 | — | 8 | 8 | 8 | PASS ✓ |
| max_mutations_per_generation | — | — | 8 | 8 | 8 | PASS ✓ |
| mutation_mode | — | — | rewrite | rewrite | rewrite | PASS ✓ |
| max_generations | — | — | 200 | 200 | 200 | PASS ✓ |
| pipeline_builder.lineage_filter.min_shared | — | — | — | 1 | 1 | PASS ✓ |
| pipeline_builder.lineage_filter.inject_shared_evidence | — | — | — | true | true | PASS ✓ |
| pipeline_builder.disable_lineage_on_improver | — | — | — | false | false | PASS ✓ |
| aggregator | — | — | heilbron_constructor | {'_target_': 'gigaevo.programs.metrics.aggregators.ConfigurableAggregator', 'metrics_context': '<ref:metrics_context>', 'outputs': {'is_valid': {'_target_': 'gigaevo.programs.metrics.aggregators.ConstantSpec', 'value': 1.0}, 'n_opponents': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'count'}, 'actual_fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.IntrinsicSpec', 'key': 'actual_fitness'}, 'quality': {'_target_': 'gigaevo.programs.metrics.aggregators.IntrinsicSpec', 'key': 'quality'}, 'resistance': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'resistance_score'}, 'mean_improvement': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'delta'}, 'best_post_improvement': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'max', 'field': 'post_q'}, 'fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.LinearSpec', 'terms': [{'coeff': 0.5, 'source': 'intrinsic', 'key': 'quality'}, {'coeff': 0.5, 'source': 'output', 'key': 'resistance'}]}}, 'invalid_defaults': {'is_valid': 0.0, 'n_opponents': 0.0, 'fitness': -1.0, 'actual_fitness': -1.0, 'quality': -1.0, 'resistance': -1.0, 'mean_improvement': -1.0, 'best_post_improvement': -1.0}} | — | — |
| evolution | — | steady_state | steady_state | — | — | — |
| stopper | — | max_generations | max_generations | {'_target_': 'gigaevo.evolution.engine.stopper.MaxGenerationsStopper', 'max_generations': 200} | — | — |
| opponent_redis_db | — | — | 6 | 6 | — | — |
| opponent_redis_prefix | — | — | heilbron_smooth_v1/pop_b | heilbron_smooth_v1/pop_b | — | — |
| feedback_mode | — | — | gradient_in_prompt | gradient_in_prompt | — | — |
| population_role | — | — | constructor | constructor | — | — |
| opponent_result_mode | — | — | exec | exec | — | — |
| opponent_sampling_mode | — | — | softmax | softmax | — | — |
| pipeline_builder.archive_reeval | — | — | false | false | — | — |
| pipeline_builder.per_opponent_timeout | — | — | ${stage_timeout} | 900 | — | — |
| problem.name | — | — | heilbron_smooth_v1/pop_a | heilbron_smooth_v1/pop_a | — | — |
| pipeline | — | — | heilbron_smooth_v1 | — | — | — |
| prompts | — | — | default | {'dir': None} | — | — |
| redis.db | — | — | 5 | 5 | — | — |
| stage_timeout | — | — | 900 | 900 | — | — |
| dag_timeout | — | — | 3600 | 3600 | — | — |
| model_name | — | — | Qwen3-235B-A22B-Thinking-2507 | Qwen3-235B-A22B-Thinking-2507 | — | — |
| llm_base_url | — | — | http://10.232.30.185:4000/v1 | http://10.232.30.185:4000/v1 | — | — |

### Run C1_D (db=6)

| Path | Task group | shared_overrides | extra_overrides | Resolved | Pinned? | Match |
|------|------------|--------------|-----------------|----------|---------|-------|
| pre_step_hook.drift_cap | — | — | — | 100000 | 100000 | PASS ✓ |
| pre_step_hook.sync_every_n_epochs | — | — | — | 1 | 1 | PASS ✓ |
| inner_iterations | — | 1 | 1 | 1 | 1 | PASS ✓ |
| n_opponents | — | 1 | 1 | 1 | 1 | PASS ✓ |
| source_prompt_k | — | 1 | 1 | 1 | 1 | PASS ✓ |
| num_parents | 1 | — | 1 | 1 | 1 | PASS ✓ |
| max_elites_per_generation | 8 | — | 8 | 8 | 8 | PASS ✓ |
| max_mutations_per_generation | — | — | 8 | 8 | 8 | PASS ✓ |
| mutation_mode | — | — | rewrite | rewrite | rewrite | PASS ✓ |
| max_generations | — | — | 200 | 200 | 200 | PASS ✓ |
| pipeline_builder.lineage_filter.min_shared | — | — | — | 1 | 1 | PASS ✓ |
| pipeline_builder.lineage_filter.inject_shared_evidence | — | — | — | true | true | PASS ✓ |
| pipeline_builder.disable_lineage_on_improver | — | — | true | true | true | PASS ✓ |
| engine_config.refresh_passes | — | — | 1 | 1 | 1 | PASS ✓ |
| aggregator | — | — | heilbron_improver | {'_target_': 'gigaevo.programs.metrics.aggregators.ConfigurableAggregator', 'metrics_context': '<ref:metrics_context>', 'outputs': {'is_valid': {'_target_': 'gigaevo.programs.metrics.aggregators.ConstantSpec', 'value': 1.0}, 'n_opponents': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'count'}, 'fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'score'}, 'actual_fitness': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'max', 'field': 'post_q'}, 'mean_pre_quality': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'pre_q'}, 'mean_post_quality': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'post_q'}, 'max_post_quality': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'max', 'field': 'post_q'}, 'mean_improvement_raw': {'_target_': 'gigaevo.programs.metrics.aggregators.ReduceSpec', 'op': 'mean', 'field': 'delta'}}, 'invalid_defaults': {'is_valid': 0.0, 'n_opponents': 0.0, 'fitness': -1.0, 'actual_fitness': -1.0, 'mean_pre_quality': -1.0, 'mean_post_quality': -1.0, 'max_post_quality': -1.0, 'mean_improvement_raw': -1.0}} | — | — |
| evolution | — | steady_state | steady_state | — | — | — |
| stopper | — | max_generations | max_generations | {'_target_': 'gigaevo.evolution.engine.stopper.MaxGenerationsStopper', 'max_generations': 200} | — | — |
| opponent_redis_db | — | — | 5 | 5 | — | — |
| opponent_redis_prefix | — | — | heilbron_smooth_v1/pop_a | heilbron_smooth_v1/pop_a | — | — |
| feedback_mode | — | — | gradient_in_prompt | gradient_in_prompt | — | — |
| population_role | — | — | improver | improver | — | — |
| opponent_result_mode | — | — | cached | cached | — | — |
| opponent_sampling_mode | — | — | top_k | top_k | — | — |
| pipeline_builder.archive_reeval | — | — | true | true | — | — |
| engine_config.refresh_order | — | — | generation_bucketed | generation_bucketed | — | — |
| problem.name | — | — | heilbron_smooth_v1/pop_b | heilbron_smooth_v1/pop_b | — | — |
| pipeline | — | — | heilbron_smooth_v1 | — | — | — |
| prompts | — | — | default | {'dir': None} | — | — |
| redis.db | — | — | 6 | 6 | — | — |
| stage_timeout | — | — | 900 | 900 | — | — |
| dag_timeout | — | — | 3600 | 3600 | — | — |
| model_name | — | — | Qwen3-235B-A22B-Thinking-2507 | Qwen3-235B-A22B-Thinking-2507 | — | — |
| llm_base_url | — | — | http://10.232.30.185:4000/v1 | http://10.232.30.185:4000/v1 | — | — |

## Hydra Default Fingerprint

| File | sha256 |
|------|--------|
| config/config.yaml | `33220115e251…` |
| config/constants/base.yaml | `dcdcbd613c56…` |
| config/constants/endpoints.yaml | `e8c260b11ddf…` |
| config/constants/evolution.yaml | `4f266d47c1be…` |
| config/constants/islands.yaml | `8d809cd068aa…` |
| config/constants/llm.yaml | `c6b12ebd4eed…` |
| config/constants/logging.yaml | `b3b17fa01dfd…` |
| config/constants/pipeline.yaml | `d3e9bc753600…` |
| config/constants/redis.yaml | `e45a8e60f854…` |
| config/constants/runner.yaml | `b66a19f97a7e…` |
| config/experiment/base.yaml | `689a580390ca…` |
| config/experiment/full_featured.yaml | `0b6473f5978e…` |
| config/experiment/heilbron.yaml | `d1edb109c0b7…` |
| config/experiment/migration_bus.yaml | `48986e42ecde…` |
| config/experiment/multi_island_complexity.yaml | `df6ae18e32f8…` |
| config/experiment/multi_llm_exploration.yaml | `f40d6f0d23e3…` |
| config/experiment/prompt_coevolution.yaml | `13cf5d107e7f…` |
| config/experiment/steady_state.yaml | `d8b5c87863c7…` |
| config/experiment/steady_state_adversarial.yaml | `7d5d94f7d03c…` |
| config/experiment/steady_state_bus.yaml | `80f1f32da92e…` |
| config/pipeline/heilbron_smooth_v1.yaml | `95d9d84d2947…` |

On re-launch any drift in these digests causes preflight to CRITICAL-fail.

