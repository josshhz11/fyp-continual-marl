"""Tests for metrics.json construction (Fix 4 DoD: both completion fields are logged)."""

import json
from pathlib import Path

import pytest

from eval.run_metrics import build_run_metrics, find_final_summary, write_run_metrics

GOOD = "Full analysis of the seller's obligations, with dates and named parties."


def _make_run(tmp_path: Path, *, with_snapshots: bool = True) -> Path:
    out = tmp_path / "workflow_outputs"
    out.mkdir()
    summary = {
        "seed": 42,
        "timesteps": 20,
        "tasks": {
            "a": {
                "id": "a",
                "name": "done",
                "status": "completed",
                "subtasks": [],
                "assigned_agent_id": "w",
                "started_at": "2026-01-01T00:00:00",
                "output_resource_ids": ["r"],
                "execution_notes": [],
            },
            "b": {"id": "b", "name": "todo", "status": "pending", "subtasks": []},
        },
        "resources": {"r": {"id": "r", "name": "Memo", "content": GOOD}},
    }
    (out / "workflow_execution_seed_42.json").write_text(json.dumps(summary))
    if with_snapshots:
        (out / "workflow_execution_seed_42_t0007.json").write_text("{}")
    return tmp_path


def test_finds_final_summary_not_snapshots(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    assert find_final_summary(run).name == "workflow_execution_seed_42.json"


def test_metrics_follow_the_logging_schema(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    m = build_run_metrics(run, condition="random", challenge_task="preference_shift", change_depth="mid")
    assert m["goal_completion_rate"] == 0.5
    assert m["verified_completion_rate"] == 0.5
    assert m["runtime_timesteps"] == 20
    assert m["seed"] == 42
    assert m["condition"] == "random"
    assert m["challenge_task"] == "preference_shift"
    assert m["change_depth"] == "mid"
    assert m["constraint_violations"] is None  # pending Fix 6
    assert set(m["completion_flags"]) and "completion_review_flags" in m


def test_write_creates_metrics_json(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    path = write_run_metrics(run, condition="cot", challenge_task="team_churn")
    assert path == run / "metrics.json"
    assert json.loads(path.read_text())["change_depth"] == "n/a"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"condition": "nope", "challenge_task": "team_churn"},
        {"condition": "cot", "challenge_task": "nope"},
        {"condition": "cot", "challenge_task": "team_churn", "change_depth": "soon"},
    ],
)
def test_rejects_values_outside_the_schema(tmp_path: Path, kwargs: dict) -> None:
    with pytest.raises(ValueError):
        build_run_metrics(_make_run(tmp_path), **kwargs)


def test_missing_summary_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "workflow_outputs").mkdir()
    with pytest.raises(FileNotFoundError):
        find_final_summary(tmp_path)
