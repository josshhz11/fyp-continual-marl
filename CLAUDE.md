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

## Current Focus
Setting up Phase 1 environment and MA-Gym submodule.
