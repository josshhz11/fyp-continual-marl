"""Build metrics.json for one MA-Gym run, following the schema in docs/metrics.md.

Reads the final workflow summary the engine writes under
``<run_dir>/workflow_outputs/`` and logs the engine's own completion rate next to
the independently verified one (see completion_verifier).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .completion_verifier import verify_workflow_summary

CONDITIONS = (
    "cot",
    "random",
    "assign_all",
    "oracle_upper",
    "frozen_lower",
    "phase2_only",
    "phase3_only",
    "combined",
    "full_history_baseline",
)
CHALLENGE_TASKS = ("preference_shift", "team_churn", "compound", "cross_episode")
CHANGE_DEPTHS = ("early", "mid", "late", "n/a")

_SNAPSHOT = re.compile(r"_t\d+$")  # per-timestep snapshots, e.g. ..._seed_42_t0007


def find_final_summary(run_dir: str | Path) -> Path:
    """The final summary, not the per-timestep ``..._t0007.json`` snapshots."""
    candidates = [
        p
        for p in Path(run_dir, "workflow_outputs").glob("workflow_execution_*.json")
        if not _SNAPSHOT.search(p.stem)
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"expected exactly one final workflow summary under {run_dir}/workflow_outputs, "
            f"found {len(candidates)}"
        )
    return candidates[0]


def build_run_metrics(
    run_dir: str | Path,
    *,
    condition: str,
    challenge_task: str,
    change_depth: str = "n/a",
) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, got {condition!r}")
    if challenge_task not in CHALLENGE_TASKS:
        raise ValueError(f"challenge_task must be one of {CHALLENGE_TASKS}, got {challenge_task!r}")
    if change_depth not in CHANGE_DEPTHS:
        raise ValueError(f"change_depth must be one of {CHANGE_DEPTHS}, got {change_depth!r}")

    with open(find_final_summary(run_dir), encoding="utf-8") as f:
        summary = json.load(f)
    report = verify_workflow_summary(summary)

    return {
        "goal_completion_rate": report.engine_completion_rate,
        # Not computed yet: needs the constraint scoring fix (Fix 6).
        "constraint_violations": None,
        "runtime_timesteps": int(summary.get("timesteps", 0)),
        "condition": condition,
        "challenge_task": challenge_task,
        "seed": int(summary.get("seed", 0)),
        "change_depth": change_depth,
        **report.to_metrics(),
    }


def write_run_metrics(run_dir: str | Path, **kwargs: Any) -> Path:
    metrics = build_run_metrics(run_dir, **kwargs)
    path = Path(run_dir) / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write metrics.json for one run")
    parser.add_argument("run_dir", help="e.g. <output-dir>/icaap/run_seed_42")
    parser.add_argument("--condition", required=True, choices=CONDITIONS)
    parser.add_argument("--challenge-task", required=True, choices=CHALLENGE_TASKS)
    parser.add_argument("--change-depth", default="n/a", choices=CHANGE_DEPTHS)
    args = parser.parse_args(argv)

    path = write_run_metrics(
        args.run_dir,
        condition=args.condition,
        challenge_task=args.challenge_task,
        change_depth=args.change_depth,
    )
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
