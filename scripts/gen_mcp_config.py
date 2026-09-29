#!/usr/bin/env python3
"""Generate one combined `mcpServers` config for every tools/*/ server.

Reads each tools/*/manifest.json (entry_point, name), so a newly added tool
appears automatically. Optionally sets CLAUDE_TOOLS_USAGE_LOG on every entry
so usage-telemetry has data to read.

    python3 scripts/gen_mcp_config.py                      # print JSON
    python3 scripts/gen_mcp_config.py --usage-log ~/.claude-tools/usage.jsonl
    python3 scripts/gen_mcp_config.py --check              # verify the
        # generated servers each start and answer list_tools (needs `mcp`)
"""
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(root=ROOT, usage_log=None, python="python3"):
    servers = {}
    for manifest in sorted((root / "tools").glob("*/manifest.json")):
        m = json.loads(manifest.read_text())
        entry = m.get("entry_point")
        if not entry or not m.get("tools_exposed"):
            continue  # not an MCP server (e.g. collection-index CLI)
        cfg = {"command": python, "args": [str(manifest.parent / entry)]}
        if usage_log:
            cfg["env"] = {"CLAUDE_TOOLS_USAGE_LOG": usage_log}
        servers[m["name"]] = cfg
    return {"mcpServers": servers}


def check(config):
    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def one(name, cfg):
        p = StdioServerParameters(command=cfg["command"], args=cfg["args"],
                                  env={**os.environ, **cfg.get("env", {})})
        async with stdio_client(p) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                return len((await s.list_tools()).tools)

    bad = 0
    for name, cfg in config["mcpServers"].items():
        try:
            print(f"ok   {name}: {asyncio.run(one(name, cfg))} tools")
        except Exception as e:  # noqa: BLE001
            bad += 1
            print(f"FAIL {name}: {e!r}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--usage-log", help="path to set as CLAUDE_TOOLS_USAGE_LOG")
    ap.add_argument("--python", default="python3")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    cfg = build(usage_log=a.usage_log and os.path.expanduser(a.usage_log),
                python=a.python)
    if a.check:
        return 1 if check(cfg) else 0
    print(json.dumps(cfg, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
