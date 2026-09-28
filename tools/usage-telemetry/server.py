"""MCP server exposing telemetrykit's usage-log reader.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet, and for
how to turn logging on across the other servers in this collection.
"""
from mcp.server.mcpserver import MCPServer

import telemetrykit
from telemetrykit import track

server = MCPServer(
    name="usage-telemetry",
    instructions=(
        "Reads the opt-in local call log the other MCP servers in this "
        "collection append to (tool name, timestamp, ok/error -- never "
        "payloads) when CLAUDE_TOOLS_USAGE_LOG is set. Use read_usage_summary "
        "to answer 'has this tool actually been called since it shipped?' "
        "with real per-server, per-tool counts instead of guessing from "
        "whether the code still exists. Use tail_usage_events to see the "
        "most recent raw invocations, e.g. while debugging why a count "
        "looks off. If no log path is configured and none is passed in, "
        "both tools report that logging is off rather than erroring."
    ),
)


@server.tool()
@track("usage-telemetry")
def read_usage_summary(log_path: str | None = None) -> dict:
    """Aggregate the usage log into per-server, per-tool invocation counts.

    Reads `log_path` if given, else the CLAUDE_TOOLS_USAGE_LOG env var this
    process was started with. Returns total_invocations, ok/error counts
    per server and per tool, first_seen/last_seen timestamps, and
    malformed_lines (log lines that didn't parse, e.g. from manual editing).
    A missing or unset log isn't an error -- it just means nothing has been
    recorded (or opted in) yet, reported as exists=false.
    """
    return telemetrykit.summarize(log_path)


@server.tool()
@track("usage-telemetry")
def tail_usage_events(n: int = 20, log_path: str | None = None) -> list:
    """The last `n` well-formed usage-log entries, most recent first.

    Each entry is `{ts, server, tool, ok, error?}`. Useful for spot-checking
    what actually got logged (e.g. right after a live proof session) before
    trusting `read_usage_summary`'s aggregate counts.
    """
    return telemetrykit.tail(n, log_path)


if __name__ == "__main__":
    server.run(transport="stdio")
