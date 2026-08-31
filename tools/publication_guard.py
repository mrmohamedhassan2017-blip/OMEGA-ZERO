"""Fail-closed publication boundary guard for the public OMEGA/ZERO repository."""

from __future__ import annotations

import argparse
import enum
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


class PublicationClass(str, enum.Enum):
    PUBLIC_SOURCE = "PUBLIC_SOURCE"
    PUBLIC_DOC = "PUBLIC_DOC"
    PUBLIC_TEST = "PUBLIC_TEST"
    PUBLIC_FIXTURE = "PUBLIC_FIXTURE"
    PUBLIC_GENERATED_SAFE = "PUBLIC_GENERATED_SAFE"
    PRIVATE_RUNTIME = "PRIVATE_RUNTIME"
    PRIVATE_EVIDENCE = "PRIVATE_EVIDENCE"
    PRIVATE_HOST_STATE = "PRIVATE_HOST_STATE"
    PRIVATE_IDENTITY = "PRIVATE_IDENTITY"
    SECRET = "SECRET"
    UNKNOWN = "UNKNOWN"


DENIED = {
    PublicationClass.PRIVATE_RUNTIME,
    PublicationClass.PRIVATE_EVIDENCE,
    PublicationClass.PRIVATE_HOST_STATE,
    PublicationClass.PRIVATE_IDENTITY,
    PublicationClass.SECRET,
    PublicationClass.UNKNOWN,
}

SECRET_INDICATORS = (
    ".env",
    ".dpapi",
    "oauth",
    "credential",
    "credentials",
    "token",
    "secret",
    "refresh",
    "private-key",
    "private_key",
)


@dataclass(frozen=True)
class GuardFinding:
    path: str
    classification: PublicationClass
    reason: str
    git_status: str = ""

    @property
    def blocked(self) -> bool:
        if self.git_status == "D":
            return False
        return self.classification in DENIED


def normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def classify_path(path: str) -> tuple[PublicationClass, str]:
    normalized = normalize_path(path)
    lowered = normalized.lower()
    parts = PurePosixPath(normalized).parts
    basename = parts[-1].lower() if parts else lowered

    if any(indicator in lowered for indicator in SECRET_INDICATORS):
        return PublicationClass.SECRET, "secret-shaped path"

    if lowered.startswith(".omega/"):
        if any(marker in lowered for marker in ("heartbeat", "checkpoint", "journal", "lock", "runtime", "session")):
            return PublicationClass.PRIVATE_RUNTIME, ".omega runtime/checkpoint state"
        if any(marker in lowered for marker in ("evidence", "evaluation", "experiment", "avf", "zero", "economic")):
            return PublicationClass.PRIVATE_EVIDENCE, ".omega evidence/experiment state"
        return PublicationClass.PRIVATE_HOST_STATE, ".omega host/runtime state"

    if lowered.startswith("data/"):
        return PublicationClass.PRIVATE_HOST_STATE, "local generated data"

    if lowered.startswith(("omega/", "agent_runtime_audit/", "src/agent_runtime_audit/")) and lowered.endswith(".py"):
        return PublicationClass.PUBLIC_SOURCE, "source code"

    if lowered.startswith("omega/web/") and lowered.endswith((".html", ".css", ".js", ".svg", ".json")):
        return PublicationClass.PUBLIC_DOC, "public web UI asset"

    if lowered.startswith("tests/") and lowered.endswith(".py"):
        return PublicationClass.PUBLIC_TEST, "test code"

    if lowered.startswith(("docs/", "experiments/")) and not lowered.endswith((".db", ".sqlite", ".sqlite3")):
        return PublicationClass.PUBLIC_DOC, "public documentation or public experiment contract"

    if lowered.startswith(".github/") and not any(indicator in lowered for indicator in SECRET_INDICATORS):
        return PublicationClass.PUBLIC_GENERATED_SAFE, "GitHub public metadata"

    if basename in {
        ".gitignore",
        "readme.md",
        "changelog.md",
        "progress.md",
        "project_state.md",
        "publication_boundary.md",
        "public-boundary.json",
        "pyproject.toml",
    }:
        return PublicationClass.PUBLIC_DOC, "top-level public project metadata"

    if lowered.startswith("tools/") and lowered.endswith(".py"):
        return PublicationClass.PUBLIC_SOURCE, "repository tooling source"

    return PublicationClass.UNKNOWN, "not classified as public-safe"


def evaluate_paths(paths: Iterable[str], statuses: dict[str, str] | None = None) -> list[GuardFinding]:
    findings: list[GuardFinding] = []
    statuses = statuses or {}
    for path in paths:
        normalized = normalize_path(path)
        classification, reason = classify_path(normalized)
        findings.append(GuardFinding(normalized, classification, reason, statuses.get(normalized, "")))
    return findings


def staged_paths() -> tuple[list[str], dict[str, str]]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff --cached failed")
    paths: list[str] = []
    statuses: dict[str, str] = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0][:1]
        path = normalize_path(fields[-1])
        paths.append(path)
        statuses[path] = status
    return paths, statuses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate staged public repository changes.")
    parser.add_argument("--staged", action="store_true", help="check git staged paths")
    parser.add_argument("paths", nargs="*", help="explicit paths to classify")
    args = parser.parse_args(argv)

    if args.staged:
        paths, statuses = staged_paths()
    else:
        paths, statuses = args.paths, {}

    findings = evaluate_paths(paths, statuses)
    blocked = [finding for finding in findings if finding.blocked]
    for finding in findings:
        state = "BLOCK" if finding.blocked else "ALLOW"
        print(f"{state}\t{finding.classification.value}\t{finding.git_status}\t{finding.path}\t{finding.reason}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
