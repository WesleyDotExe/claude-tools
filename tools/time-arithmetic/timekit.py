"""Deterministic date/time/timezone arithmetic — stdlib only.

Why this exists: language models are well-documented to be unreliable at
exactly this kind of math — DST transitions, month/year rollover with
day clamping, and computing real elapsed time across two different
timezones — because they do it by approximate reasoning instead of
calculation. Every function here does the calculation instead, using
Python's ``zoneinfo`` (the IANA tz database), and returns plain dicts
so a caller (human, script, or model via the MCP server in server.py)
gets a checkable answer rather than a sentence to trust.

No network access, no credentials, no third-party runtime dependency.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones


class TimeKitError(ValueError):
    """Raised for bad input (unknown timezone, unparseable datetime, ...)."""


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:  # zoneinfo raises different errors per platform
        raise TimeKitError(f"unknown IANA timezone: {name!r}") from exc


def _parse_naive(when: str) -> datetime:
    """Parse an ISO-8601-ish local datetime with no offset attached."""
    text = when.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise TimeKitError(f"could not parse datetime: {when!r} (use e.g. 2026-03-08T01:30)")


def _describe(dt: datetime) -> dict:
    offset = dt.utcoffset()
    dst = dt.dst()
    return {
        "iso": dt.isoformat(),
        "timezone": str(dt.tzinfo),
        "utc_offset": _fmt_offset(offset),
        "is_dst": bool(dst and dst != timedelta(0)),
        "weekday": calendar.day_name[dt.weekday()],
    }


def _fmt_offset(offset: timedelta | None) -> str:
    if offset is None:
        return "+00:00"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return f"{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def convert(when: str, from_tz: str, to_tz: str) -> dict:
    """Convert a local wall-clock time in ``from_tz`` to the equivalent in ``to_tz``."""
    naive = _parse_naive(when)
    source = naive.replace(tzinfo=_zone(from_tz))
    target = source.astimezone(_zone(to_tz))
    return {"input": _describe(source), "output": _describe(target)}


def add_delta(
    when: str,
    tz: str,
    years: int = 0,
    months: int = 0,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
) -> dict:
    """Add a calendar/clock delta to a local time, DST- and rollover-aware.

    Calendar units (years, months, weeks, days) preserve wall-clock time
    across the shift, the way "same time tomorrow" or "in 3 days" is
    normally meant, with day clamping for month/year overflow (e.g.
    Jan 31 + 1 month -> Feb 28/29, not an exception or Mar 3). Clock
    units (hours, minutes) are real elapsed time, applied through UTC,
    so "+1 hour" across a DST boundary lands on the correct wall-clock
    time instead of a time that never happened or one hour off.
    """
    naive = _parse_naive(when)
    zone = _zone(tz)
    original = naive.replace(tzinfo=zone)

    total_months = naive.month - 1 + months + years * 12
    new_year = naive.year + total_months // 12
    new_month = total_months % 12 + 1
    last_day = calendar.monthrange(new_year, new_month)[1]
    new_day = min(naive.day, last_day)
    calendar_shifted = naive.replace(year=new_year, month=new_month, day=new_day)
    calendar_shifted += timedelta(weeks=weeks, days=days)

    aware = calendar_shifted.replace(tzinfo=zone)
    # Apply the clock delta in UTC (real elapsed time), then convert back to
    # the zone. Adding a timedelta directly to a zoneinfo-aware datetime
    # uses whatever fixed offset is attached at that instant and does NOT
    # skip a DST gap or absorb a DST fold on its own — going through UTC
    # is what makes "+1 hour" correct across a spring-forward/fall-back
    # boundary instead of silently landing on a wall-clock time that never
    # happened (e.g. 02:30 on a US spring-forward night).
    shifted = aware.astimezone(ZoneInfo("UTC")) + timedelta(hours=hours, minutes=minutes)
    shifted = shifted.astimezone(zone)

    return {"input": _describe(original), "output": _describe(shifted)}


def diff(when1: str, tz1: str, when2: str, tz2: str) -> dict:
    """Real elapsed time between two local timestamps in (possibly different) zones."""
    dt1 = _parse_naive(when1).replace(tzinfo=_zone(tz1))
    dt2 = _parse_naive(when2).replace(tzinfo=_zone(tz2))
    delta = dt2 - dt1
    total_seconds = delta.total_seconds()
    sign = "-" if total_seconds < 0 else ""
    seconds = abs(int(total_seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    units = [(days, "d"), (hours, "h"), (minutes, "m"), (secs, "s")]
    while len(units) > 1 and units[0][0] == 0:
        units.pop(0)
    human = sign + " ".join(f"{value}{suffix}" for value, suffix in units)
    return {
        "first": _describe(dt1),
        "second": _describe(dt2),
        "total_seconds": total_seconds,
        "human": human,
    }


def day_info(date: str) -> dict:
    """Facts about a calendar date that models routinely get wrong under pressure."""
    naive = _parse_naive(date)
    year, month = naive.year, naive.month
    return {
        "date": naive.date().isoformat(),
        "weekday": calendar.day_name[naive.weekday()],
        "iso_week": naive.isocalendar()[1],
        "day_of_year": naive.timetuple().tm_yday,
        "is_leap_year": calendar.isleap(year),
        "days_in_month": calendar.monthrange(year, month)[1],
    }


def find_timezones(query: str, limit: int = 20) -> list[str]:
    """Case-insensitive substring search over the IANA tz database (e.g. 'york', 'berlin')."""
    q = query.strip().lower()
    matches = sorted(name for name in available_timezones() if q in name.lower())
    return matches[:limit]
