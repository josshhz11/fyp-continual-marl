"""Independent verification of MA-Gym task completion (Fix 4: ML-003/009/011/015).

MA-Gym marks a task COMPLETED as soon as the worker call returns without
raising, so the engine's completion rate says nothing about whether real work
happened. This module re-scores a finished run from its workflow summary JSON
(the file written by ``OutputWriter.save_workflow_summary``) using cheap,
deterministic checks, without importing or modifying the engine.

Scope and limits: these are heuristics. A task with no flags is "not
contradicted by the checks below", not proven adequate. Placeholder detection
only catches bracketed/marker-style stubs; a template whose fields were left
blank in prose is caught only when the resource is *named* a template.
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
BLANK_FIELDS = "blank_fields"
TEMPLATE_RESOURCE = "template_resource"

# Hard flags: objective defects. A task with any of these is not verified.
ALL_FLAGS = (
    NO_ASSIGNED_AGENT,
    NEVER_STARTED,
    NO_OUTPUT_RESOURCES,
    EMPTY_OUTPUT,
    SELF_REPORTED_NON_EXECUTION,
    PLACEHOLDER_CONTENT,
    BLANK_FIELDS,
)

# Review flags: worth a human look, but do not affect the verified rate.
REVIEW_FLAGS = (TEMPLATE_RESOURCE,)

# Phrases a worker writes when it says it did not actually do the work (ML-011).
_NON_EXECUTION = re.compile(
    r"not[_ ]executed|not[_ ]computed|no input resources were provided|no input data",
    re.IGNORECASE,
)

# Template stubs such as "[Date]", "[Seller Legal Name]", "TBD" (ML-003).
_PLACEHOLDER = re.compile(
    r"\[[^\]\n]{0,40}\b(?:insert|your|enter|date|name|company|address|amount|signature|title|tbd|todo|placeholder)\b"
    r"[^\]\n]{0,40}\](?!\()"
    r"|\bTBD\b|lorem ipsum|<insert[^>\n]*>|\{\{[^}\n]*\}\}"
    # dummy names and "fill this in" wording seen in real output
    r"|\bJohn Doe\b|\bJane (?:Doe|Smith)\b|(?-i:\bExample[A-Z0-9]\w*)"
    r"|should be (?:tailored|populated|customi[sz]ed)|to be (?:filled|completed|populated)",
    re.IGNORECASE,
)

# A bullet whose label has no value, e.g. "- Version:". Blank only when the
# next line is not a deeper-indented child (which would make it a list intro).
_BLANK_LABEL = re.compile(r"^(\s*)[-*]\s+[A-Za-z][^:\n]{0,60}:\s*$")
_MIN_BLANK_FIELDS = 2


def _count_blank_fields(text: str) -> int:
    lines = text.split("\n")
    blanks = 0
    for i, line in enumerate(lines):
        m = _BLANK_LABEL.match(line)
        if not m:
            continue
        nxt = next((x for x in lines[i + 1 :] if x.strip()), "")
        if len(nxt) - len(nxt.lstrip()) <= len(m.group(1)):
            blanks += 1
        # a deeper-indented next line means this label introduces a list
    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if any(cells) and not all(set(c) <= set("-: ") for c in cells) and "" in cells:
                blanks += 1
    return blanks

# A deliverable titled "... Template" is often a blank form rather than finished
# work (observed on real ICAAP output), but a task may legitimately ask for one,
# so this is a review flag only.
_TEMPLATE_NAME = re.compile(r"\btemplates?\b", re.IGNORECASE)


@dataclass
class TaskVerdict:
    task_id: str
    name: str
    flags: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)

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

    @property
    def review_flag_counts(self) -> dict[str, int]:
        counts = Counter(f for v in self.verdicts for f in v.review_flags)
        return {flag: counts.get(flag, 0) for flag in REVIEW_FLAGS}

    def to_metrics(self) -> dict[str, Any]:
        """Fields to log alongside goal_completion_rate (see docs/metrics.md)."""
        return {
            "verified_completion_rate": self.verified_completion_rate,
            "completion_flags": self.flag_counts,
            "completion_review_flags": self.review_flag_counts,
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
    body = "\n".join(r.get("content") or "" for r in outputs)
    if _count_blank_fields(body) >= _MIN_BLANK_FIELDS:
        flags.append(BLANK_FIELDS)
    if any(_TEMPLATE_NAME.search(r.get("name") or "") for r in outputs):
        verdict.review_flags.append(TEMPLATE_RESOURCE)

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
    print(f"review flag counts:         {report.review_flag_counts}")
    for v in report.verdicts:
        status = "FLAGGED " if v.flags else "verified"
        extra = f" | review: {', '.join(v.review_flags)}" if v.review_flags else ""
        print(f"  - {status} {v.name}: {', '.join(v.flags) or '-'}{extra}")


if __name__ == "__main__":
    main()
