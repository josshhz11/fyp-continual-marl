---
description: Refresh statuses, change summaries and remaining-verification lists in external/manager_agent_gym/fixes/PROPOSED_FIXES_SUMMARY.md
---

Update `external/manager_agent_gym/fixes/PROPOSED_FIXES_SUMMARY.md` so every
fix and phase reflects what has actually been done. Optional argument: a fix
number (e.g. `1`) to update only that fix and its phase.

## Step 1 - Gather evidence (never rely on the chat conversation or memory)

Run inside `external/manager_agent_gym`:
- `git status --short` and `git log --oneline 3f7a5d4..HEAD` - what has been
  committed on `fyp/ma-gym-fixes` since the pinned upstream commit, and what
  is still uncommitted.
- `git show --stat <sha>` for each fix commit, to see which files it touched.
- `uv run --group agents --group openai pytest tests -m "not integration" -q`
  - current suite result. Record pass/fail/skip counts.
- Any test file added for a fix (named in that fix's section): run it on its
  own and record the result.

Also run `git log --oneline -5` at the repo root to see whether the submodule
pointer bump has landed in the parent repo.

## Step 2 - Update each fix section (Fix 1 to Fix 8)

Every fix section must contain, in this order, directly under its heading:
- `**Status:**` - exactly one of: `Not started`, `In progress`,
  `Complete (unit-verified)`, `Complete (verified end-to-end)`, `Blocked`.
  Add a short qualifier after `;` if something is outstanding. Append
  `(optional)` for Fix 7 and Fix 8 while they are optional.

And at the end of the fix's block (after its DoD checklist):
- `**Summary of Changes Done:**` - bullets naming the actual files/functions
  changed and the evidence (tests added, before/after results, commit
  message). `- None yet.` if nothing has been done.
- `**What's left to verify:**` - bullets for every unchecked DoD item, plus
  any risk or assumption found while implementing that has not been checked.
  Do not leave it empty for a fix that is not verified end-to-end.

Rules:
- Tick a DoD box (`[x]`) only if you saw the evidence this run (a passing
  test, a diff, a log). Otherwise leave it `[ ]`.
- Choose the status from the evidence:
  - `Complete (unit-verified)` - code merged into the branch, its tests pass,
    but an end-to-end DoD item is still unchecked.
  - `Complete (verified end-to-end)` - every DoD box is ticked.
  - `In progress` - some code or tests exist but not all DoD items that
    can be unit-tested are done.
- If a test now fails, or the suite regressed against the last recorded
  count, set the status to `Blocked` (or `In progress`) and say why in
  "What's left to verify" - do not paper over it.
- Do not change a fix's "Where / Root cause / Proposed fix" text unless the
  implementation showed it was wrong; if so, correct it and mention the
  correction under "Summary of Changes Done".

## Step 3 - Update each phase status

Under each `### Phase X` heading, set `**Status:**` from its fixes: `Not
started` if none are, `Complete` if all non-optional fixes are complete,
otherwise `In progress - <one-line breakdown per fix>`. Optional fixes
(7, 8) do not block a phase from being `Complete`.

## Step 4 - Housekeeping

- Set the `**Last updated:**` line to today's date (from the system date).
- Keep the file UTF-8 and preserve its existing line endings.
- Do not commit, stage or push. Finish by telling the user which statuses
  changed, and that committing this doc inside the submodule (and bumping the
  parent pointer) is left to `/commit-pr`.
