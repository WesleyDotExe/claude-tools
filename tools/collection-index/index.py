#!/usr/bin/env python3
"""Foundational tool: reads tools/*/manifest.json and reports the collection.

This is the first thing the standing "MCP connectors and tools" project
builds (see TASKS.md), because everything after it -- the dashboard, and
any future tool that wants to know what already exists before building
something overlapping -- depends on a single, trustworthy read of what's
in tools/. Stdlib only.

Usage:
    python3 index.py                # human-readable table on stdout
    python3 index.py --json         # machine-readable, for other scripts
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ("name", "summary", "problem", "keyless", "created")
TOOLS_DIR = Path(__file__).resolve().parent.parent


def collect(tools_dir: Path = TOOLS_DIR) -> list[dict]:
    """Read every tools/<name>/manifest.json and return them sorted by name.

    A manifest missing a required field is skipped with a note on stderr
    rather than crashing the whole scan -- one broken tool shouldn't take
    down the index for every other tool.
    """
    entries = []
    for manifest_path in sorted(tools_dir.glob("*/manifest.json")):
        tool_dir = manifest_path.parent
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"skipping {manifest_path}: invalid JSON ({exc})", file=sys.stderr)
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            print(f"skipping {manifest_path}: missing fields {missing}", file=sys.stderr)
            continue
        data["path"] = str(tool_dir.relative_to(tools_dir.parent))
        entries.append(data)
    entries.sort(key=lambda d: d["name"])
    return entries


def render_table(entries: list[dict]) -> str:
    if not entries:
        return "(no tools in the collection yet)"
    lines = [f"{len(entries)} tool(s) in the collection:", ""]
    for e in entries:
        lines.append(f"- {e['name']}  ({e['path']}, created {e['created']})")
        lines.append(f"    solves: {e['summary']}")
    return "\n".join(lines)


def main() -> None:
    entries = collect()
    if "--json" in sys.argv:
        print(json.dumps(entries, indent=2))
    else:
        print(render_table(entries))


if __name__ == "__main__":
    main()
