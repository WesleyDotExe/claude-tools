# usage-telemetry

An MCP server that reads a local, opt-in call log — one JSON line per
invocation, `{tool name, timestamp, ok/error}`, never payloads — that every
other server in this collection can now append to, and aggregates it into
real per-server, per-tool invocation counts.

## What it solves

TASKS.md's build loop has a step ("check usage") that asks whether prior
tools have actually been called since they shipped — a build cycle is
supposed to use that to decide what to harden versus what to retire. Until
this tool, nothing in this repo could answer it: there was no telemetry, no
log, no callback from an external MCP client back into this repo. Every
prior cycle's log either skipped the step or, at best, restated that the
collection-index/manifest counts were unchanged, which shows a tool still
*exists*, not that anything *called* it (`progress/quality-debt.md`'s
standing note on this, since 2026-09-25).

This closes it with the simplest thing that's actually true: a plain JSONL
file, written only when a caller explicitly turns it on, and a second MCP
server whose whole job is reading that file back into counts.

## Design

- **Opt-in, not default-on.** Nothing writes anywhere unless
  `CLAUDE_TOOLS_USAGE_LOG` is set (or a `log_path` is passed explicitly) —
  set it in your MCP client config once, across every server entry, and
  every tool call from every server in this collection lands in the same
  file. Leave it unset and the collection behaves exactly as before: no
  file, no I/O, nothing to clean up.
- **One shared module, wired into all seven other servers.** `telemetrykit.py`
  here is the only place `record`/`track`/`summarize`/`tail` are
  implemented. Each other `tools/*/server.py` adds this directory to
  `sys.path`, imports `track`, and applies `@track("<server-name>")` between
  `@server.tool()` and the function definition on every tool it exposes — no
  logging code is duplicated seven times. If `usage-telemetry` is ever
  missing (e.g. someone copies a single tool folder out of this repo on its
  own), the `try/except ImportError` fallback makes `track` a no-op
  decorator, so every other tool keeps working standalone; only the logging
  is lost.
- **No payloads, ever.** A record is exactly `{ts, server, tool, ok, error?}`
  — `error` is an exception *type* name at most (e.g. `"ValueError"`), never
  a message, argument, or return value. This collection is public; nothing
  a caller passes in or gets back should ever end up in a committed or
  shared log.
- **Concurrency-safe by construction, not by locking.** Every append is a
  single `os.write` to an `O_APPEND`-opened file descriptor — one write(2)
  syscall per line, which POSIX guarantees is atomic for writes under
  `PIPE_BUF` (4096 bytes) even when several processes have the file open at
  once. That's the real situation here: every `tools/*/server.py` is its own
  OS process (stdio MCP servers), and several can be logging to the same
  file concurrently.
- **Best-effort.** A logging failure (bad path, full disk, no permission)
  is swallowed inside `record` rather than breaking the tool call it's
  observing — telemetry must never be the reason a real tool call fails.

## Files

- `telemetrykit.py` — `record` (append one line), `track` (a decorator that
  wraps a function, recording ok/error around it and re-raising), `summarize`
  (aggregate the log into per-server/per-tool counts), `tail` (the last N
  raw entries). Stdlib only (`json`, `os`, `time`, `functools`). Usable
  standalone.
- `server.py` — a thin MCP server (stdio transport) exposing
  `read_usage_summary` and `tail_usage_events`.
- `tests/test_telemetrykit.py` — 17 unit tests: logging is truly off by
  default and only writes when a path is given or the env var is set, never
  logs anything beyond the five allowed fields, creates parent directories,
  `track` records both the success and the exception path (and never
  swallows the exception itself), `summarize` aggregates correctly
  (including malformed-line skipping and first/last-seen tracking), and
  `tail` returns the right entries in the right order.
- `proof/run_2026-09-28.txt` — a live session: `CLAUDE_TOOLS_USAGE_LOG` set
  to a temp file, several real tool calls made against `secure-random` and
  `time-arithmetic` (a mix of success and a deliberate error) via
  `scripts/mcp_client.py`, then `usage-telemetry`'s own `read_usage_summary`
  and `tail_usage_events` called live and shown correctly reporting those
  exact calls — the whole loop, end to end, not just the aggregation logic
  in isolation.

## Try it without MCP

```
python3 -c "
import telemetrykit as t
t.record('secure-random', 'roll_dice', True, log_path='/tmp/usage.jsonl')
t.record('secure-random', 'generate_password', False, 'ValueError', log_path='/tmp/usage.jsonl')
print(t.summarize(log_path='/tmp/usage.jsonl'))
print(t.tail(5, log_path='/tmp/usage.jsonl'))
"
```

## Run the tests

```
python3 -m unittest discover -s tests -v
```

## Run as an MCP server

```
pip install -r requirements.txt
python3 server.py
```

## Turning logging on across the collection

Set the same `CLAUDE_TOOLS_USAGE_LOG` path on **every** server entry in your
MCP client config (this one included), so every tool call from every server
lands in one shared file:

```json
{
  "mcpServers": {
    "usage-telemetry": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/usage-telemetry/server.py"],
      "env": { "CLAUDE_TOOLS_USAGE_LOG": "/absolute/path/to/usage.jsonl" }
    },
    "secure-random": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/secure-random/server.py"],
      "env": { "CLAUDE_TOOLS_USAGE_LOG": "/absolute/path/to/usage.jsonl" }
    }
  }
}
```

Repeat the `env` block for every other `tools/*/server.py` entry you run.
Leave `CLAUDE_TOOLS_USAGE_LOG` unset anywhere (including here) and that
server simply never writes to the log — `read_usage_summary` on an unset or
missing log reports `exists: false` rather than erroring, so it's safe to
call before you've turned anything on.

## Tools exposed

| Tool | Purpose |
|---|---|
| `read_usage_summary` | Aggregate counts: total invocations, ok/error per server and per tool, first/last-seen timestamps, malformed-line count. |
| `tail_usage_events` | The last `n` raw log entries, most recent first — for spot-checking what actually got logged. |

## What it doesn't do

No cross-machine aggregation (the log is a local file; if the owner's
agents run this collection from several machines, each has its own log
unless they're pointed at a shared path), no rotation or size cap (a
long-running log grows unbounded — `summarize`/`tail` are linear scans over
the whole file, fine at the call volumes a personal agent stack produces,
not designed for high-throughput production logging), and no built-in
retention policy (trimming or archiving old entries is on the caller). No
payload/argument logging by design, not as a gap — see "No payloads, ever"
above; a tool that needs to debug *what* was called with, not just *that*
it was called, needs a different, non-public mechanism.
