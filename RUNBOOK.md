# OMEGA Runbook

## Setup and dependencies

- Python 3.11+.
- No third-party runtime dependency.
- Run commands from `C:\Users\Eng-Mohamed Hasan\Documents\Codex\Impossible-Machine-OMEGA`.

## Start

```powershell
python -m omega.cli --db data/omega.db serve
```

Open `http://127.0.0.1:8787/`. Health: `GET /health`.

## Continuity entry point

```powershell
python -m omega.cli project-status --verify-tests
python -m omega.cli continue
```

The first command performs continuity checks and executes the test suite. The second prints a concise, secret-free execution context.

## Autonomous worker

```powershell
python -m omega.cli supervisor install
python -m omega.cli supervisor start
python -m omega.cli supervisor status
python -m omega.cli supervisor stop
```

The Windows Scheduled Task runs the standalone `python -m omega.runtime.worker` with absolute interpreter, repository, and working-directory paths. Work/Codex is installer-only and does not own the worker lifecycle.

## Verification

```powershell
python -m unittest discover -s tests
python -m omega.cli benchmark
python -m omega.cli release-check
python -m omega.cli --db data/omega-self.db stability-audit
python -m omega.cli --db data/smoke.db demo
```

## Recovery and troubleshooting

- If continuity reports a version mismatch, reconcile `pyproject.toml`, `omega/__init__.py`, `PROJECT_STATE.md`, and `NEXT_TASK.md`; do not choose the older value automatically.
- If the path check fails, return to the canonical path in `PROJECT_STATE.md`; do not clone project state into an ad-hoc folder.
- For database recovery, use the documented `backup` and `restore` CLI commands. Never replace a live database without a backup.
- Inspect `git status` before edits and preserve unrelated working-tree changes.
