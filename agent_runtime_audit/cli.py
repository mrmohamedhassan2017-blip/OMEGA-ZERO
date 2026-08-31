from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_agent_events, render_html


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Audit agent-runtime lifecycle events locally.")
    result.add_argument("events", type=Path)
    result.add_argument("--json-out", type=Path, required=True)
    result.add_argument("--html-out", type=Path, required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    events: list[dict[str, object]] = []
    for line in args.events.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    report = audit_agent_events(events)
    for output in (args.json_out, args.html_out):
        if output.exists():
            raise FileExistsError(f"refusing to overwrite report: {output}")
    args.json_out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.html_out.write_text(render_html(report), encoding="utf-8")
    print(json.dumps({"assessment": report["assessment"]}, indent=2))


if __name__ == "__main__":
    main()
