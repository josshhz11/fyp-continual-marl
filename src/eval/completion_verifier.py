"""Independent verification of MA-Gym task completion (Fix 4: ML-003/009/011/015).

MA-Gym marks a task COMPLETED as soon as the worker call returns without
raising, so the engine's completion rate says nothing about whether real work
happened. This module re-scores a finished run from its workflow summary JSON
(the file written by ``OutputWriter.save_workflow_summary``) using cheap,
deterministic checks, without importing or modifying the engine.

Scope and limits: these are heuristics. A task with no flags is "not
contradicted by the checks below", not proven adequate. Placeholder detection
only catches bracketed/marker-style stubs, not a template whose fields were
left blank in prose.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NO_ASSIGNED_AGENT = "no_assigned_agent"
NEVER_STARTED = "never_started"
NO_OUTPUT_RESOURCES = "no_output_resources"
EMPTY_OUTPUT = "empty_output"
SELF_REPORTED_NON_EXECUTION = "self_reported_non_execution"
PLACEHOLDER_CONTENT = "placeholder_content"

ALL_FLAGS = (
    NO_ASSIGNED_AGENT,
    NEVER_STARTED,
    NO_OUTPUT_RESOURCES,
    EMPTY_OUTPUT,
    SELF_REPORTED_NON_EXECUTION,
    PLACEHOLDER_CONTENT,
)

# Phrases a worker writes when it says it did not actually do the work (ML-011).
_NON_EXECUTION = re.compile(
    r"not[_ ]executed|not[_ ]computed|no input resources were provided|no input data",
    re.IGNORECASE,
)

# Template stubs such as "[Date]", "[Seller Legal Name]", "TBD" (ML-003).
_PLACEHOLDER = re.compile(
    r"\[[^\]\n]{0,40}\b(?:insert|your|enter|date|name|company|address|amount|signature|title|tbd|todo|placeholder)\b"
    r"[^\]\n]{0,40}\](?!\()"
    r"|\bTBD\b|lorem ipsum|<insert[^>\n]*>|\{\{[^}\n]*\}\}",
    re.IGNORECASE,
)


@dataclass
class TaskVerdict:
    task_id: str
    name: str
    flags: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return not self.flags


@dataclass
class CompletionReport:
    """Engine-reported vs. independently verified completion for one run."""

    total_nodes: int
    engine_completed: int
    verdicts: list[TaskVerdict]

    @property
    def verified_completed(self) -> int:
        return sum(1 for v in self.verdicts if v.verified)

    @property
    def engine_completion_rate(self) -> float:
        return self.engine_completed / self.total_nodes if self.total_nodes else 0.0

    @property
    def verified_completion_rate(self) -> float:
        return self.verified_completed / self.total_nodes if self.total_nodes else 0.0

    @property
    def flagged_completions(self) -> list[TaskVerdict]:
        return [v for v in self.verdicts if not v.verified]

    @property
    def flag_counts(self) -> dict[str, int]:
        counts = Counter(f for v in self.verdicts for f in v.flags)
        return {flag: counts.get(flag, 0) for flag in ALL_FLAGS}

    def to_metrics(self) -> dict[str, Any]:
        """Fields to log alongside goal_completion_rate (see docs/metrics.md)."""
        return {
            "verified_completion_rate": self.verified_completion_rate,
            "completion_flags": self.flag_counts,
        }


def _leaf_tasks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = summary.get("tasks") or {}
    values = tasks.values() if isinstance(tasks, dict) else tasks
    return [t for t in values if not t.get("subtasks")]


def _verify_task(
    task: dict[str, Any], resources: dict[str, Any], min_content_chars: int
) -> TaskVerdict:
    verdict = TaskVerdict(task_id=str(task.get("id")), name=str(task.get("name", "")))
    flags = verdict.flags

    if not task.get("assigned_agent_id"):
        flags.append(NO_ASSIGNED_AGENT)
    if not task.get("started_at"):
        flags.append(NEVER_STARTED)

    outputs = [
        resources[rid]
        for rid in (str(r) for r in task.get("output_resource_ids") or [])
        if rid in resources
    ]
    if not outputs:
        flags.append(NO_OUTPUT_RESOURCES)
    elif all(len((r.get("content") or "").strip()) < min_content_chars for r in outputs):
        flags.append(EMPTY_OUTPUT)

    text = "\n".join(
        [*(task.get("execution_notes") or [])]
        + [f"{r.get('name', '')}\n{r.get('content') or ''}" for r in outputs]
    )
    if _NON_EXECUTION.search(text):
        flags.append(SELF_REPORTED_NON_EXECUTION)
    if _PLACEHOLDER.search("\n".join(r.get("content") or "" for r in outputs)):
        flags.append(PLACEHOLDER_CONTENT)

    return verdict


def verify_workflow_summary(
    summary: dict[str, Any], *, min_content_chars: int = 20
) -> CompletionReport:
    """Verify every task the engine marked completed.

    Only leaf tasks count: composite parents carry no output of their own, so
    including them would flag every decomposed task. Denominator is all leaf
    tasks, so ``verified_completion_rate <= engine_completion_rate``.
    """
    leaves = _leaf_tasks(summary)
    resources = {str(k): v for k, v in (summary.get("resources") or {}).items()}
    completed = [t for t in leaves if t.get("status") == "completed"]
    verdicts = [_verify_task(t, resources, min_content_chars) for t in completed]
    return CompletionReport(
        total_nodes=len(leaves),
        engine_completed=len(completed),
        verdicts=verdicts,
    )


def verify_workflow_summary_file(path: str | Path, **kwargs: Any) -> CompletionReport:
    with open(path, encoding="utf-8") as f:
        return verify_workflow_summary(json.load(f), **kwargs)


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Verify completion for one MA-Gym run")
    parser.add_argument("summary_json", help="Path to workflow summary JSON from a run")
    args = parser.parse_args(argv)

    report = verify_workflow_summary_file(args.summary_json)
    print(f"leaf tasks:                 {report.total_nodes}")
    print(f"engine completed:           {report.engine_completed} ({report.engine_completion_rate:.1%})")
    print(f"verified completed:         {report.verified_completed} ({report.verified_completion_rate:.1%})")
    print(f"flag counts:                {report.flag_counts}")
    for v in report.flagged_completions:
        print(f"  - {v.name} [{v.task_id}]: {', '.join(v.flags)}")


if __name__ == "__main__":
    main()
