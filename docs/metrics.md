# Evaluation Metrics

## Per-Task Evaluation Questions and Metrics

1. How does the memory-augmented manager compare to CoT/Random/Assign-All on **goal completion, constraint adherence, and runtime**?
   1. Metrics: Goal completion rate (% of task graph nodes completed), constraint adherence (violation count/rate per episode, by constraint type), Runtime (wall-clock timesteps to completion), Composite/Pareto view across all three metrics
2. How does **performance scale** with churn frequency, number of preference shifts per episode, and workflow size?
   1. Metrics: Same three (goal completion, constraint adherence, runtime), **each plotted against churn count / shift count / workflow size**, with mean ± standard error across seeds at each point – the degradation slope, not just endpoints
3. What is the individual contribution of the Phase 2 selector vs. Phase 3 memory vs their combination (ablation)?
   1. Metrics: Same three, compared across – CoT baseline, Phase 2 only, Phase 3 only, combined; contribution margin (delta over baseline per component, and delta of combined over either alone)
4. How does **performance degrade** if retrieved memory is irrelevant or misleading (robustness to a violated assumption)?
   1. Metrics: **Performance delta under corrupted vs. clean retrieval**; **retrieval relevance rate** (fraction of retrieved memories from a genuinely similar workflow); check whether degraded performance floors at the no-memory baseline or drops below it (graceful vs. harmful failure)

## Baselines

* Bounds: an oracle upper bound with advance knowledge of preference/team changes, and a "frozen" lower-bound manager that never re-reads updated state after episode start.
* Ablations: Phase 2 selector alone, Phase 3 memory alone, and the combined system.
* State-of-the-art comparison: CoT (current published SOTA on MA-Gym), plus a naive full-history-in-context baseline (no retrieval) as a fair additional comparison point.

## Statistics

Statistics: each challenge task is run across multiple seeds/workflow instantiations per condition; results reported as **mean ± standard error, with significance tested** (e.g. paired t-test) between method and baseline before any performance claim is made.

## Logging Schema

For each experiment run, the following fields must be captured in
metrics.json:
- goal_completion_rate (float, 0-1)
- constraint_violations (dict, keyed by constraint type)
- runtime_timesteps (int)
- condition (str: one of "cot", "random", "assign_all", "oracle_upper",
  "frozen_lower", "phase2_only", "phase3_only", "combined",
  "full_history_baseline")
- challenge_task (str: one of "preference_shift", "team_churn",
  "compound", "cross_episode")
- seed (int)
- change_depth (str: one of "early", "mid", "late", "n/a" — n/a for
  cross_episode and any task without an injected preference/churn
  event)
- verified_completion_rate (float, 0-1) — goal_completion_rate re-scored by
  src/eval/completion_verifier.py. A COMPLETED task only counts as verified if
  it has an assigned agent, a start, non-empty output, no self-reported
  non-execution, no placeholder/dummy content and no blank form fields (MA-Gym
  audit ML-003/009/011/015). Log it next to goal_completion_rate; report both.
- completion_flags (dict[str, int]) — count of completed tasks per failing
  check from the same verifier.
- completion_review_flags (dict[str, int]) — checks that need a human look but
  do not reduce verified_completion_rate (currently: template_resource, a
  deliverable named as a template).

constraint_violations is null until the constraint scoring fix (Fix 6) lands;
src/eval/run_metrics.py writes null rather than an unreliable engine figure.

This schema is the contract between src/eval/ and experiments/results/ —
any new metric must be added here before being logged.
