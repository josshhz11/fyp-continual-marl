"""Tests for metrics.json construction (Fix 4 DoD: both completion fields are logged)."""

import json
from pathlib import Path

import pytest

from eval.run_metrics import (
    build_run_metrics,
    compute_constraint_violations,
    find_final_evaluation,
    find_final_summary,
    write_run_metrics,
)

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
    assert m["constraint_violations"] is None  # no evaluation_outputs in this fixture
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


# ---------------------------------------------------------------------------
# constraint_violations (Fix 6), including a replay of the real ICAAP run
# where the engine reported 0.0722 despite a hard-constraint violation.
# ---------------------------------------------------------------------------

ICAAP_CONSTRAINT_RUBRICS = [
    {"name": "constraint_coverage_mapping", "score": 0.8888888888888888, "max_score": 1.0},
    {"name": "deadline_guardrails", "score": 1.0, "max_score": 1.0},
    {"name": "prohibited_actions_avoidance", "score": 1.0, "max_score": 1.0},
    {"name": "formal_signoffs_present", "score": 0.0, "max_score": 10.0},
    {"name": "access_control_pii_evidence", "score": 0.0, "max_score": 10.0},
    {"name": "soft_constraints_tradeoff_documentation", "score": 0.0, "max_score": 6.0},
    {"name": "data_lineage_controls_evidence", "score": 0.0, "max_score": 10.0},
    {"name": "hard_constraints_enforced", "score": 0.0, "max_score": 1.0},
]


def _add_evaluation_outputs(run: Path, *, rubrics: list[dict]) -> None:
    out = run / "evaluation_outputs"
    out.mkdir()
    (out / "final_evaluation_seed_42.json").write_text(
        json.dumps(
            {
                "evaluation_results": [
                    {
                        "evaluator_name": "constraint_adherence",
                        "aggregation_strategy": "weighted_by_max",
                        "aggregated_score": sum(r["score"] for r in rubrics)
                        / sum(r["max_score"] for r in rubrics),
                        "rubric_scores": rubrics,
                    }
                ]
            }
        )
    )


def test_no_evaluation_outputs_means_null_constraint_violations(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    assert find_final_evaluation(run) is None
    assert compute_constraint_violations(run) is None


def test_constraint_violations_recomputed_from_real_icaap_run_data(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    _add_evaluation_outputs(run, rubrics=ICAAP_CONSTRAINT_RUBRICS)

    result = compute_constraint_violations(run)

    assert result["engine_reported_score"] == pytest.approx(0.07222222222222222)
    assert result["correctly_aggregated_score"] == 0.0  # hard constraint violated -> gated to 0
    assert result["by_rubric_violated"]["hard_constraints_enforced"] is True
    assert result["by_rubric_violated"]["deadline_guardrails"] is False
    # 6 of 8 rubrics scored under their max: constraint_coverage_mapping (0.889/1.0),
    # formal_signoffs_present, access_control_pii_evidence,
    # soft_constraints_tradeoff_documentation, data_lineage_controls_evidence (all 0),
    # and hard_constraints_enforced (0/1). Only deadline_guardrails and
    # prohibited_actions_avoidance hit their max.
    assert result["violation_count"] == 6


def test_build_run_metrics_includes_constraint_violations_when_available(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    _add_evaluation_outputs(run, rubrics=ICAAP_CONSTRAINT_RUBRICS)

    m = build_run_metrics(run, condition="cot", challenge_task="team_churn")

    assert m["constraint_violations"]["correctly_aggregated_score"] == 0.0


def test_evaluator_present_with_no_rubrics_is_a_vacuous_answer_not_null(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    out = run / "evaluation_outputs"
    out.mkdir()
    (out / "final_evaluation_seed_42.json").write_text(
        json.dumps({"evaluation_results": [{"evaluator_name": "constraint_adherence", "rubric_scores": []}]})
    )
    result = compute_constraint_violations(run)
    assert result is not None
    assert result["violation_count"] == 0
    assert result["by_rubric_violated"] == {}


def test_evaluator_not_found_at_all_is_null(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    out = run / "evaluation_outputs"
    out.mkdir()
    (out / "final_evaluation_seed_42.json").write_text(json.dumps({"evaluation_results": []}))
    assert compute_constraint_violations(run) is None
