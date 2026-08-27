from __future__ import annotations

from html import escape
from typing import Any


REQUIRED_EVENTS = {
    "AGENT_STARTED",
    "AGENT_COMPLETED",
    "CHANGES_DETECTED",
    "HOST_TEST_STARTED",
    "HOST_TEST_PASSED",
}


def audit_agent_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize lifecycle event names without retaining raw input payloads."""
    names = [str(item.get("event", "UNKNOWN")) for item in events]
    counts = {name: names.count(name) for name in sorted(set(names))}
    missing = sorted(REQUIRED_EVENTS - set(names))
    findings: list[str] = []
    if names.count("AGENT_STARTED") > names.count("AGENT_COMPLETED"):
        findings.append("agent execution without matching completion")
    if "HOST_TEST_STARTED" in names and not {
        "HOST_TEST_PASSED",
        "HOST_TEST_FAILED",
    }.intersection(names):
        findings.append("host verification started without terminal result")
    if "HARD_BLOCKER" in names:
        findings.append("hard blocker recorded; inspect protected source log locally")
    return {
        "format": "omega.agent-runtime-audit",
        "format_version": 1,
        "event_count": len(events),
        "event_counts": counts,
        "required_lifecycle_events_missing": missing,
        "findings": findings,
        "raw_payloads_included": False,
        "credentials_included": False,
        "assessment": "REVIEW" if findings or missing else "PASS",
        "limitations": [
            "event logs do not prove process ownership",
            "absence of an event is not proof an action did not occur",
        ],
    }


def render_html(report: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{escape(str(name))}</td><td>{int(count)}</td></tr>"
        for name, count in report["event_counts"].items()
    )
    findings = "".join(
        f"<li>{escape(str(item))}</li>"
        for item in report["findings"] + report["limitations"]
    )
    assessment = escape(str(report["assessment"]))
    return (
        "<!doctype html><meta charset='utf-8'><title>Agent Runtime Audit</title>"
        "<style>body{font:16px system-ui;max-width:850px;margin:40px auto;padding:0 18px}"
        "table{border-collapse:collapse}td{padding:7px 14px;border:1px solid #ccc}"
        ".PASS{color:#087}.REVIEW{color:#b50}</style>"
        f"<h1>Agent Runtime Audit</h1><h2 class='{assessment}'>{assessment}</h2>"
        f"<p>{int(report['event_count'])} events analyzed. Raw payloads and credentials excluded.</p>"
        f"<table>{rows}</table><h3>Findings and limits</h3><ul>{findings}</ul>"
    )
