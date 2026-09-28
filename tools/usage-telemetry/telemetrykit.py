"""A local, opt-in call log every other server in this collection can write
to, plus the aggregation this tool's own MCP server reads back.

Logging is off unless a log path is given: no tool call anywhere in this
collection writes a file unless the caller (an env var, or an explicit
argument) turns it on. When it is on, `record` appends one JSON line per
invocation -- `{ts, server, tool, ok, error?}`, never call arguments or
return values -- so `summarize`/`tail` can answer "was this tool actually
called since it shipped?" (TASKS.md step 9) with real counts instead of a
restated manifest. Stdlib only. Usable standalone.
"""
from __future__ import annotations

import functools
import json
import os
import time
from typing import Any, Callable, TypeVar

_ENV_VAR = "CLAUDE_TOOLS_USAGE_LOG"
_F = TypeVar("_F", bound=Callable[..., Any])


def log_path_from_env() -> str | None:
    """The log path an unset-by-caller `record`/`track`/`summarize` falls back to.

    Empty string counts as unset (a common way an env var ends up "set but blank").
    """
    path = os.environ.get(_ENV_VAR)
    return path if path else None


def _resolve(log_path: str | None) -> str | None:
    return log_path if log_path is not None else log_path_from_env()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record(server: str, tool: str, ok: bool, error: str | None = None, log_path: str | None = None) -> None:
    """Append one invocation record to the log, or do nothing if logging is off.

    `error` is an exception type name at most (e.g. "ValueError"), never a
    message or a traceback -- the whole point is a log this public repo's
    own tools can write without ever risking a payload or a secret in it.
    Best-effort: a logging failure (permissions, a full disk, a bad path)
    is swallowed rather than breaking the tool call it's trying to record.
    """
    path = _resolve(log_path)
    if not path:
        return
    entry: dict[str, Any] = {"ts": _now_iso(), "server": server, "tool": tool, "ok": ok}
    if error is not None:
        entry["error"] = error
    line = (json.dumps(entry, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # A single write(2) of one line via a raw fd (not a buffered
        # TextIOWrapper) is atomic on POSIX for writes under PIPE_BUF
        # (4096 bytes) even across processes opening the same path with
        # O_APPEND -- the property this needs, since every tools/*/server.py
        # is its own process and several can log concurrently.
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    except OSError:
        pass


def track(server_name: str, log_path: str | None = None) -> Callable[[_F], _F]:
    """Decorator: record one invocation of the wrapped function, ok or erroring.

    Meant to sit between `@server.tool()` and `def ...` so the MCP tool
    registered is the wrapped function (`functools.wraps` keeps its name,
    docstring, and signature intact for schema generation). Re-raises
    whatever the wrapped function raised, after logging it -- this never
    changes a tool's behavior, only observes it.
    """

    def decorator(fn: _F) -> _F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                record(server_name, fn.__name__, False, type(exc).__name__, log_path)
                raise
            record(server_name, fn.__name__, True, None, log_path)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def _empty_summary(path: str | None) -> dict[str, Any]:
    return {
        "log_path": path,
        "exists": False,
        "total_invocations": 0,
        "malformed_lines": 0,
        "first_seen": None,
        "last_seen": None,
        "servers": {},
    }


def summarize(log_path: str | None = None) -> dict[str, Any]:
    """Aggregate the log into per-server, per-tool counts.

    Returns `{log_path, exists, total_invocations, malformed_lines,
    first_seen, last_seen, servers: {server: {total, ok, error, tools:
    {tool: {total, ok, error, last_seen}}}}}`. A missing or empty log isn't
    an error -- it means "opted in but nothing called yet" or "not opted
    in", both real, answerable states for TASKS.md step 9.
    """
    path = _resolve(log_path)
    if not path or not os.path.exists(path):
        return _empty_summary(path)

    servers: dict[str, dict[str, Any]] = {}
    total = 0
    malformed = 0
    first_seen: str | None = None
    last_seen: str | None = None

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(entry, dict) or "server" not in entry or "tool" not in entry or "ok" not in entry:
                malformed += 1
                continue

            total += 1
            ts = entry.get("ts")
            if isinstance(ts, str):
                if first_seen is None or ts < first_seen:
                    first_seen = ts
                if last_seen is None or ts > last_seen:
                    last_seen = ts

            server_bucket = servers.setdefault(entry["server"], {"total": 0, "ok": 0, "error": 0, "tools": {}})
            tool_bucket = server_bucket["tools"].setdefault(
                entry["tool"], {"total": 0, "ok": 0, "error": 0, "last_seen": None}
            )
            is_ok = bool(entry["ok"])
            for bucket in (server_bucket, tool_bucket):
                bucket["total"] += 1
                bucket["ok" if is_ok else "error"] += 1
            if isinstance(ts, str) and (tool_bucket["last_seen"] is None or ts > tool_bucket["last_seen"]):
                tool_bucket["last_seen"] = ts

    return {
        "log_path": path,
        "exists": True,
        "total_invocations": total,
        "malformed_lines": malformed,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "servers": servers,
    }


def tail(n: int = 20, log_path: str | None = None) -> list[dict[str, Any]]:
    """The last `n` well-formed log entries, most recent first.

    Malformed lines are skipped (not counted toward `n`) rather than
    surfaced as `None` entries -- `summarize`'s `malformed_lines` is where
    that count belongs.
    """
    path = _resolve(log_path)
    if not path or not os.path.exists(path) or n <= 0:
        return []
    entries: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                entries.append(entry)
    return list(reversed(entries[-n:]))
