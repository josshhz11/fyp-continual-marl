"""Tests for the independent completion verifier (Fix 4)."""

from uuid import uuid4

import pytest

from eval.completion_verifier import (
    BLANK_FIELDS,
    EMPTY_OUTPUT,
    NEVER_STARTED,
    NO_ASSIGNED_AGENT,
    NO_OUTPUT_RESOURCES,
    PLACEHOLDER_CONTENT,
    SELF_REPORTED_NON_EXECUTION,
    TEMPLATE_RESOURCE,
    verify_workflow_summary,
)

GOOD = "Full analysis of the seller's obligations, with dates and named parties."


def _summary(tasks: list[dict], resources: list[dict]) -> dict:
    return {
        "tasks": {t["id"]: t for t in tasks},
        "resources": {r["id"]: r for r in resources},
    }


def _resource(content: str, name: str = "Deliverable") -> dict:
    return {"id": str(uuid4()), "name": name, "content": content}


def _task(resource: dict | None, **overrides) -> dict:
    task = {
        "id": str(uuid4()),
        "name": "Draft memo",
        "status": "completed",
        "subtasks": [],
        "assigned_agent_id": "worker-1",
        "started_at": "2026-01-01T00:00:00",
        "output_resource_ids": [resource["id"]] if resource else [],
        "execution_notes": [],
    }
    task.update(overrides)
    return task


def _flags_for(task: dict, resource: dict | None) -> list[str]:
    report = verify_workflow_summary(_summary([task], [resource] if resource else []))
    return report.verdicts[0].flags


def test_clean_completion_is_verified() -> None:
    res = _resource(GOOD)
    report = verify_workflow_summary(_summary([_task(res)], [res]))
    assert report.engine_completion_rate == 1.0
    assert report.verified_completion_rate == 1.0
    assert report.flagged_completions == []


def test_phantom_completion_without_agent_start_or_output() -> None:
    task = _task(None, assigned_agent_id=None, started_at=None)
    assert set(_flags_for(task, None)) == {
        NO_ASSIGNED_AGENT,
        NEVER_STARTED,
        NO_OUTPUT_RESOURCES,
    }


def test_empty_output_is_flagged() -> None:
    res = _resource("  ok ")
    assert _flags_for(_task(res), res) == [EMPTY_OUTPUT]


@pytest.mark.parametrize(
    "body",
    [
        "status: not_executed_no_input_data",
        "No input resources were provided, so nothing was computed. " + GOOD,
        "Result: not_computed. " + GOOD,
    ],
)
def test_self_reported_non_execution_is_flagged(body: str) -> None:
    res = _resource(body)
    assert SELF_REPORTED_NON_EXECUTION in _flags_for(_task(res), res)


def test_non_execution_note_on_task_is_flagged() -> None:
    res = _resource(GOOD)
    task = _task(res, execution_notes=["Worker: not executed, missing inputs"])
    assert SELF_REPORTED_NON_EXECUTION in _flags_for(task, res)


@pytest.mark.parametrize(
    "body",
    [
        "Agreement dated [Date] between the parties. " + GOOD,
        "Seller: [Seller Legal Name] " + GOOD,
        "Price: TBD. " + GOOD,
        "Lorem ipsum dolor sit amet. " + GOOD,
    ],
)
def test_placeholder_content_is_flagged(body: str) -> None:
    res = _resource(body)
    assert PLACEHOLDER_CONTENT in _flags_for(_task(res), res)


def _verdict(task: dict, resource: dict):
    return verify_workflow_summary(_summary([task], [resource])).verdicts[0]


def test_resource_named_template_is_review_only() -> None:
    res = _resource(GOOD, name="Model Inventory Template")
    verdict = _verdict(_task(res), res)
    assert verdict.review_flags == [TEMPLATE_RESOURCE]
    assert verdict.verified  # a review flag does not fail verification


def test_template_word_in_body_only_is_not_flagged() -> None:
    res = _resource("We reviewed the template used last year. " + GOOD)
    assert _flags_for(_task(res), res) == []


def test_markdown_links_and_citations_are_not_placeholders() -> None:
    res = _resource("See [the contract](https://example.com) and reference [1]. " + GOOD)
    assert _flags_for(_task(res), res) == []


def test_composites_are_excluded_and_rates_use_leaves() -> None:
    good, bad = _resource(GOOD), _resource("[Date] " + GOOD)
    leaf_ok, leaf_bad = _task(good), _task(bad)
    pending = _task(None, status="pending")
    parent = _task(None, subtasks=[leaf_ok], assigned_agent_id=None)
    report = verify_workflow_summary(
        _summary([parent, leaf_ok, leaf_bad, pending], [good, bad])
    )
    assert report.total_nodes == 3
    assert report.engine_completed == 2
    assert report.verified_completed == 1
    assert report.engine_completion_rate == pytest.approx(2 / 3)
    assert report.verified_completion_rate == pytest.approx(1 / 3)
    assert report.flag_counts[PLACEHOLDER_CONTENT] == 1


def test_metrics_payload_shape() -> None:
    res = _resource(GOOD)
    metrics = verify_workflow_summary(_summary([_task(res)], [res])).to_metrics()
    assert set(metrics) == {
        "verified_completion_rate",
        "completion_flags",
        "completion_review_flags",
    }


def test_empty_workflow_does_not_divide_by_zero() -> None:
    report = verify_workflow_summary({"tasks": {}, "resources": {}})
    assert report.verified_completion_rate == 0.0


def test_accepts_real_engine_summary_shape() -> None:
    """Build the summary the way OutputWriter.save_workflow_summary does."""
    pytest.importorskip("manager_agent_gym")
    from manager_agent_gym.schemas.core import Resource, Task, Workflow
    from manager_agent_gym.schemas.core.base import TaskStatus

    wf = Workflow(name="w", workflow_goal="g", owner_id=uuid4())
    res = Resource(name="Memo", description="d", content=GOOD)
    wf.add_resource(res)
    ok = Task(
        name="ok",
        description="d",
        status=TaskStatus.COMPLETED,
        assigned_agent_id="a",
        output_resource_ids=[res.id],
    )
    phantom = Task(name="phantom", description="d", status=TaskStatus.COMPLETED)
    wf.add_task(ok)
    wf.add_task(phantom)

    summary = wf.model_dump(mode="json", exclude={"agents"})
    summary["tasks"][str(ok.id)]["started_at"] = "2026-01-01T00:00:00"
    report = verify_workflow_summary(summary)

    assert report.engine_completed == 2
    assert report.verified_completed == 1
    assert report.flagged_completions[0].name == "phantom"


# Excerpt of a real ICAAP deliverable (blank form) that an earlier version missed.
REAL_BLANK_FORM = """# Access Control Documentation Template

## 1. Document Information
- Document Name/ID:
- Version:
- Date:

## 2. Access Roles
| Role | Description | Individuals/Groups |
|------|-------------|--------------------|
| Data Owner | Responsible for data classification | |
| Data Steward | Manages day-to-day access | |

## 5. Periodic Review
- Frequency (e.g., quarterly, annually):
- Reviewer(s):
"""


def test_real_blank_form_is_flagged_for_blank_fields() -> None:
    res = _resource(REAL_BLANK_FORM, name="Access Control Documentation")
    assert BLANK_FIELDS in _flags_for(_task(res), res)


def test_filled_bullets_and_list_intros_are_not_blank_fields() -> None:
    body = (
        "- Owner: Data Steward\n- Steps:\n    - extract\n    - load\n"
        "1. For every transfer, apply:\n   - reconcile counts\n" + GOOD
    )
    res = _resource(body)
    assert _flags_for(_task(res), res) == []


def test_single_blank_label_is_tolerated() -> None:
    res = _resource("- Notes:\n\nAnalysis follows. " + GOOD)
    assert BLANK_FIELDS not in _flags_for(_task(res), res)


@pytest.mark.parametrize(
    "body",
    [
        "| Model | Owner |\n|---|---|\n| ExamplePD01 | John Doe |",
        "Owner: Jane Smith. " + GOOD,
        "This template should be tailored and populated for each asset. " + GOOD,
    ],
)
def test_dummy_data_wording_is_flagged(body: str) -> None:
    res = _resource(body)
    assert PLACEHOLDER_CONTENT in _flags_for(_task(res), res)


def test_the_word_examples_is_not_a_placeholder() -> None:
    res = _resource("Examples of controls include reconciliation. " + GOOD)
    assert _flags_for(_task(res), res) == []
