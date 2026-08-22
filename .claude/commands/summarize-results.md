---
description: Summarize a completed experiment run and add it to experiments/results/INDEX.md
---

Summarize the results of an experiment run and record it in experiments/results/INDEX.md.

Steps:
1. Locate the relevant run under experiments/results/ (ask the user for the experiment_id or path if it isn't clear from context).
2. Read its metrics.json (per the schema in docs/metrics.md) and compute: goal_completion_rate, constraint_violations summary, runtime_timesteps, and any per-seed mean ± standard error if multiple seeds are present.
3. Append one row to experiments/results/INDEX.md with columns:
   experiment_id | date | phase | challenge_task | condition | goal_completion | constraint_violations | runtime | notes
4. Do not overwrite or reorder existing rows.
5. In the notes column, flag anything notable: unexpected failures, whether results support or contradict a prior claim in notes/DECISIONS.md, or whether the run should be treated as provisional (e.g. too few seeds for significance testing per docs/metrics.md).
6. Report back a short plain-text summary of the run's headline numbers.
