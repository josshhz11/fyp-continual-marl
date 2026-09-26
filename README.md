# Continual Multi-Agent Workflow Orchestration

A Final Year Project studying how a frozen-LLM manager agent can adapt to shifting stakeholder preferences and changing team composition in multi-agent workflow orchestration, without retraining — see [docs/proposal.md](docs/proposal.md) for the canonical spec.

## Setting up `external/manager_agent_gym`

`external/manager_agent_gym` is a **git submodule**: a full, separate clone of
[josshhz11/manager_agent_gym](https://github.com/josshhz11/manager_agent_gym)
(our fork of the official MA-Gym), on the branch `fyp/ma-gym-fixes`. This repo
does not store its code, only a **pointer** to one exact commit of the fork. So
`git pull` on this repo does not move the submodule by itself; you also have to
update it (see below). The fixes we are making to MA-Gym are tracked in
[external/manager_agent_gym/fixes/PROPOSED_FIXES_SUMMARY.md](external/manager_agent_gym/fixes/PROPOSED_FIXES_SUMMARY.md).

Requirements: [git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/) and
an OpenAI API key (only needed to run workflows, not to run the tests).

### First-time setup (new machine)

```bash
git clone --recurse-submodules https://github.com/josshhz11/fyp-continual-marl.git
cd fyp-continual-marl
```

Already cloned without `--recurse-submodules`, or the folder is empty?

```bash
git submodule update --init --recursive
```

Then set up the MA-Gym environment (these two are **not** in git, so you
recreate them on every machine):

```bash
cd external/manager_agent_gym
cp .env.example .env        # then edit .env: OPENAI_API_KEY=sk-...  (no quotes, no repeated name)
uv sync --group agents --group openai
```

Check it works:

```bash
# from external/manager_agent_gym
uv run --group agents --group openai pytest tests -m "not integration" -q

# from the repo root
PYTHONPATH=src uv run --no-project --with pytest pytest tests -q
```

`git submodule status` should show one line starting with a space (a `-` means
not initialized, a `+` means it is on a different commit than this repo expects).

### Getting the latest changes (every time you sit down at another machine)

The submodule has two layers, so update both, in this order:

```bash
git switch main                       # or the branch you are working on
git pull                              # 1. this repo: code, docs and the new submodule pointer
git submodule sync external/manager_agent_gym      # 2. only matters if .gitmodules changed (e.g. the URL)
git submodule update --init --recursive            # 3. check out the commit this repo points to
```

Tip: `git config submodule.recurse true` makes `git pull` and `git switch` update
submodules too, so step 3 happens automatically.

After step 3 the submodule sits on a **detached HEAD** at the pinned commit.
That is normal. To work on it (or to be on the newest fork commit, which may be
ahead of the pinned one until the pointer bump is merged here):

```bash
cd external/manager_agent_gym
git fetch origin
git switch fyp/ma-gym-fixes
git pull origin fyp/ma-gym-fixes
```

### Making a change to MA-Gym (the machine you are working on)

Order matters: push the **submodule first**, then update the pointer here.
Otherwise other machines are told to fetch a commit that only exists on yours.

```bash
# 1. inside the submodule, on fyp/ma-gym-fixes: one commit per fix
cd external/manager_agent_gym
git switch fyp/ma-gym-fixes && git pull origin fyp/ma-gym-fixes   # start from the latest
# ...edit, run the tests, then:
git add <files>
git commit -m "fix(scope): summary"
git push origin fyp/ma-gym-fixes                                    # push this BEFORE step 2

# 2. back in this repo, on a dated branch, record the new pointer
cd ../..
git switch -c <type>/<YY>.<MM>_<slug>
git add external/manager_agent_gym
git commit -m "chore: bump manager_agent_gym submodule for <what changed>"
git push -u origin <type>/<YY>.<MM>_<slug>                          # then open a PR and merge into main
```

Other machines then follow "Getting the latest changes" above.

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `external/manager_agent_gym` is empty | Never initialized: `git submodule update --init --recursive`. |
| No `fixes/` folder, or old code | The submodule is on an old commit or still points at the official repo. Run `git pull`, `git submodule sync external/manager_agent_gym`, `git submodule update --init`. Then check `git -C external/manager_agent_gym remote -v` shows `josshhz11`. |
| `fatal: ... did not contain <sha>` | That commit was never pushed to the fork. On the machine that made it: `cd external/manager_agent_gym && git push origin fyp/ma-gym-fixes`. |
| `git status` shows `modified: external/manager_agent_gym (new commits)` | The submodule is on a different commit than this repo records. To reset it: `git submodule update`. To keep it, commit the new pointer as above. |
| `ModuleNotFoundError: agents` when running tests | Missing dependency groups: use `uv run --group agents --group openai ...`. |
| API key errors (401) | Check `.env` is exactly `OPENAI_API_KEY=sk-...` (the variable name must not appear inside the value). |
| Redirecting run output on Windows crashes on an emoji | Set `PYTHONUTF8=1` first. |

Not synced by git, so recreate or copy per machine: `.env`, `.venv`, and run
outputs (keep them outside the repo, e.g. `--output-dir ../fyp-smoke`).
`external/ergon/` is a plain local clone, not a submodule, so it is not part of
this repo either.
