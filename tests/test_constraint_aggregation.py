"""Tests for the scoped aggregation re-implementation (Fix 6: ML-016/033/034)."""

import pytest

from eval.constraint_aggregation import (
    AggregationStrategy,
    aggregate,
    hard_zero_gate,
    weighted_by_max,
)

# ---------------------------------------------------------------------------
# Built-in strategies: known expected results, matching MA-Gym's own math.
# ---------------------------------------------------------------------------


def test_weighted_average_is_plain_mean() -> None:
    assert aggregate([1.0, 0.5, 0.0], AggregationStrategy.WEIGHTED_AVERAGE) == pytest.approx(0.5)


def test_min_strategy() -> None:
    assert aggregate([0.9, 0.3, 1.0], AggregationStrategy.MIN) == pytest.approx(0.3)


def test_max_strategy() -> None:
    assert aggregate([0.9, 0.3, 1.0], AggregationStrategy.MAX) == pytest.approx(1.0)


def test_product_strategy() -> None:
    assert aggregate([0.5, 0.5, 1.0], AggregationStrategy.PRODUCT) == pytest.approx(0.25)


def test_harmonic_mean_strategy() -> None:
    assert aggregate([1.0, 1.0], AggregationStrategy.HARMONIC_MEAN) == pytest.approx(1.0)
    assert aggregate([0.5, 1.0], AggregationStrategy.HARMONIC_MEAN) == pytest.approx(2 / 3)


def test_harmonic_mean_with_a_zero_is_zero() -> None:
    assert aggregate([0.0, 1.0], AggregationStrategy.HARMONIC_MEAN) == 0.0


def test_empty_scores_is_zero_for_every_strategy() -> None:
    for strategy in AggregationStrategy:
        assert aggregate([], strategy) == 0.0


# ---------------------------------------------------------------------------
# hard_zero_gate: the actual semantic the broken dead code was supposed to have.
# ---------------------------------------------------------------------------


def _rubric(name: str, normalized_score: float) -> dict:
    return {"name": name, "normalized_score": normalized_score}


def test_hard_zero_gate_zeroes_the_whole_group_on_violation() -> None:
    rubrics = [
        _rubric("hard_constraints_enforced", 0.0),
        _rubric("constraint_coverage_mapping", 0.889),
        _rubric("deadline_guardrails", 1.0),
    ]
    assert hard_zero_gate(rubrics) == 0.0


def test_hard_zero_gate_averages_when_no_violation() -> None:
    rubrics = [
        _rubric("hard_constraints_enforced", 1.0),
        _rubric("constraint_coverage_mapping", 0.5),
    ]
    assert hard_zero_gate(rubrics) == pytest.approx(0.75)


def test_hard_zero_gate_defaults_to_open_when_gate_rubric_absent() -> None:
    rubrics = [_rubric("constraint_coverage_mapping", 0.5)]
    assert hard_zero_gate(rubrics) == pytest.approx(0.5)


def test_hard_zero_gate_empty_is_zero() -> None:
    assert hard_zero_gate([]) == 0.0


def test_weighted_by_max_matches_validation_engines_own_formula() -> None:
    # sum(raw)/sum(max): 2.889 / 40, matching ValidationEngine's literal formula.
    assert weighted_by_max([0.889, 1.0, 1.0], [1.0, 1.0, 1.0]) == pytest.approx(2.889 / 3.0)


# ---------------------------------------------------------------------------
# Real-data regression: the exact rubric scores from a real ICAAP run where
# MA-Gym's engine reported constraint_adherence=0.0722 despite a hard
# constraint violation that should have zeroed it under its own declared
# aggregation (hard_zero_agg). See src/eval/constraint_aggregation.py for the
# source run.
# ---------------------------------------------------------------------------

ICAAP_RUN_CONSTRAINT_RUBRICS = [
    {"name": "constraint_coverage_mapping", "score": 0.8888888888888888, "max_score": 1.0, "normalized_score": 0.8888888888888888},
    {"name": "deadline_guardrails", "score": 1.0, "max_score": 1.0, "normalized_score": 1.0},
    {"name": "prohibited_actions_avoidance", "score": 1.0, "max_score": 1.0, "normalized_score": 1.0},
    {"name": "formal_signoffs_present", "score": 0.0, "max_score": 10.0, "normalized_score": 0.0},
    {"name": "access_control_pii_evidence", "score": 0.0, "max_score": 10.0, "normalized_score": 0.0},
    {"name": "soft_constraints_tradeoff_documentation", "score": 0.0, "max_score": 6.0, "normalized_score": 0.0},
    {"name": "data_lineage_controls_evidence", "score": 0.0, "max_score": 10.0, "normalized_score": 0.0},
    {"name": "hard_constraints_enforced", "score": 0.0, "max_score": 1.0, "normalized_score": 0.0},
]
ENGINE_REPORTED_SCORE = 0.07222222222222222  # aggregated_score actually logged for this run


def test_engines_reported_score_matches_weighted_by_max_not_the_declared_strategy() -> None:
    """Confirms the bug as observed: the engine's output is weighted-by-max,
    not hard_zero_agg (the strategy constraint_evaluator.py actually declares
    for this evaluator)."""
    raw = [r["score"] for r in ICAAP_RUN_CONSTRAINT_RUBRICS]
    max_ = [r["max_score"] for r in ICAAP_RUN_CONSTRAINT_RUBRICS]
    assert weighted_by_max(raw, max_) == pytest.approx(ENGINE_REPORTED_SCORE)


def test_declared_strategy_would_have_scored_zero_on_this_real_run() -> None:
    """What should have been reported, had the declared aggregation actually
    run: 0.0, since hard_constraints_enforced was violated."""
    assert hard_zero_gate(ICAAP_RUN_CONSTRAINT_RUBRICS) == 0.0
    assert hard_zero_gate(ICAAP_RUN_CONSTRAINT_RUBRICS) != pytest.approx(ENGINE_REPORTED_SCORE)
