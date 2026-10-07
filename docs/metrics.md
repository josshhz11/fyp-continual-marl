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

Statistics: each challenge task is run across multiple seeds/workflow
instantiations per condition; results reported as **mean ± standard error,
with significance tested** between method and baseline before any
performance claim is made.

**Use an unpaired (two-sample) test, not a paired one** (e.g. Welch's t-test,
or Mann-Whitney U if score distributions look non-normal). A paired design
was the original plan, on the assumption that running condition A and
condition B under "the same seed" holds the underlying randomness constant
between them, reducing variance. Empirically confirmed this does not hold
(MA-Gym audit ML-092; see `external/manager_agent_gym/fixes/PROPOSED_FIXES_SUMMARY.md`,
Fix 5): the same seed, same model, same temperature=0, same prompt, with
nothing else running, produced 5 different outputs in 5 calls at the
isolated-LLM-call level; a full 10-step scenario run repeated with identical
seed/scenario/model diverged by step 8 and ended with a different task count
(52 vs. 53). "Seed s for condition A" and "seed s for condition B" are not
shared-randomness pairs — they are two independent draws that happen to
carry the same label. Applying a paired test to data like that doesn't just
lose power, it can understate variance and overstate significance, since the
test's assumptions (correlated pairs) don't hold. Plan more seeds per
condition than a paired design would have needed, to recover power lost by
giving up pairing — no fixed target seed count is set yet; size it with a
power analysis once a target effect size is chosen.

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

constraint_violations is computed by src/eval/run_metrics.py's
compute_constraint_violations, not read from the engine's own
aggregated_score: MA-Gym's ValidationEngine always falls back to a
hardcoded weighted-by-max formula whenever an evaluator has any rubric
results, silently ignoring whatever aggregation strategy was actually
declared (confirmed on a real ICAAP run — the built-in
constraint_adherence evaluator declares a hard-constraint zeroing gate,
hard_zero_agg, that never runs; the engine reported 0.0722 despite a
violated hard constraint, where the declared strategy would have scored
0.0 — see src/eval/constraint_aggregation.py and
tests/test_constraint_aggregation.py). It is null only when no evaluation
output exists for the run at all (e.g. evaluation was disabled) or the
named evaluator didn't run — never a silently-wrong number. When present,
shape:
- by_rubric_violated (dict[str, bool]) — one entry per rubric in the
  constraint_adherence evaluator group, true if it scored under its max
- violation_count (int) — count of the above
- correctly_aggregated_score (float) — the group's score under its actual
  declared aggregation (currently: hard_zero_agg's semantics — zero if
  hard_constraints_enforced scored 0, else the mean of every rubric)
- engine_reported_score (float | None) — MA-Gym's own (weighted-by-max)
  figure for the same group, kept for comparison

Scope note: "by constraint type" above currently means "by rubric name
within MA-Gym's built-in constraint_adherence evaluator" — this project has
not yet defined its own scenario-specific constraints (Phase 2/3 not
started); revisit this shape once it does.

This schema is the contract between src/eval/ and experiments/results/ —
any new metric must be added here before being logged.
