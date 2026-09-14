# CLAUDE.md — Project Memory

## Identity
Project ID: CCDS26-0710
Acad Yr/Sem: 2026/1
Title: Continual Multi-Agent Workflow Orchestration
Supervisor: A/P Stefano Vittorino Albrecht

## Research Gap (one paragraph)
The MA-Gym paper identifies four foundational challenges in workflow orchestration; this project targets challenges (2) multi-objective optimization under shifting stakeholder preferences and (3) coordination and planning in ad hoc teams, since MA-Gym names these as open but does not attempt a learned or continual solution to either. Following the shift in continual RL and inference-time adaptation literature away from gradient-based retraining, the architectural stance is to keep the manager LLM frozen and place learned/adaptive components (a lightweight selection layer, then episodic memory) around it, rather than fine-tuning the LLM or learning a policy over its full raw action space.

## Phase Status
- Phase 1 (Baseline Reproduction): NOT STARTED
- Phase 2 (Lightweight Learned Selection Layer): NOT STARTED
- Phase 3 (Episodic Memory for Continual Adaptation): NOT STARTED
- Phase 4 (Zero-Shot Generalization, stretch): NOT STARTED
[Update this line whenever a phase begins/completes — don't let it go stale]

## Before You Build Anything
- Challenge task definitions: see docs/challenge-tasks.md — every
  scenario in src/scenarios/ must implement one of these four tasks,
  not a variant invented ad hoc.
- Metrics and logging schema: see docs/metrics.md — every experiment
  must log to the schema defined there so results stay comparable
  across phases.
- Past decisions: check notes/DECISIONS.md before making an
  architectural choice that contradicts or extends the proposal.
- Past results: check experiments/results/INDEX.md before re-running
  something that may have already been tried.

## Repo Conventions
- external/manager_agent_gym is a git submodule — do not edit it directly.
- experiments/results/*/raw/ is gitignored — never commit raw logs.
- Every experiment run must get an entry in experiments/results/INDEX.md.

## Known Issues / Open Questions (pending supervisor meeting)
Supervisor's group is refactoring MA-Gym after an audit found several
critical/high-severity undocumented bugs, and is evaluating a successor
platform, Ergon (https://github.com/DeepFlow-research/ergon). A group
meeting next week will decide direction. **Platform choice
(manager_agent_gym vs. ergon) is undecided** — do not commit to either
beyond what's needed for a single-workflow smoke test until that
decision is made.

Audited bugs relevant to this project:
- **NEW-001** — the preference weight vector shown to the manager does
  not match the weight vector actually scored, in 16 of 20 scenarios.
  Directly affects the preference-shift challenge task: the manager's
  observed vs. scored preferences may already diverge natively, which
  would confound any shift we inject on top.
- **ML-092** — seed=42 does not reliably control reproducibility;
  identical seeds have produced very different runs. Undermines the
  paired significance-testing approach in docs/metrics.md, which
  assumes seed-controlled comparability between conditions.
- **ML-009** — reported completion ~100% vs. actual 42-66% due to
  inadequate handoffs. Affects trust in goal_completion_rate as logged
  by the engine — may need independent verification rather than taking
  the reported figure at face value.
- **ML-025/ML-026** — EACH_TIMESTEP evaluation cadence broken by
  default. Affects any metric intended to be sampled every timestep
  (e.g. tracking degradation across injected-shift depths within an
  episode).
- **ML-036** — LLM-judge scoring noise large enough to flip which
  condition wins. Affects any evaluation question that relies on
  judge-scored preference/quality metrics to rank conditions,
  including baseline comparisons and ablations.

Own findings from the single-workflow smoke test (not from the audit
list, but relevant to the platform decision):
- `examples/getting_started/hello_manager_agent.py` never registers a
  real worker team for the ICAAP scenario — `workflow.agents` is empty
  for that scenario (its team lives in the separate `team.py`, unlike
  `workflow.py`), so the example silently runs with 0 registered
  agents. It doesn't crash, but its completion-rate output is
  meaningless. Use `examples.run_examples.run_demo(...)` instead — it
  correctly loads each scenario's team timeline.
- The ICAAP scenario's folder is `examples/end_to_end_examples/icap/`
  but its registry key in `examples/scenarios.py` is `"icaap"`, not
  `"icap"` — easy to trip over when scripting runs.
- `run_demo`'s/`create_manager`'s `model_name` argument only controls
  the *manager* agent's model. The rubric/LLM-judge evaluation pipeline
  (`manager_agent_gym/core/evaluation/validation_rules.py`) has its own
  independent hardcoded default of `model: str = "o3"`, with no
  parameter on `run_demo` to redirect it. A single 20-timestep run of
  one workflow with `model_name="gpt-4o-mini"` still hit `o3`'s 30,000
  TPM org rate limit repeatedly from evaluation calls alone — this
  compounds ML-036 (same `o3`-judge pipeline) and means per-run API
  cost/rate-limit exposure is higher than the manager model choice
  alone would suggest; budget planning must account for the evaluator
  cost separately from the manager cost.

## Current Focus
Phase 1 is deliberately scoped to a single-workflow smoke test of
external/manager_agent_gym (confirming environment/tooling work) —
NOT full CoT/Random/Assign-All baseline reproduction across all 20
workflows, and NOT challenge-task scenario implementation against the
engine's internals. Both are paused pending the platform decision
above, so API budget and design effort aren't spent on a platform that
may be replaced.
