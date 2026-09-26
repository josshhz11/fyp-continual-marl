# Decisions Log

## [2026-09-17] Down-scope primary work to preference-shift and team-churn; cross-episode as stretch

**Context:** The MA-Gym audit (`external/manager_agent_gym/fixes/MA_GYM_ERGON_EVALUATION.md`) shows many bugs touching our four challenge tasks, and the preference-shift, team-churn, compound and cross-episode tasks do not all depend on the same fixes. The user asked whether to reduce scope.

**Decision:** Treat team-churn and preference-shift as the primary tasks, run individually. Compound only after both are individually trustworthy. Cross-episode is a smaller-scale stretch goal (e.g. one workflow, 2-3 consecutive runs). Working plan only: not yet confirmed with the supervisor.

**Rationale:** Team-churn benefits most from the one well-evidenced fix (real artifact handoff). Preference-shift is central to the research gap but depends on NEW-001, which was unverified. Compound is a composition of the two. Cross-episode has no existing memory infrastructure on either platform (Ergon's persistence feeds gradient-based RL, which our frozen-manager stance rejects), so it is the highest build-from-scratch risk.

**Alternatives considered:** Keep all four tasks in scope (rejected: too much unverified infrastructure). Drop cross-episode entirely (rejected: it is the direct test of the "continual" claim, so keep it as a stretch).

**Affects:** Phase 2-4 scoping, `docs/challenge-tasks.md`, ordering of the fix phases below.

## [2026-09-22] Fix only the MA-Gym bugs this project needs (MUST / SHOULD / DEFER)

**Context:** The audit lists 32+ critical/high bugs. The meeting notes say the supervisor's group wants a refactored, modular MA-Gym, but our own deadline is our experiments.

**Decision:** Fix only what blocks our experiments. MUST: NEW-001, ML-001/002, ML-051/052/053, ML-003/009/011/015. SHOULD: ML-092, ML-016/033/034, ML-007/023, ML-025/026 (the last two optional). DEFER: ML-070/072/073 (archive/restore, only for cross-episode), ML-036 (judge noise, mitigated by practice), ML-006/045/047/050 (monitor). Recorded in `fixes/PROPOSED_FIXES_SUMMARY.md`.

**Rationale:** A full repair is a multi-month effort neither MA-Gym's nor Ergon's team has finished. A small, bounded set keeps commits isolated and easy to cherry-pick into the shared refactor.

**Alternatives considered:** Fix everything (rejected: out of FYP scope). Migrate to Ergon (rejected: Ergon does not address fake completion, seed reproducibility, preference-vector fidelity or restore fidelity, and has same-shape open bugs of its own).

**Affects:** All phases; `external/manager_agent_gym`; `src/eval/`.

## [2026-09-22] Ergon is a reference, not a migration target; fixes are platform-independent

**Context:** Platform choice (MA-Gym vs Ergon) was undecided in CLAUDE.md. The meeting notes indicate the group will build a fixed, modular MA-Gym, with Tianyi's adaptive MA-Gym as a template.

**Decision:** Do not migrate to Ergon. Use it for patterns only (e.g. artifact handoff design, full-artifact judge context). Design each fix so it does not depend on the platform choice, and put verification tooling outside the engine (`src/eval/`).

**Rationale:** Ergon fixes handoff well and the judge preview in one evaluator, but leaves most of what we depend on unaddressed and is less tested than MA-Gym (its own audit shows silent-zero and empty-description bugs).

**Alternatives considered:** Full migration to Ergon; wait for the supervisor's decision before doing anything (rejected: blocks all progress).

**Affects:** Every fix's "Ergon relevance" note; `CLAUDE.md` "Known Issues" paragraph (still says undecided; needs the user's confirmation before rewording).

## [2026-09-22] Work on a personal fork of MA-Gym; one commit per fix; no upstream PRs

**Context:** `external/manager_agent_gym` is a submodule of the official repo, and CLAUDE.md said "do not edit it directly". Fixes need to live somewhere fetchable, and waiting on upstream PRs would slow work.

**Decision:** Fork to `josshhz11/manager_agent_gym`, work on branch `fyp/ma-gym-fixes`, and repoint `.gitmodules` at the fork (upstream stays as remote `upstream`). One isolated commit per fix, pushed to the fork. Do not merge the fork branch into the fork's `main` (keep it a clean mirror of upstream). Docs about the fixes live in the submodule under `fixes/`. Order per fix: commit and push in the submodule first, then bump the pointer in the parent repo on a dated branch.

**Rationale:** The parent repo only stores a commit SHA, so that commit must be reachable from the configured URL. Per-fix commits (not per-fix branches) are enough to cherry-pick into the shared team fork later and avoid merge overhead.

**Alternatives considered:** Plain local edits (rejected: other machines cannot fetch the commit). A branch per fix (rejected: overhead for no extra isolation). PRs to upstream (rejected: slow, and the shared refactor is the real destination).

**Affects:** `.gitmodules`, `external/manager_agent_gym`, branch naming (`<type>/<YY>.<MM>_<slug>`), CLAUDE.md convention line (now outdated: we do edit the fork).

## [2026-09-22] Implement fixes in phases: A (integrity), B (coordination), C (metrics trust)

**Context:** Eight fixes need an order.

**Decision:** Phase A: Fix 1 (NEW-001), Fix 4 (completion verification). Phase B: Fix 2 (handoff), Fix 3 (churn/reassignment). Phase C: Fix 5 (seed), Fix 6 (aggregation), Fix 7 and 8 (optional). Each fix has a Definition-of-Done checklist.

**Rationale:** Phase A is cheap, isolated and unblocks everything. Reassignment (Fix 3) only tests meaningfully once handoff (Fix 2) is real. Statistics-trust fixes matter before cross-condition comparisons, not before smoke tests.

**Alternatives considered:** Fix 4 before Fix 1 (rejected: Fix 4 is new tooling, Fix 1 is a small diagnosed patch).

**Affects:** `fixes/PROPOSED_FIXES_SUMMARY.md`; the order of work.

## [2026-09-22] Fix 2 (handoff): propagate outputs along dependency edges, not port Ergon's artifact store

**Context:** ML-001: `Task.input_resource_ids` has no writer, so workers never see predecessor output. Ergon replaced this with a content-addressed blob store.

**Decision:** Planned, not yet implemented: when a task completes, append its `output_resource_ids` to every dependent task's `input_resource_ids` (walk `dependency_task_ids`). Known limitation to document: subtasks created by decomposition before the parent is wired (ML-008). Scenario definitions must also declare resource wiring (ML-002).

**Rationale:** Achieves the observable behaviour (a worker sees predecessor output) with far less surface area than a store rewrite.

**Alternatives considered:** Port Ergon's artifact model (rejected: disproportionate for the scope; keep as a design reference).

**Affects:** `manager_agent_gym/core/execution/engine.py`, `schemas/core/tasks.py`, team-churn and compound tasks.

## [2026-09-22] Fixes 3, 5, 6, 7, 8: chosen approaches (not yet implemented)

**Context:** Remaining fixes need a direction so their scope stays bounded.

**Decision:** Fix 3: add a requeue path when an assigned worker leaves, validate `AssignTaskAction` for un-executable tasks, and write the rejection back to the manager (audit line numbers to be re-verified first). Fix 5: test seed reproducibility empirically (same seed twice, diff actions) before any code change; if it fails, fall back to an unpaired test with more seeds rather than threading seeds through the provider stack. Fix 6: write our own aggregation for exactly the constraint rubrics we use and test it, instead of repairing MA-Gym's shared aggregation. Fix 7 and 8: only if the ablation or per-timestep tracking needs them.

**Rationale:** Each is scoped to what our metrics need, avoiding general repairs of the shared engine.

**Alternatives considered:** General fixes to the evaluation engine (rejected: multi-month, and the shared refactor may replace it).

**Affects:** Phases B and C; `docs/metrics.md` statistics section (paired vs unpaired test).

## [2026-09-24] Fix 1 (NEW-001): copy Preference objects at the construction site

**Context:** `StakeholderAgent.apply_weight_update` mutated `Preference.weight` on the live timeline entry, and `PreferenceWeights`' validator normalizes in place, so updating at a later timestep rewrote the earlier entry.

**Decision:** Build `name_to_pref` from `preference.model_copy()` (one change in `stakeholder_agent.py`), rather than copying in each update-mode branch. Corrected the plan's root cause: it is the earlier entry that is corrupted, not the new one.

**Rationale:** One change covers every mode and the validator's in-place normalization. Evidence: on the original code all 20 registered scenarios with scripted shifts rewrote earlier timesteps (in ICAAP, `t=0` read `quality=0.286`, the `t=10` value, instead of `0.429`); with the fix all pass. Full suite: 78 passed. No other library code mutates a returned timeline entry.

**Alternatives considered:** Copy inside each branch (more edits, easier to miss); deep-copy in `get_preferences_for_timestep` (does not stop the validator mutating inputs).

**Affects:** `stakeholder_agent.py`, `tests/test_stakeholder_preference_history.py`, `tests/test_icaap_preference_shift_history.py`; preference-shift task. Note: the audit measured "shown vs scored t=0 vector differs in 16/20"; our invariant (no earlier timestep rewritten) fails in 20/20 on the original code. They measure slightly different things.

## [2026-09-24] Fix 4: verify completion with an external post-hoc verifier, not by patching the engine

**Context:** MA-Gym marks a task COMPLETED when the worker call returns without raising (engine.py:639), so `goal_completion_rate` overstates progress (ML-003/009/011/015).

**Decision:** Build `src/eval/completion_verifier.py`: it reads the final workflow summary JSON, scores only leaf tasks, and reports the engine's completion rate next to a verified rate. Log both, never replace the engine figure.

**Rationale:** Avoids engine surgery and conflicts with the shared refactor; works on any platform's output; keeps the engine number visible for comparison with published results.

**Alternatives considered:** Patch `engine.py` to validate on completion (rejected: conflicts with the shared refactor, and would change reported numbers silently). Use the LLM judge (rejected: ML-036 noise, cost).

**Affects:** `src/eval/`, `docs/metrics.md`, all four challenge tasks (all report `goal_completion_rate`).

## [2026-09-24] Smoke-test protocol for MA-Gym runs

**Context:** We needed a cheap real run to test Fix 1 and Fix 4.

**Decision:** Run `icaap` with `--manager-agent-mode random --model-name gpt-4o-mini --max-timesteps 20 --seed 42` and an `--output-dir` outside the repo (raw logs must not be committed). On Windows, set `PYTHONUTF8=1` when redirecting output.

**Rationale:** ICAAP scripts a preference shift at `t=10` and team additions at `t=0` and `t=15`, so it exercises Fix 1. Findings: the "random" manager still calls an LLM (the first run failed all 20 steps on an invalid API key), worker cost was about $0.03 by the engine's count (judge cost not included), and the `o3` judge hits its 30k TPM limit.

**Alternatives considered:** Full 50-step runs (rejected: cost, rate limits).

**Affects:** `experiments/`, budgeting, CLAUDE.md smoke-test notes.

## [2026-09-24] Track fix progress in the plan doc, with a `/status-update` command

**Context:** Fix status was only in the conversation.

**Decision:** Each fix and phase carries a `Status`, "Summary of Changes Done" and "What's left to verify" in `PROPOSED_FIXES_SUMMARY.md`, refreshed by `.claude/commands/status-update.md`, which derives them from git and test evidence and ticks DoD boxes only on observed evidence.

**Rationale:** Keeps the plan honest and reproducible from a fresh session.

**Alternatives considered:** Ad hoc notes (drift out of date).

**Affects:** `fixes/PROPOSED_FIXES_SUMMARY.md`, `.claude/commands/status-update.md`.

## [2026-09-26] Verifier flag policy: hard flags fail verification; "template" is review-only

**Context:** On the real ICAAP run, the first verifier reported 3/3 completed tasks verified, but reading the outputs showed two were unusable (dummy rows such as `ExamplePD01` / `John Doe`, and a blank access-control form) and one was generic but filled in.

**Decision:** Hard flags (fail verification): no agent, never started, no output, empty output, self-reported non-execution, placeholder/dummy content, blank form fields (bullet labels or table cells with no value). Review flag (reported, does not fail): a deliverable named "...Template". Result on that run: engine 3/37 (8.1%), verified 1/37 (2.7%).

**Rationale:** Hard flags are objective defects that we can regression-test; the template name is only a hint, since a task may legitimately ask for one.

**Alternatives considered:** Fail any template-named deliverable (rejected: would have marked the generic-but-filled registry as a failure on name alone).

**Affects:** `src/eval/completion_verifier.py`, `docs/metrics.md`. Limits: heuristics tuned on one run of three completed tasks; false-positive rate unmeasured; unbracketed blanks in prose are only caught in bullet or table form.

## [2026-09-26] metrics.json writer: `constraint_violations` stays null until Fix 6

**Context:** `docs/metrics.md` requires every run to log a fixed schema, but the engine's constraint scores are unreliable (ML-016/033/034).

**Decision:** `src/eval/run_metrics.py` writes `constraint_violations: null` rather than an unreliable figure, validates `condition`, `challenge_task` and `change_depth` against the schema, and logs `verified_completion_rate`, `completion_flags` and `completion_review_flags`.

**Rationale:** A null is honest; a wrong number would look valid in later comparisons.

**Alternatives considered:** Copy the engine's constraint output (rejected: known-broken).

**Affects:** `src/eval/run_metrics.py`, `docs/metrics.md`, Fix 6.

## [2026-09-26] Log decisions as they are made

**Context:** `notes/DECISIONS.md` was empty and `/log-decision` was never used: CLAUDE.md said to read the log but never to write to it, and slash commands only run when invoked.

**Decision:** Added a CLAUDE.md convention to log scoping, architecture, method and convention decisions with `/log-decision` at the time they are made. This file was backfilled from the work between 2026-09-17 and 2026-09-26.

**Rationale:** Decisions and their evidence were only in chat history.

**Alternatives considered:** A hook that prompts at session end (not added; the CLAUDE.md rule is simpler).

**Affects:** `CLAUDE.md`, `notes/DECISIONS.md`.
