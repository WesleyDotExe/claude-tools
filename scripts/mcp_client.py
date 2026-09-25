"""A small, reusable harness for driving one of this repo's MCP servers over
stdio and collecting typed results -- the "drive an MCP server over stdio and
collect typed results" tool called for in special-projects/wishlist.md's
[mcp-proof] entry.

Every cycle that builds or extends an MCP server here has to write a
throwaway stdio client script to prove it actually works (not just that it
scaffolds), and re-discovers the same footgun each time: `mcp`'s
`CallToolResult` returns typed output in `structured_content` *when the
tool's return type annotation supports it*, but many results (plain
strings, or older/untyped tools) only come back in the text content block,
which then has to be parsed as JSON by hand. This module does that
extraction once, so future proof scripts (and this repo's own test/example
runs) can import it instead of re-deriving it.

Library use:

    from mcp_client import run_calls

    results = asyncio.run(run_calls("tools/secure-random/server.py", [
        {"label": "list tools", "tool": "list_tools"},
        {"label": "roll 2d6+3", "tool": "roll_dice", "args": {"notation": "2d6+3"}},
    ]))
    # results is a list of {"label": ..., "ok": True, "value": <typed result>}
    # (or {"label": ..., "ok": False, "error": "<message>"} for a tool error)

CLI use:

    python3 scripts/mcp_client.py list-tools tools/secure-random/server.py
    python3 scripts/mcp_client.py call tools/secure-random/server.py roll_dice '{"notation": "2d6+3"}'
    python3 scripts/mcp_client.py run tools/secure-random/server.py calls.json [--out proof.txt]

`run`'s calls.json is a JSON list of objects: {"label": str, "tool": str,
"args": dict (optional, omit or {} for a no-arg tool)}. The special tool
name "list_tools" (args ignored) lists the server's tool names instead of
calling one. Output is printed (and, with --out, written) in the same
"--- label ---\\n<value>" shape this repo's existing proof/run_*.txt files
already use, so `run` can replace the one-off script most cycles wrote by
hand.

Requires `mcp` (see scripts/mcp_dev_setup.sh for the one-shot preflight).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _extract(result: Any) -> Any:
    """Pull the typed value out of a CallToolResult.

    Prefers `structured_content` (present when the tool's return type
    annotation lets the MCP SDK generate a JSON schema for it). Falls back
    to parsing the text content block(s) as JSON, which is what a plain
    `str`-returning tool, or an older/untyped one, actually produces.
    """
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured

    blocks = list(getattr(result, "content", []) or [])
    texts = [b.text for b in blocks if getattr(b, "type", None) == "text"]
    if not texts:
        return None
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except json.JSONDecodeError:
            return texts[0]
    # Multiple text blocks: the SDK does this for some list-typed returns
    # when structured_content isn't available. Try to recover a list.
    parsed = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except json.JSONDecodeError:
            parsed.append(t)
    return parsed


def _error_text(result: Any) -> str:
    blocks = list(getattr(result, "content", []) or [])
    texts = [b.text for b in blocks if getattr(b, "type", None) == "text"]
    return "\n".join(texts) if texts else "(no error text)"


async def run_calls(
    server_path: str, calls: list[dict[str, Any]], python: str | None = None
) -> list[dict[str, Any]]:
    """Drive `server_path` over stdio for the whole session, executing
    `calls` in order against one shared ClientSession (matching how a real
    MCP client talks to a server: one initialize, many calls).
    """
    params = StdioServerParameters(command=python or sys.executable, args=[server_path])
    results: list[dict[str, Any]] = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for call in calls:
                label = call.get("label", call.get("tool", "?"))
                tool = call["tool"]
                if tool == "list_tools":
                    tools = await session.list_tools()
                    results.append(
                        {"label": label, "ok": True, "value": [t.name for t in tools.tools]}
                    )
                    continue
                args = call.get("args", {}) or {}
                result = await session.call_tool(tool, args)
                if getattr(result, "is_error", False):
                    results.append({"label": label, "ok": False, "error": _error_text(result)})
                else:
                    results.append({"label": label, "ok": True, "value": _extract(result)})
    return results


def _format_results(results: list[dict[str, Any]]) -> str:
    lines = []
    for r in results:
        lines.append(f"--- {r['label']} ---")
        if r["ok"]:
            value = r["value"]
            lines.append(
                json.dumps(value, indent=2) if not isinstance(value, str) else value
            )
        else:
            lines.append(f"ERROR: {r['error']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _cli() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command, server_path = sys.argv[1], sys.argv[2]

    if command == "list-tools":
        calls = [{"label": "list_tools", "tool": "list_tools"}]
    elif command == "call":
        if len(sys.argv) < 4:
            print("usage: mcp_client.py call <server.py> <tool_name> ['<json_args>']")
            sys.exit(1)
        tool_name = sys.argv[3]
        args = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        calls = [{"label": tool_name, "tool": tool_name, "args": args}]
    elif command == "run":
        if len(sys.argv) < 4:
            print("usage: mcp_client.py run <server.py> <calls.json> [--out <file>]")
            sys.exit(1)
        calls = json.loads(Path(sys.argv[3]).read_text())
    else:
        print(f"unknown command: {command}")
        print(__doc__)
        sys.exit(1)

    results = asyncio.run(run_calls(server_path, calls))
    output = _format_results(results)
    print(output, end="")

    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        out_path.write_text(output)

    if any(not r["ok"] for r in results) and command != "run":
        sys.exit(1)


if __name__ == "__main__":
    _cli()
