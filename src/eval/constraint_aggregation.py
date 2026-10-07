"""Correct, scoped re-implementation of rubric-group aggregation (Fix 6: ML-016/033/034).

MA-Gym's ValidationEngine always falls back to a hardcoded weighted-by-max
formula (``sum(score)/sum(max_score)``) whenever a preference or evaluator has
any rubric results, and only consults the evaluator's own declared
``aggregation`` strategy when there are none — which never happens in
practice, since every real evaluator has rubrics. This makes every declared
strategy other than "sum over max" dead code, including the hard-constraint
gate:

``manager_agent_gym/core/evaluation/constraint_evaluator.py`` builds the
built-in ``constraint_adherence`` evaluator with ``aggregation=hard_zero_agg``
(zero the whole group if ``hard_constraints_enforced`` is 0), but because it
has 7 rubrics, that gate never runs. Confirmed on a real ICAAP run: the
``hard_constraints_enforced`` rubric scored 0.0 (a hard constraint was
violated), yet the reported ``constraint_adherence`` score was 0.0722, not
0.0 (see ``tests/test_constraint_aggregation.py``, which replays that exact
run's rubric data).

This module does not patch ``validation_engine.py`` — see
``external/manager_agent_gym/fixes/PROPOSED_FIXES_SUMMARY.md`` for why
(avoids engine surgery, keeps this independent of the platform decision).
Instead it re-aggregates the same ``RubricResult``-shaped data MA-Gym already
computes and exposes (``RubricGroupResult.rubric_scores`` /
``PreferenceScore.ruberic_group_results``), honoring the strategy actually
declared rather than silently overriding it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AggregationStrategy(str, Enum):
    """Mirrors manager_agent_gym.schemas.preferences.evaluator.AggregationStrategy.

    Kept as an independent copy rather than importing MA-Gym's enum, so this
    module has no import-time dependency on the engine (consistent with
    completion_verifier.py and run_metrics.py elsewhere in src/eval/).
    """

    WEIGHTED_AVERAGE = "weighted_average"
    MIN = "min"
    MAX = "max"
    PRODUCT = "product"
    HARMONIC_MEAN = "harmonic_mean"


@dataclass(frozen=True)
class RubricLike:
    """The minimal shape this module needs from a rubric result.

    Accepts either a MA-Gym RubricResult (which has these same attributes) or
    a plain dict with these keys, via `from_any`.
    """

    name: str
    normalized_score: float


def from_any(rubric: Any) -> RubricLike:
    if isinstance(rubric, RubricLike):
        return rubric
    if isinstance(rubric, dict):
        return RubricLike(name=rubric["name"], normalized_score=float(rubric["normalized_score"]))
    return RubricLike(name=rubric.name, normalized_score=float(rubric.normalized_score))


def aggregate(scores: list[float], strategy: AggregationStrategy) -> float:
    """The 5 built-in strategies, matching MA-Gym's own math exactly.

    `scores` are expected normalized to [0, 1] (score / max_score per
    rubric), same convention as MA-Gym's `normalized_by_owner`.
    """
    if not scores:
        return 0.0
    if strategy == AggregationStrategy.WEIGHTED_AVERAGE:
        return sum(scores) / len(scores)
    if strategy == AggregationStrategy.MIN:
        return min(scores)
    if strategy == AggregationStrategy.MAX:
        return max(scores)
    if strategy == AggregationStrategy.PRODUCT:
        product = 1.0
        for s in scores:
            product *= s
        return product
    if strategy == AggregationStrategy.HARMONIC_MEAN:
        if any(s == 0 for s in scores):
            return 0.0
        return len(scores) / sum(1 / s for s in scores if s > 0)
    raise ValueError(f"Unsupported strategy: {strategy!r}")


def hard_zero_gate(
    rubrics: list[Any], *, gate_rubric_name: str = "hard_constraints_enforced"
) -> float:
    """Re-implementation of constraint_evaluator.hard_zero_agg, operating on
    the rubric results directly rather than relying on the dead dispatch path.

    If the named gate rubric is present and scored 0, the whole group is 0.
    Otherwise, the mean of every rubric's normalized score (matching the
    original's `mean(scores)` over *all* rubrics, gate included).
    """
    resolved = [from_any(r) for r in rubrics]
    if not resolved:
        return 0.0
    gate = next((r.normalized_score for r in resolved if r.name == gate_rubric_name), 1.0)
    if gate == 0.0:
        return 0.0
    return sum(r.normalized_score for r in resolved) / len(resolved)


def weighted_by_max(raw_scores: list[float], max_scores: list[float]) -> float:
    """MA-Gym's actual (buggy-as-the-default, but sometimes legitimately
    wanted) fallback, exposed here so callers can compare against it or use
    it deliberately rather than get it silently no matter what they declared.
    """
    total_max = sum(max_scores)
    total_raw = sum(raw_scores)
    return (total_raw / total_max) if total_max > 0 else 0.0
