#!/usr/bin/env python3
"""Experiment tracking auditor for GigaEvo.

Ensures every experiment has a GitHub Issue on the project board,
with correct status column, labels, and PR linkage. Generates INDEX.md
from board state.

Usage:
    PYTHONPATH=. python .claude/skills/project-pm/scripts/pm_audit.py --audit [--fix]
    PYTHONPATH=. python .claude/skills/project-pm/scripts/pm_audit.py --sync hover/prompt_coevolution [--fix]
    PYTHONPATH=. python .claude/skills/project-pm/scripts/pm_audit.py --bootstrap
    PYTHONPATH=. python .claude/skills/project-pm/scripts/pm_audit.py --generate-index

Exit codes: 0 = clean, 1 = issues fixed, 2 = errors
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import yaml  # noqa: I001

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJ = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
)  # .claude/skills/project-pm/scripts -> repo root
EXPERIMENTS_DIR = PROJ / "experiments"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "board_config.yaml"
OWNER = "KhrulkovV"
REPO = f"{OWNER}/gigaevo-core-internal"

STATUS_TO_COLUMN = {
    "preregistered": "Pre-registered",
    "implemented": "Implemented",
    "running": "Running",
    "complete": "Complete",
    "invalid": "Invalid",
}

STATUS_LABELS = {
    "preregistered": "status:preregistered",
    "implemented": "status:implemented",
    "running": "status:running",
    "complete": "status:complete",
    "invalid": "status:invalid",
}

RESULT_LABELS = {
    "positive": "result:positive",
    "null": "result:null",
    "negative": "result:negative",
}

# Pre-manifest experiments (no experiment.yaml) — parsed from INDEX.md
# Maps name -> (pr_number, status, task, key_finding, result_type)
PRE_MANIFEST_DEFAULTS = {
    "hotpotqa/thinking": (
        66,
        "complete",
        "hotpotqa",
        "Established ddce37b4 warm-start seed (val 62.7%) with Qwen3-8B thinking mode.",
        None,
    ),
    "hotpotqa/p1p2": (
        67,
        "complete",
        "hotpotqa",
        "E+G invalid (repr-contamination). F+H valid: ASI pipeline confirmed.",
        None,
    ),
    "hotpotqa/nlp_prompts": (
        69,
        "complete",
        "hotpotqa",
        "NULL — NLP mutation prompts indistinguishable from default.",
        "null",
    ),
    "hotpotqa/val_gap": (
        70,
        "complete",
        "hotpotqa",
        "Gate B NULL. Gate C UNANSWERABLE. Gate E SUGGESTIVE (+4.3pp gap compression).",
        None,
    ),
    "hotpotqa/push": (
        73,
        "complete",
        "hotpotqa",
        "Primary NULL (58.67%). Run D exploratory: 63.00% (first above GEPA).",
        None,
    ),
    "hotpotqa/crossover": (
        74,
        "complete",
        "hotpotqa",
        "All NULL. P replication: 57.33%. Stagnation confirmed in 12 runs.",
        "null",
    ),
    "hotpotqa/cold_start": (
        75,
        "complete",
        "hotpotqa",
        "SUGGESTIVE — cold-start 59.58% vs warm-start 57.11% (p=0.008).",
        None,
    ),
    "hotpotqa/colbert_feedback": (
        76,
        "complete",
        "hotpotqa",
        "NEGATIVE — test EM 57.00% vs BM25 ref 59.58%. Val-test gap overfitting.",
        "negative",
    ),
    "hotpotqa/gemini_mutation": (
        79,
        "complete",
        "hotpotqa",
        "NULL — gemini 59.50% vs cold_start 59.58%. Mutation LLM not binding.",
        "null",
    ),
    "hotpotqa/generalization": (
        81,
        "complete",
        "hotpotqa",
        "NULL — held-out validation does not improve generalization.",
        "null",
    ),
    "hotpotqa/prompt_coevolution": (
        84,
        "complete",
        "hotpotqa",
        "NULL — test EM 60.22% vs 59.58% baseline. Prompt quality not binding.",
        "null",
    ),
    "hover/baseline": (
        90,
        "complete",
        "hover",
        "Established HoVer baseline. Grand mean test coverage 51.65%.",
        None,
    ),
    "hover/feedback_softfit": (
        92,
        "complete",
        "hover",
        "POSITIVE — Cell C mean 54.37% (+2.72pp, p~0.03). GEPA exceeded.",
        "positive",
    ),
}


# ---------------------------------------------------------------------------
# Finding collection (follows diagnose.py pattern)
# ---------------------------------------------------------------------------
@dataclass
class Finding:
    severity: str  # CRITICAL, MAJOR, MINOR, INFO
    check: str
    experiment: str
    detail: str
    action: str = ""

    def __str__(self):
        tag = {"CRITICAL": "!!!", "MAJOR": "!!", "MINOR": "!", "INFO": "."}[
            self.severity
        ]
        action_str = f"\n         Action: {self.action}" if self.action else ""
        return f"  [{tag}] {self.severity}: {self.experiment} — {self.check}\n         {self.detail}{action_str}"


findings: list[Finding] = []
counters: dict[str, int] = {
    "discovered": 0,
    "with_manifest": 0,
    "pre_manifest": 0,
    "issues_ok": 0,
    "issues_created": 0,
    "issues_updated": 0,
    "issues_skipped": 0,
    "board_ok": 0,
    "board_moved": 0,
    "board_added": 0,
    "labels_ok": 0,
    "labels_fixed": 0,
    "errors": 0,
}


def add(severity, check, experiment, detail, action=""):
    findings.append(Finding(severity, check, experiment, detail, action))
    if severity in ("CRITICAL", "MAJOR"):
        counters["errors"] += 1


def ok(check, experiment, detail=""):
    findings.append(Finding("INFO", check, experiment, detail or "OK"))


# ---------------------------------------------------------------------------
# gh CLI helpers
# ---------------------------------------------------------------------------
def gh(*args, check=True, capture=True) -> str:
    """Run a gh CLI command and return stdout."""
    cmd = ["gh"] + list(args)
    env = os.environ.copy()
    # Ensure NO_PROXY includes github
    no_proxy = env.get("NO_PROXY", "")
    if "api.github.com" not in no_proxy:
        env["NO_PROXY"] = f"{no_proxy},api.github.com" if no_proxy else "api.github.com"
        env["no_proxy"] = env["NO_PROXY"]
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        env=env,
        timeout=60,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"gh command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip() if capture else ""


def gh_json(*args) -> list | dict:
    """Run gh command and parse JSON output."""
    out = gh(*args)
    return json.loads(out) if out else {}


# ---------------------------------------------------------------------------
# Board config
# ---------------------------------------------------------------------------
@dataclass
class BoardConfig:
    owner: str = OWNER
    repo: str = REPO
    project_number: int = 0
    project_id: str = ""
    status_field_id: str = ""
    columns: dict[str, str] = field(default_factory=dict)  # column_name -> option_id

    def save(self):
        data = {
            "owner": self.owner,
            "repo": self.repo,
            "project_number": self.project_number,
            "project_id": self.project_id,
            "status_field_id": self.status_field_id,
            "columns": self.columns,
        }
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        print(f"Board config saved to {CONFIG_PATH}")

    @classmethod
    def load(cls) -> BoardConfig:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"No board_config.yaml at {CONFIG_PATH}. Run: /project-pm --bootstrap"
            )
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f)
        cfg = cls()
        cfg.owner = data.get("owner", OWNER)
        cfg.repo = data.get("repo", REPO)
        cfg.project_number = data["project_number"]
        cfg.project_id = data["project_id"]
        cfg.status_field_id = data["status_field_id"]
        cfg.columns = data.get("columns", {})
        return cfg


# ---------------------------------------------------------------------------
# Experiment discovery
# ---------------------------------------------------------------------------
@dataclass
class ExperimentRecord:
    name: str
    task: str
    status: str
    pr_number: int | None = None
    tracking_issue: int | None = None
    branch: str | None = None
    has_manifest: bool = False
    key_finding: str | None = None
    result_type: str | None = None  # positive, null, negative


def discover_experiments() -> list[ExperimentRecord]:
    """Find all experiments from manifests + pre-manifest defaults."""
    records = []

    # 1. Manifest-era experiments
    for yaml_path in sorted(EXPERIMENTS_DIR.glob("*/*/experiment.yaml")):
        if "_template" in str(yaml_path):
            continue
        rel = yaml_path.parent.relative_to(EXPERIMENTS_DIR)
        name = str(rel)
        try:
            sys.path.insert(0, str(PROJ))
            from gigaevo.experiment.manifest import load_manifest

            m = load_manifest(name)
            rec = ExperimentRecord(
                name=name,
                task=m.task,
                status=m.status,
                pr_number=m.pr_number,
                tracking_issue=m.tracking_issue,
                branch=m.branch,
                has_manifest=True,
            )
            records.append(rec)
            counters["with_manifest"] += 1
        except Exception as e:
            add("MINOR", "discovery", name, f"Failed to load manifest: {e}")

    # 2. Pre-manifest experiments
    manifest_names = {r.name for r in records}
    for name, (pr, status, task, finding, result) in PRE_MANIFEST_DEFAULTS.items():
        if name not in manifest_names:
            rec = ExperimentRecord(
                name=name,
                task=task,
                status=status,
                pr_number=pr,
                has_manifest=False,
                key_finding=finding,
                result_type=result,
            )
            records.append(rec)
            counters["pre_manifest"] += 1

    counters["discovered"] = len(records)
    return records


# ---------------------------------------------------------------------------
# Issue management
# ---------------------------------------------------------------------------
def _issue_body(exp: ExperimentRecord) -> str:
    """Generate issue body markdown."""
    status_display = exp.status.replace("_", " ").title()
    pr_link = f"#{exp.pr_number}" if exp.pr_number else "N/A"
    branch_display = f"`{exp.branch}`" if exp.branch else "N/A"
    summary = exp.key_finding or "(see design doc)"

    return f"""## Experiment: {exp.name}

**Status**: {status_display}  |  **PR**: {pr_link}  |  **Branch**: {branch_display}

### Summary
{summary}

### Links
- Manifest: `experiments/{exp.name}/experiment.yaml`

---
_Managed by `/project-pm`. Do not edit manually._"""


def _issue_labels(exp: ExperimentRecord) -> list[str]:
    """Compute expected labels for an experiment."""
    labels = ["experiment", f"task:{exp.task}"]
    status_label = STATUS_LABELS.get(exp.status)
    if status_label:
        labels.append(status_label)
    if exp.result_type:
        result_label = RESULT_LABELS.get(exp.result_type)
        if result_label:
            labels.append(result_label)
    return labels


def find_existing_issue(exp: ExperimentRecord) -> int | None:
    """Search for an existing tracking issue by title pattern."""
    title_pattern = f"exp: {exp.name}"
    try:
        out = gh(
            "issue",
            "list",
            "--repo",
            REPO,
            "--search",
            f'"{title_pattern}" in:title',
            "--state",
            "all",
            "--json",
            "number,title",
            "--limit",
            "5",
        )
        issues = json.loads(out) if out else []
        for issue in issues:
            if issue["title"] == title_pattern:
                return issue["number"]
    except Exception:
        pass
    return None


def create_issue(exp: ExperimentRecord, fix: bool) -> int | None:
    """Create a GitHub issue for an experiment. Returns issue number."""
    if not fix:
        add(
            "MAJOR",
            "issue_missing",
            exp.name,
            "No tracking issue exists",
            "Run with --fix to create",
        )
        return None

    title = f"exp: {exp.name}"
    body = _issue_body(exp)
    labels = ",".join(_issue_labels(exp))

    try:
        out = gh(
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            title,
            "--body",
            body,
            "--label",
            labels,
        )
        # gh issue create prints the issue URL, e.g. https://github.com/OWNER/REPO/issues/123
        match = re.search(r"/issues/(\d+)", out)
        if not match:
            raise RuntimeError(f"Could not parse issue number from: {out}")
        issue_num = int(match.group(1))

        # Close if experiment is complete/invalid (retry once for propagation delay)
        if exp.status in ("complete", "invalid"):
            try:
                gh("issue", "close", str(issue_num), "--repo", REPO)
            except RuntimeError:
                time.sleep(2)
                gh("issue", "close", str(issue_num), "--repo", REPO)

        ok("issue_created", exp.name, f"Created issue #{issue_num}")
        counters["issues_created"] += 1
        return issue_num
    except Exception as e:
        add("CRITICAL", "issue_create_failed", exp.name, str(e))
        return None


def update_issue(exp: ExperimentRecord, issue_num: int, fix: bool):
    """Update issue body, labels, and open/close state if needed."""
    if not fix:
        return

    try:
        # Update body
        body = _issue_body(exp)
        gh("issue", "edit", str(issue_num), "--repo", REPO, "--body", body)

        # Update labels: remove old status/result labels, add current ones
        current_labels_out = gh(
            "issue", "view", str(issue_num), "--repo", REPO, "--json", "labels"
        )
        current_data = json.loads(current_labels_out) if current_labels_out else {}
        current_labels = {lb["name"] for lb in current_data.get("labels", [])}
        expected_labels = set(_issue_labels(exp))

        # Remove stale status/result labels
        for label in current_labels:
            if (
                label.startswith("status:") or label.startswith("result:")
            ) and label not in expected_labels:
                gh(
                    "issue",
                    "edit",
                    str(issue_num),
                    "--repo",
                    REPO,
                    "--remove-label",
                    label,
                    check=False,
                )

        # Add missing labels
        for label in expected_labels:
            if label not in current_labels:
                gh(
                    "issue",
                    "edit",
                    str(issue_num),
                    "--repo",
                    REPO,
                    "--add-label",
                    label,
                    check=False,
                )

        # Open/close state
        if exp.status in ("complete", "invalid"):
            gh("issue", "close", str(issue_num), "--repo", REPO, check=False)
        else:
            gh("issue", "reopen", str(issue_num), "--repo", REPO, check=False)

        counters["issues_updated"] += 1
    except Exception as e:
        add("MAJOR", "issue_update_failed", exp.name, str(e))


# ---------------------------------------------------------------------------
# Board management
# ---------------------------------------------------------------------------
def get_board_items(cfg: BoardConfig) -> dict[str, dict]:
    """Get all items on the board. Returns {issue_url: item_data}."""
    try:
        out = gh(
            "project",
            "item-list",
            str(cfg.project_number),
            "--owner",
            cfg.owner,
            "--format",
            "json",
            "-L",
            "200",
        )
        data = json.loads(out) if out else {}
        items = data.get("items", [])
        result = {}
        for item in items:
            content = item.get("content", {})
            url = content.get("url", "")
            if url:
                result[url] = item
        return result
    except Exception as e:
        add("CRITICAL", "board_query", "all", f"Failed to query board: {e}")
        return {}


def add_to_board(cfg: BoardConfig, issue_num: int, exp: ExperimentRecord, fix: bool):
    """Add an issue to the project board and set its status column."""
    if not fix:
        add(
            "MAJOR",
            "board_missing",
            exp.name,
            f"Issue #{issue_num} not on board",
            "Run with --fix to add",
        )
        return

    try:
        issue_url = f"https://github.com/{REPO}/issues/{issue_num}"
        # Add item
        out = gh(
            "project",
            "item-add",
            str(cfg.project_number),
            "--owner",
            cfg.owner,
            "--url",
            issue_url,
            "--format",
            "json",
        )
        item_data = json.loads(out) if out else {}
        item_id = item_data.get("id")

        if item_id:
            # Set status column
            column_name = STATUS_TO_COLUMN.get(exp.status, "Complete")
            option_id = cfg.columns.get(column_name)
            if option_id:
                gh(
                    "project",
                    "item-edit",
                    "--id",
                    item_id,
                    "--project-id",
                    cfg.project_id,
                    "--field-id",
                    cfg.status_field_id,
                    "--single-select-option-id",
                    option_id,
                )

        ok("board_added", exp.name, f"Added to board in '{column_name}'")
        counters["board_added"] += 1
    except Exception as e:
        add("MAJOR", "board_add_failed", exp.name, str(e))


def move_on_board(
    cfg: BoardConfig,
    item_id: str,
    exp: ExperimentRecord,
    current_column: str,
    fix: bool,
):
    """Move an item to the correct column on the board."""
    target_column = STATUS_TO_COLUMN.get(exp.status, "Complete")
    if current_column == target_column:
        counters["board_ok"] += 1
        return

    if not fix:
        add(
            "MINOR",
            "board_wrong_column",
            exp.name,
            f"On board in '{current_column}', expected '{target_column}'",
            "Run with --fix to move",
        )
        return

    try:
        option_id = cfg.columns.get(target_column)
        if option_id:
            gh(
                "project",
                "item-edit",
                "--id",
                item_id,
                "--project-id",
                cfg.project_id,
                "--field-id",
                cfg.status_field_id,
                "--single-select-option-id",
                option_id,
            )
            ok(
                "board_moved",
                exp.name,
                f"Moved from '{current_column}' to '{target_column}'",
            )
            counters["board_moved"] += 1
    except Exception as e:
        add("MAJOR", "board_move_failed", exp.name, str(e))


# ---------------------------------------------------------------------------
# INDEX.md generation
# ---------------------------------------------------------------------------
STATUS_ICONS = {
    "complete": "✅ Complete",
    "running": "🟡 Running",
    "preregistered": "📋 Designed",
    "implemented": "📋 Designed",
    "invalid": "❌ Invalid",
}

RESULT_ICONS = {
    "positive": "**POSITIVE**",
    "null": "**NULL**",
    "negative": "**NEGATIVE**",
}


TASK_DISPLAY_ORDER = ["hotpotqa", "hover", "adversarial", "toy"]
TASK_TITLES = {
    "hotpotqa": "HotpotQA",
    "hover": "HoVer",
    "adversarial": "Adversarial",
    "toy": "Toy / Validation",
}


def generate_index(experiments: list[ExperimentRecord]):
    """Regenerate experiments/INDEX.md from experiment records, grouped by task."""

    # Sort within each task: running first, then by PR number
    def sort_key(e):
        status_order = {
            "running": 0,
            "implemented": 1,
            "preregistered": 2,
            "complete": 3,
            "invalid": 4,
        }
        return (status_order.get(e.status, 5), e.pr_number or 999)

    experiments.sort(key=sort_key)

    # Group by task
    from collections import defaultdict

    by_task: dict[str, list[ExperimentRecord]] = defaultdict(list)
    for exp in experiments:
        by_task[exp.task].append(exp)

    lines = [
        "# Experiment Index",
        "",
        "One row per experiment, updated by `/project-pm`.",
        "Columns: name, status, key finding, PR link",
        "",
        "**Server inventory**: [`infrastructure.yaml`](infrastructure.yaml)",
        "",
        "---",
    ]

    # Emit sections in display order, then any remaining tasks
    task_order = list(TASK_DISPLAY_ORDER)
    for t in sorted(by_task):
        if t not in task_order:
            task_order.append(t)

    for task in task_order:
        if task not in by_task:
            continue
        title = TASK_TITLES.get(task, task.title())
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Experiment | Status | Key Finding | PR |",
                "|-----------|--------|-------------|-----|",
            ]
        )
        for exp in by_task[task]:
            status = STATUS_ICONS.get(exp.status, exp.status)
            finding = exp.key_finding or "—"
            if len(finding) > 120:
                finding = finding[:117] + "..."
            pr = f"#{exp.pr_number}" if exp.pr_number else "—"
            lines.append(f"| `{exp.name}` | {status} | {finding} | {pr} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Status legend",
            "",
            "| Symbol | Meaning |",
            "|--------|---------|",
            "| 📋 Designed | Phase 1-3 complete; not yet launched |",
            "| 🟡 Running | Runs active |",
            "| ✅ Complete | Phase 5 done; PR merged |",
            "| ❌ Invalid | Invalidated; see PR for details |",
            "",
            "---",
            "",
            "*Auto-generated by `/project-pm`. Do not edit manually.*",
            "",
        ]
    )

    index_path = EXPERIMENTS_DIR / "INDEX.md"
    index_path.write_text("\n".join(lines))
    print(f"INDEX.md regenerated with {len(experiments)} experiments")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def bootstrap():
    """Create the project board, save config, and backfill all experiments."""
    print("=== BOOTSTRAP: Creating GigaEvo Experiments board ===\n")

    # 1. Create project
    print("Creating project board...")
    try:
        out = gh(
            "project",
            "create",
            "--owner",
            OWNER,
            "--title",
            "GigaEvo Experiments",
            "--format",
            "json",
        )
        project_data = json.loads(out) if out else {}
        project_number = project_data.get("number")
        project_id = project_data.get("id")
        if not project_number:
            raise RuntimeError(f"Failed to create project: {out}")
        print(f"  Created project #{project_number} (id={project_id})")
    except RuntimeError as e:
        if "already exists" in str(e).lower():
            # Try to find existing project
            out = gh("project", "list", "--owner", OWNER, "--format", "json")
            projects = json.loads(out) if out else {"projects": []}
            for p in projects.get("projects", []):
                if p.get("title") == "GigaEvo Experiments":
                    project_number = p["number"]
                    project_id = p["id"]
                    print(f"  Using existing project #{project_number}")
                    break
            else:
                raise
        else:
            raise

    # 2. Get field IDs
    print("Querying status field...")
    fields_out = gh(
        "project",
        "field-list",
        str(project_number),
        "--owner",
        OWNER,
        "--format",
        "json",
    )
    fields_data = json.loads(fields_out) if fields_out else {}
    status_field_id = None
    columns = {}

    for f in fields_data.get("fields", []):
        if f.get("name") == "Status":
            status_field_id = f.get("id")
            for opt in f.get("options", []):
                columns[opt["name"]] = opt["id"]
            break

    if not status_field_id:
        print("  WARNING: No 'Status' field found. Board may need manual column setup.")
        print(
            "  Expected columns: Pre-registered, Implemented, Running, Complete, Invalid"
        )

    # 2b. Replace default columns with custom experiment status columns
    CUSTOM_COLUMNS = [
        ("Pre-registered", "GREEN", "Phase 1-3 complete"),
        ("Implemented", "BLUE", "Phase 4 Steps 0-3 done"),
        ("Running", "YELLOW", "Runs active"),
        ("Complete", "GREEN", "Phase 5 done"),
        ("Invalid", "RED", "Invalidated"),
    ]
    if status_field_id and set(columns.keys()) != {c[0] for c in CUSTOM_COLUMNS}:
        print("  Replacing default columns with custom experiment statuses...")
        opts_gql = ", ".join(
            f'{{name: "{name}", color: {color}, description: "{desc}"}}'
            for name, color, desc in CUSTOM_COLUMNS
        )
        query = (
            f"mutation {{ updateProjectV2Field(input: {{"
            f'fieldId: "{status_field_id}", '
            f"singleSelectOptions: [{opts_gql}]"
            f"}}) {{ projectV2Field {{ ... on ProjectV2SingleSelectField {{ options {{ id name }} }} }} }} }}"
        )
        try:
            result = gh("api", "graphql", "-f", f"query={query}")
            result_data = json.loads(result) if result else {}
            new_options = (
                result_data.get("data", {})
                .get("updateProjectV2Field", {})
                .get("projectV2Field", {})
                .get("options", [])
            )
            columns = {opt["name"]: opt["id"] for opt in new_options}
            print(f"  Custom columns created: {list(columns.keys())}")
        except Exception as e:
            print(f"  WARNING: Failed to create custom columns: {e}")

    # 3. Save config
    cfg = BoardConfig(
        owner=OWNER,
        repo=REPO,
        project_number=project_number,
        project_id=project_id,
        status_field_id=status_field_id or "",
        columns=columns,
    )
    cfg.save()

    # 4. Backfill experiments
    print("\nBackfilling experiments...")
    experiments = discover_experiments()
    for exp in experiments:
        print(f"  Processing {exp.name}...")

        # Create issue
        existing = find_existing_issue(exp)
        if existing:
            exp.tracking_issue = existing
            print(f"    Issue #{existing} already exists")
        else:
            issue_num = create_issue(exp, fix=True)
            if issue_num:
                exp.tracking_issue = issue_num
                # Write tracking_issue to manifest if applicable
                if exp.has_manifest:
                    _update_tracking_issue(exp.name, issue_num)

        # Add to board
        if exp.tracking_issue:
            add_to_board(cfg, exp.tracking_issue, exp, fix=True)

    # 5. Generate INDEX.md
    # Re-read key findings from INDEX.md for manifest experiments
    _enrich_findings(experiments)
    generate_index(experiments)

    print("\n=== BOOTSTRAP COMPLETE ===")
    print(f"  Project: #{project_number}")
    print(f"  Experiments: {len(experiments)}")
    print(f"  Issues created: {counters['issues_created']}")
    print(f"  Board items added: {counters['board_added']}")


def _update_tracking_issue(experiment: str, issue_num: int):
    """Write tracking_issue into experiment.yaml."""
    try:
        from gigaevo.experiment.manifest import update_manifest

        update_manifest(
            experiment,
            lambda raw: raw.setdefault("experiment", {}).update(
                {"tracking_issue": issue_num}
            ),
        )
        print(f"    Updated tracking_issue={issue_num} in manifest")
    except Exception as e:
        add(
            "MINOR",
            "manifest_update",
            experiment,
            f"Failed to write tracking_issue: {e}",
        )


def _enrich_findings(experiments: list[ExperimentRecord]):
    """Enrich experiment records with key findings from INDEX.md.

    INDEX.md is the curated source of truth — always prefer its findings
    over PRE_MANIFEST_DEFAULTS or empty values from manifests.
    """
    index_path = EXPERIMENTS_DIR / "INDEX.md"
    if not index_path.exists():
        return

    index_text = index_path.read_text()
    for exp in experiments:
        # Try to extract from INDEX.md table row
        # Format: | `name` | status | key_finding | PR |
        pattern = rf"`{re.escape(exp.name)}`\s*\|[^|]*\|([^|]*)\|"
        match = re.search(pattern, index_text)
        if match:
            curated = match.group(1).strip()
            if curated and curated != "—":
                exp.key_finding = curated
        # Also extract status from INDEX.md for pre-manifest experiments
        # (PRE_MANIFEST_DEFAULTS may have stale statuses)
        if not exp.has_manifest and f"`{exp.name}`" in index_text:
            row = index_text.split(f"`{exp.name}`")[1].split("\n")[0]
            if "❌ Invalid" in row:
                exp.status = "invalid"


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def audit(
    experiments: list[ExperimentRecord],
    cfg: BoardConfig,
    fix: bool,
    all_experiments: list[ExperimentRecord] | None = None,
):
    """Run full audit on experiments. If all_experiments is provided, use it for INDEX.md generation."""
    print(f"=== AUDIT: {len(experiments)} experiments ===\n")

    # Get current board state
    board_items = get_board_items(cfg)

    for exp in experiments:
        # Check 1: Issue exists
        if exp.tracking_issue:
            issue_num = exp.tracking_issue
        else:
            issue_num = find_existing_issue(exp)
            if issue_num:
                exp.tracking_issue = issue_num
                if exp.has_manifest:
                    _update_tracking_issue(exp.name, issue_num)

        if not issue_num:
            issue_num = create_issue(exp, fix)
            if issue_num:
                exp.tracking_issue = issue_num
                if exp.has_manifest:
                    _update_tracking_issue(exp.name, issue_num)
        else:
            # Check labels and body are correct
            update_issue(exp, issue_num, fix)
            counters["issues_ok"] += 1

        # Check 2: On board in correct column
        if issue_num:
            issue_url = f"https://github.com/{REPO}/issues/{issue_num}"
            if issue_url in board_items:
                item = board_items[issue_url]
                item_id = item.get("id")
                # Extract current status from item
                current_status = item.get("status", "")
                move_on_board(cfg, item_id, exp, current_status, fix)
            else:
                add_to_board(cfg, issue_num, exp, fix)

    # Enrich findings and regenerate INDEX.md if fixing
    if fix:
        index_source = all_experiments if all_experiments is not None else experiments
        _enrich_findings(index_source)
        generate_index(index_source)


def sync_one(experiment_name: str, cfg: BoardConfig, fix: bool):
    """Sync tracking for a single experiment."""
    print(f"=== SYNC: {experiment_name} ===\n")

    # Load ALL experiments so generate_index has complete data
    all_experiments = discover_experiments()
    exp = next((e for e in all_experiments if e.name == experiment_name), None)
    if not exp:
        add("CRITICAL", "sync", experiment_name, "Experiment not found")
        return

    # Audit only the target experiment (issues, board)
    audit([exp], cfg, fix, all_experiments=all_experiments)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def report() -> int:
    print(f"\n{'=' * 60}")
    print("  TRACKING AUDIT REPORT")
    print(f"{'=' * 60}\n")

    # Group findings
    for severity in ("CRITICAL", "MAJOR", "MINOR", "INFO"):
        sf = [f for f in findings if f.severity == severity]
        if not sf:
            continue
        print(f"  --- {severity} ---")
        for f in sf:
            print(f)
        print()

    # Summary
    print(f"{'=' * 60}")
    print(
        f"  Experiments: {counters['discovered']} "
        f"(manifest: {counters['with_manifest']}, pre-manifest: {counters['pre_manifest']})"
    )
    print(
        f"  Issues: {counters['issues_ok']} ok, "
        f"{counters['issues_created']} created, "
        f"{counters['issues_updated']} updated"
    )
    print(
        f"  Board: {counters['board_ok']} ok, "
        f"{counters['board_moved']} moved, "
        f"{counters['board_added']} added"
    )
    print(f"  Errors: {counters['errors']}")
    print()
    print("  Every experiment leaves a paper trail. No exceptions.")
    print(f"{'=' * 60}")

    if counters["errors"] > 0:
        return 2
    if (
        counters["issues_created"] > 0
        or counters["board_moved"] > 0
        or counters["board_added"] > 0
    ):
        return 1
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="GigaEvo experiment tracking auditor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit", action="store_true", help="Full audit sweep")
    group.add_argument(
        "--sync",
        metavar="EXPERIMENT",
        help="Sync one experiment (e.g. hover/prompt_coevolution)",
    )
    group.add_argument(
        "--bootstrap",
        action="store_true",
        help="One-time setup: create board, backfill",
    )
    group.add_argument(
        "--generate-index",
        action="store_true",
        help="Regenerate INDEX.md from current state",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix discrepancies (create issues, move cards)",
    )
    args = parser.parse_args()

    if args.bootstrap:
        bootstrap()
        sys.exit(report())

    if args.generate_index:
        experiments = discover_experiments()
        _enrich_findings(experiments)
        generate_index(experiments)
        sys.exit(0)

    # Load board config
    cfg = BoardConfig.load()

    if args.sync:
        sync_one(args.sync, cfg, args.fix)
    else:
        experiments = discover_experiments()
        audit(experiments, cfg, args.fix)

    sys.exit(report())


if __name__ == "__main__":
    main()
