# Pre-existing test failures on `main` (as of 2026-04-19)

Captured during `lib/issues-cleanup-2026-04` branch prep — these 25 failures exist on
`main` before any cleanup commits land. They are **pre-existing**, not regressions
from C1–C10. Each is mapped to the cleanup commit that will fix it (or to a new
fix if not covered).

## Failure groups

### Group A — `RunSpec.pinned` missing (9 failures) → fixed by C6

```
tests/experiment/test_checks_resolved_config.py::
  TestResolvedConfigMatchesPinned::test_pin_matches_pass
  TestResolvedConfigMatchesPinned::test_pin_mismatch_fails_critical
  TestResolvedConfigMatchesPinned::test_per_run_pin_overrides_contract
  TestResolvedConfigMatchesPinned::test_pin_absent_from_resolved_fails
  TestResolvedConfigMatchesPinned::test_dry_run_failure_surfaces_as_critical
  TestResolvedConfigMatchesPinned::test_empty_pinned_passes_advisory
  TestConfigFingerprintStable::test_fresh_launch_no_fingerprint_recorded_passes
  TestConfigFingerprintStable::test_relaunch_matching_fingerprint_passes
  TestConfigFingerprintStable::test_relaunch_drifted_fingerprint_fails_critical
```

**Root cause**: `RunSpec` Pydantic model (in `gigaevo/experiment/manifest.py`) lacks
`pinned: dict[str, Any] | None`. `gigaevo/experiment/checks.py:370` accesses
`run.pinned` and raises `AttributeError`.

**Issues**: I-01 / I-09 / I-11 (04_issues_log.md).

**Fix**: C6 adds `pinned` field to `RunSpec` and wires it through.

---

### Group B — Launch preview tests (9 failures) → investigate under C6 or new C11

```
tests/experiment/test_launch_preview.py::
  TestWriteLaunchPreview::test_creates_file_at_expected_path
  TestWriteLaunchPreview::test_header_names_task_group
  TestWriteLaunchPreview::test_reports_pass_when_all_pins_satisfied
  TestWriteLaunchPreview::test_reports_fail_with_drift
  TestWriteLaunchPreview::test_per_run_table_shows_pin_rows
  TestWriteLaunchPreview::test_provenance_reflects_extra_overrides
  TestWriteLaunchPreview::test_provenance_reflects_config_extra
  TestWriteLaunchPreview::test_fingerprint_table_includes_all_files
  TestWriteLaunchPreview::test_is_idempotent_and_overwrites
```

**Likely root cause**: Same `RunSpec.pinned` issue — `launch_preview.py` iterates
over runs and reads `run.pinned`. Verify after C6 merges; residual failures become
their own commit.

---

### Group C — `test_result_records_cli_args_per_run` (1 failure) → investigate

```
tests/experiment/test_dry_run.py::TestDryRunResult::test_result_records_cli_args_per_run
```

**Unknown root cause** — may be `extra` vs `extras` collision (I-00, fixed by C7)
or an unrelated dry-run issue. Triage after C7 merges.

---

### Group D — `redesign-sandbox` yaml pydantic mismatch (6 failures) → new fix needed

```
tests/experiment/test_manifest_omegaconf_loader.py::
  TestAllV2YamlsLoad::test_every_real_yaml_loads[experiments/heilbron/redesign-sandbox/experiment.yaml]
tests/experiment/test_manifest_v2_groups.py::
  TestWatchdogFencePlotCommands::test_plot_commands_preserved[experiments/heilbron/redesign-sandbox/experiment.yaml]
  TestWatchdogFencePlotCommands::test_alert_thresholds_preserved[experiments/heilbron/redesign-sandbox/experiment.yaml]
  TestWatchdogFencePlotCommands::test_checkpoint_milestones_preserved[experiments/heilbron/redesign-sandbox/experiment.yaml]
  TestEveryYamlValidates::test_every_real_yaml_validates[experiments/heilbron/redesign-sandbox/experiment.yaml]
tests/experiment/test_manifest_v2_models.py::
  TestExistingYamlsStillLoad::test_existing_yaml_loads[experiments/heilbron/redesign-sandbox/experiment.yaml]
```

**Root cause**: `experiments/heilbron/redesign-sandbox/experiment.yaml` has
`lifecycle.treatment_verification.note: null`, but the pydantic model requires
`note: str` (non-optional). Either:

- (a) Make `note` field optional: `note: str | None = None` in
  `gigaevo/monitoring/manifest_schema.py` (or wherever `TreatmentVerification`
  lives), OR
- (b) Fix the yaml: `note: ""` or remove the `note` key entirely from
  redesign-sandbox/experiment.yaml.

**Recommendation**: (a) — optional string is safer; many experiments may want to
omit the note.

**Not covered by C1–C10**: Add a C11 "fix treatment_verification.note schema" or
fold into C7 cleanup.

---

## Action items

- [ ] C6 fixes Group A (9 tests) — planned
- [ ] Re-run tests after C6 merges to check Group B (expected to clear too)
- [ ] Re-run tests after C7 merges to check Group C (extras/extra collision)
- [ ] Add C11 to cleanup plan: `note: str | None = None` in `TreatmentVerification`
      model → clears Group D (6 tests)

Total: **25 pre-existing failures → expected 0 after C6+C7+C11**.
