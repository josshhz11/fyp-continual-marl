# MA-Gym Problems vs. Ergon: A Plain-Language Evaluation

Source material: `magym-undocumented-behaviour - Critical and High bugs.csv`
(the supervisor's group's audit of `external/manager_agent_gym`), plus a
direct read of the code and docs in `external/manager_agent_gym` and
`external/ergon` as cloned into this repo.

This is a general evaluation of MA-Gym's problems and how Ergon (its
proposed successor) addresses them — not scoped to this project's specific
challenge tasks or metrics design. Written in plain terms.

## MA-Gym's problems, in plain terms

Grouping the 32 audited bugs into five themes — this is what anyone using
MA-Gym as-is should know, regardless of what their project is about:

### 1. "Task completed" doesn't mean the work actually happened

The engine marks a task `COMPLETED` just because the worker's function call
didn't crash — it never checks whether the output is actually any good. In
practice this let through unfilled templates (`[Date]`,
`"Seller Legal Name"`), tasks marked done with zero output and no assigned
worker, and tasks the worker itself said it didn't execute. Result: the
audit measured 42–66% of "completed" handoffs as actually inadequate,
while the tool reports ~100% completion. **The headline success number
lies.**

### 2. Workers never actually see each other's work

The mechanism meant to pass one worker's output to the next worker was
never wired up — across all 20 official example runs, 0% of tasks ever
received input from a predecessor. Every "workflow" that looks like a
pipeline is actually a set of independent tasks running in parallel with
no real handoff between them. This is the single worst bug — it means the
core thing MA-Gym claims to simulate (a team coordinating on shared work)
has never actually been exercised in any published result.

### 3. The scoring system (the "judge") is broken in many independent ways

An AI model grades how well each task was done, but: it only ever sees a
300-character preview of each artifact (so it's grading a snippet, not the
real deliverable); several of its scoring formulas are dead code that
silently fall back to a different, more forgiving formula; some entire
scoring categories always return zero no matter what; the judge is
sometimes blind to the exact evidence (messages, task history) it's
supposed to be looking at; and re-running the same grading twice on
identical input can flip a score from 1.0 to 0.0. **You cannot trust a
"condition A beat condition B" claim from this scoring pipeline without
independent verification.**

### 4. Runs aren't reproducible

Setting the same random seed twice gives meaningfully different runs (up
to double the number of actions taken). Any two "identical" experiments
are actually two different, uncontrolled experiments — this undermines any
comparison that depends on holding conditions constant.

### 5. Saved/archived runs can't be reliably replayed or trusted

Restoring a saved run drops tasks, descriptions, and scoring
configuration; by default the tool doesn't even save enough detail to
re-score an old run without paying to re-run the whole thing from scratch;
and only the last 10 messages of a conversation are ever saved, so most
communication history is lost forever.

## What Ergon does about each of these

| Problem | Ergon's status | Evidence |
|---|---|---|
| **Fake completion / no quality check** | **Not addressed** that could be found | No doc or RFC targets this specifically |
| **No real handoff between workers** | **Fixed, and well-designed** | Old broken mechanism was deleted outright and replaced with a real system: workers write files to a proper storage location, get a unique ID, and the next worker reads them back by name — with the old "silent data loss" bug no longer being *possible* to reintroduce (`docs/architecture/cross_cutting/artifacts.md`) |
| **300-char judge preview** | **Fixed, in at least one place** | A 2026-04-28 implementation plan (`docs/superpowers/plans/2026-04-28-evaluation-resource-context-and-scoring.md`) makes the judge read up to 30,000 real characters of the actual final output instead of a fixed 300-char snippet — but so far this is built for one specific evaluator type (ResearchRubrics), not proven to apply everywhere yet |
| **Dead/broken scoring formulas, always-zero categories** | **Partially — a different but related bug already found and still open** | Ergon's own internal audit (`docs/integration-spec/4-violated-assumptions.md`, item I) already found "a completed run can show zero scores with no warning that anything went wrong" — same *shape* of silent-failure bug, not yet fixed |
| **Judge blind to the real evidence it's supposed to see** | **Partially fixed, partially still open** | Fixed for one evaluator (now reads real files). But Ergon's own audit *also* found a live case (item C) where the evaluator is currently given an empty/blank task description instead of the real one — same category of bug, different spot, unfixed |
| **Reproducibility (seeds don't work)** | **No evidence found either way** | No Ergon document addressing seeding/reproducibility was found |
| **Archived runs can't be faithfully replayed** | **No evidence found either way** | No doc found addressing snapshot/restore fidelity |
| **Ergon's own reliability** | **Worth knowing** | Ergon's own test-coverage audit (`docs/integration-spec/1-audit.md`) found 3 tests that have never actually run (a `testresolve_*` vs `test_*` typo hid them from the test runner since they were written), and most of its "integration tests" are actually fully fake/mocked |

## Bottom line, simply put

Ergon fixes the single worst problem (workers never seeing each other's
real output) properly — not a patch, an actual redesign, with the old
broken path deleted so it can't come back by accident. It's also making
real progress on the judge-only-sees-a-snippet problem, at least in the
one place it's been applied so far.

But it hasn't touched two of MA-Gym's other big problems (completion being
a fake quality signal, and reproducibility), and — this is the important
part — **its own internal documentation already lists new bugs of the
exact same shape** as MA-Gym's worst ones (silent zero-scores with no
warning, evaluators being fed the wrong/empty data). So it's not "solved,
evaluation is broken," it's "fixed some, found more of the same kind,
hasn't fixed those yet." It's also simply younger and less tested than
MA-Gym — its own audit says as much.
