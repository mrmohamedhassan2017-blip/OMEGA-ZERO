from __future__ import annotations

import re
import subprocess
import sys
try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]
from pathlib import Path
from typing import Any

from . import __version__


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "PROJECT_STATE.md", "ROADMAP.md", "CHANGELOG.md", "ARCHITECTURE.md",
    "RUNBOOK.md", "NEXT_TASK.md", ".ai/EXECUTOR.md", ".ai/RULES.md", ".ai/VISION.md",
)


def parse_front_matter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read {path.name}: {exc}") from exc
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name} has no metadata front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{path.name} has corrupt metadata front matter")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid metadata line in {path.name}: {line}")
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def repository_versions(root: Path = ROOT) -> dict[str, str]:
    with (root / "pyproject.toml").open("rb") as handle:
        package = str(tomllib.load(handle)["project"]["version"])
    return {"package": package, "runtime": __version__}


def _git(root: Path) -> dict[str, Any]:
    try:
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True,
                                text=True, check=True, timeout=2).stdout.strip()
        changes = subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True,
                                 text=True, check=True, timeout=2).stdout.splitlines()
        return {"available": True, "branch": branch or "detached", "dirty": bool(changes),
                "changed_files": len(changes)}
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return {"available": False, "branch": None, "dirty": None, "changed_files": None}


def inspect_project(root: Path = ROOT, verify_tests: bool = False) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        errors.append("missing continuity files: " + ", ".join(missing))
    try:
        state = parse_front_matter(root / "PROJECT_STATE.md")
    except ValueError as exc:
        state = {}
        errors.append(str(exc))
    try:
        next_task = parse_front_matter(root / "NEXT_TASK.md")
    except ValueError as exc:
        next_task = {}
        errors.append(str(exc))
    try:
        versions = repository_versions(root)
    except (OSError, KeyError, ValueError) as exc:
        versions = {}
        errors.append(f"cannot determine repository version: {exc}")
    version_values = {value for value in (*versions.values(), state.get("version", "")) if value}
    if len(version_values) != 1:
        errors.append("version mismatch: " + ", ".join(f"{k}={v}" for k, v in {**versions, "state": state.get("version", "missing")}.items()))
    baseline = next_task.get("baseline_version")
    if baseline and state.get("version") and baseline != state["version"]:
        errors.append(f"NEXT_TASK baseline {baseline} is stale; current state is {state['version']}")
    canonical = state.get("canonical_path")
    if canonical and Path(canonical).resolve() != root:
        errors.append(f"canonical path mismatch: state={canonical}; actual={root}")
    git = _git(root)
    if git["dirty"]:
        warnings.append(f"working tree has {git['changed_files']} changed file(s); preserve existing work")
    tests: dict[str, Any] = {"mode": "recorded", "result": state.get("test_result", "unknown"),
                             "last_verified": state.get("last_verified", "unknown")}
    if verify_tests:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=180)
        count = re.search(r"Ran (\d+) tests?", completed.stderr + completed.stdout)
        tests = {"mode": "executed", "passed": completed.returncode == 0,
                 "count": int(count.group(1)) if count else None, "returncode": completed.returncode}
        if completed.returncode:
            errors.append("test verification failed")
    return {"path": str(root), "version": state.get("version") or versions.get("package", "unknown"),
            "state": state.get("status", "unknown"), "last_verified": state.get("last_verified", "unknown"),
            "current_milestone": state.get("current_milestone", "unknown"),
            "next_milestone": next_task.get("milestone") or state.get("next_milestone", "unknown"),
            "git": git, "tests": tests, "missing": missing, "errors": errors, "warnings": warnings,
            "continuity": "OK" if not errors else "FAILED", "ready_to_continue": not errors}


def format_status(result: dict[str, Any]) -> str:
    git = result["git"]
    git_text = "unavailable" if not git["available"] else f"{git['branch']} / {'dirty' if git['dirty'] else 'clean'}"
    tests = result["tests"]
    tests_text = (f"EXECUTED: {'PASS' if tests.get('passed') else 'FAIL'} ({tests.get('count', '?')} tests)"
                  if tests["mode"] == "executed" else f"RECORDED: {tests['result']} at {tests['last_verified']}")
    issues = result["errors"] + result["warnings"]
    lines = ["OMEGA PROJECT STATUS", "", f"Path: {result['path']}", f"Version: {result['version']}",
             f"State: {result['state']}", f"Git: {git_text}", f"Tests: {tests_text}",
             f"Last verified: {result['last_verified']}", "", f"Current milestone: {result['current_milestone']}",
             f"Next milestone: {result['next_milestone']}", f"Known blockers: {'; '.join(issues) if issues else 'none'}", "",
             f"CONTINUITY: {result['continuity']}", f"READY TO CONTINUE: {'YES' if result['ready_to_continue'] else 'NO'}"]
    return "\n".join(lines)


def execution_context(root: Path = ROOT) -> str:
    result = inspect_project(root)
    state_text = (root / "PROJECT_STATE.md").read_text(encoding="utf-8")
    next_text = (root / "NEXT_TASK.md").read_text(encoding="utf-8")
    architecture = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    return "\n\n".join((format_status(result), "NEXT TASK\n" + next_text[:4000],
                          "ARCHITECTURE SUMMARY\n" + architecture[:2500],
                          "RECENT CHANGELOG\n" + changelog[:2000],
                          "STATE NOTES\n" + state_text[:3000]))
