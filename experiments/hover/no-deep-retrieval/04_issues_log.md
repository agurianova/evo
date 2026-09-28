# Issues Log — hover/no-deep-retrieval

## Summary

Implementation completed with following fixes and notes:

### Fixed Issues

1. **Critical: Import path bugs in static_soft_no_deep** (FIXED)
   - `validate.py` and `test.py` were importing from `static_soft.config` instead of `static_soft_no_deep.config`
   - This would have loaded the wrong STATIC_CHAIN_TOPOLOGY and baseline
   - Fixed both imports to point to `static_soft_no_deep.config`

2. **Task description stale reference** (FIXED)
   - `static_soft_no_deep/task_description.txt` still mentioned "retrieve & retrieve deep"
   - Fixed to only reference "retrieve" tool (k=7)

3. **Ruff linter exclude for stale worktrees** (FIXED)
   - `.claude/worktrees/test-quality-sprint/` had old vartodd files failing lint
   - Added `exclude = [".claude/worktrees", "experiments/*/top_programs_*"]` to pyproject.toml

### Implementation Details

1. **Tool Registry Enforcement**
   - Treatment runs (R1, R3): only `{"retrieve": k=7}` in tool_registry
   - Control runs (R2, R4): both `{"retrieve": k=7, "retrieve_deep": k=10}`
   - No silent fallback modes — hard ValueError on unknown tool

2. **3D MAP-Elites for Dynamic Runs**
   - Created new `topology_3d_ret.yaml` using `n_retrievals` instead of `n_deep_retrieval`
   - Reason: n_deep_retrieval always 0 in treatment → collapsed to 1 bin
   - n_retrievals counts all retrieval steps → preserves 3D space for both treatment and control
   - Added `n_retrievals` feature to ChainFeatureExtractor and ChainStructuralMetricsStage

3. **LPT_Chain Scheduling for Dynamic Runs**
   - Changed from `scheduling=lpt` to `scheduling=lpt_chain`
   - Reason: chain-specific feature extraction and prediction is more efficient than generic code-level features

4. **LiteLLM Proxy Integration**
   - All runs use single proxy at `10.232.30.185:4000`
   - No per-server chain/mutation URLs

### N=1 Per Condition Note

Manifest has 4 runs (N=1 per condition) instead of designed 8 runs (N=2 per condition).
Treatment verification confirmed this is a compute resource constraint, not an implementation gap.

### Test Results

- All 152 integration tests pass
- Linting clean
- Treatment verification: PASS — no silent fallback modes
