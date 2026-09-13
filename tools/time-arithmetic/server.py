"""MCP server exposing timekit's deterministic date/time functions.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from mcp.server.mcpserver import MCPServer

import timekit

server = MCPServer(
    name="time-arithmetic",
    instructions=(
        "Deterministic date/time/timezone calculations. Use these tools "
        "instead of computing DST transitions, month/year rollover, or "
        "cross-timezone elapsed time by reasoning — they are frequent "
        "sources of silent arithmetic mistakes."
    ),
)


@server.tool()
def convert_timezone(when: str, from_tz: str, to_tz: str) -> dict:
    """Convert a local wall-clock time from one IANA timezone to another.

    when: local time, e.g. "2026-03-08T01:30" (no offset).
    from_tz / to_tz: IANA names, e.g. "America/New_York", "Europe/Berlin".
    """
    return timekit.convert(when, from_tz, to_tz)


@server.tool()
def add_time_delta(
    when: str,
    tz: str,
    years: int = 0,
    months: int = 0,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
) -> dict:
    """Add a delta to a local time, correct across DST and month/year rollover.

    years/months/weeks/days are calendar units (wall-clock time preserved,
    e.g. "same time tomorrow"). hours/minutes are real elapsed time
    (correct across a DST spring-forward or fall-back boundary).
    """
    return timekit.add_delta(when, tz, years, months, weeks, days, hours, minutes)


@server.tool()
def time_difference(when1: str, tz1: str, when2: str, tz2: str) -> dict:
    """Real elapsed time between two local timestamps, which may be in different timezones."""
    return timekit.diff(when1, tz1, when2, tz2)


@server.tool()
def date_facts(date: str) -> dict:
    """Weekday, ISO week number, day-of-year, leap-year status, and days-in-month for a date."""
    return timekit.day_info(date)


@server.tool()
def search_timezones(query: str, limit: int = 20) -> list[str]:
    """Case-insensitive substring search over the IANA timezone database (e.g. 'tokyo')."""
    return timekit.find_timezones(query, limit)


if __name__ == "__main__":
    server.run(transport="stdio")
