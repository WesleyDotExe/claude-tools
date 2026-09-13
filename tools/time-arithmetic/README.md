# time-arithmetic

An MCP server that does date/time/timezone math by calculation instead of
by asking a language model to reason it out. This is a real, well-documented
gap: DST transitions, month/year rollover, and cross-timezone "same time"
scheduling are exactly the kind of thing models get confidently wrong.

## What it solves

- **DST transitions.** "1 hour after 01:30 America/New_York on 2026-03-08"
  should land at 03:30 (02:30 never happens that night). "+1 day" and "+1
  hour" across a fall-back night behave differently on purpose: a calendar
  day preserves wall-clock time, an hour is real elapsed time.
- **Month/year rollover.** "Jan 31 + 1 month" is Feb 28 (or 29), not an
  error and not "March 3".
- **Cross-timezone elapsed time.** "9am in Los Angeles" and "9am in Berlin"
  on the same date are 9 hours apart, not simultaneous — a classic source
  of scheduling bugs when a model eyeballs "same time" as "same instant."

Building this as code that's *called* (rather than prose the model
generates) is the point: the answer is checkable, and it's the same answer
every time.

## Files

- `timekit.py` — the actual logic. Stdlib only (`datetime`, `zoneinfo`,
  `calendar`). No network, no credentials, no third-party dependency. Usable
  standalone by importing it directly.
- `server.py` — a thin MCP server (stdio transport) wrapping `timekit.py`'s
  five functions as tools. Requires the `mcp` package (see below).
- `tests/test_timekit.py` — unit tests targeting the exact failure modes
  above (spring-forward gap, fall-back fold, leap day, month clamping,
  cross-timezone diff). Runs with stdlib `unittest`, no extra install.
- `proof/run_2026-09-13.txt` — a captured run of the full test suite plus a
  live MCP client session (list_tools + five real tool calls over stdio),
  proving the server actually speaks MCP, not just that the Python
  functions work in isolation.

## Try it without MCP

```
python3 -c "
import timekit
print(timekit.add_delta('2026-03-08T01:30', 'America/New_York', hours=1))
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

Point an MCP client at it, e.g. in Claude Desktop/Code's MCP config:

```json
{
  "mcpServers": {
    "time-arithmetic": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/time-arithmetic/server.py"]
    }
  }
}
```

## Tools exposed

| Tool | Purpose |
|---|---|
| `convert_timezone` | Convert a local time from one IANA zone to another. |
| `add_time_delta` | Add years/months/weeks/days (calendar) and/or hours/minutes (elapsed time) to a local time. |
| `time_difference` | Real elapsed time between two local timestamps, possibly in different zones. |
| `date_facts` | Weekday, ISO week, day-of-year, leap-year status, days-in-month for a date. |
| `search_timezones` | Substring search over the IANA timezone database. |

## What it doesn't do

No recurrence rules (RRULE), no natural-language date parsing ("next
Tuesday"), no historical pre-1970-ish tz quirks beyond what the system's
IANA database carries. Inputs are ISO-ish (`YYYY-MM-DDTHH:MM[:SS]`) and
IANA zone names, not free text — that's a deliberate boundary: this tool
is for exact calculation once the inputs are already unambiguous, not for
interpreting vague scheduling language.
