# collection-index

Reads every `tools/<name>/manifest.json` in the collection and reports
what's there. This is the foundational tool the standing project's first
run built (see `TASKS.md` -> Task 2 -> "First run's job"): the dashboard
generator (`scripts/build_dashboard.py`) imports `collect()` from here
rather than re-implementing the scan, and any future run can use it to
see what already exists before building something overlapping.

## Manifest schema

Each tool directory needs a `manifest.json` with at least:

```json
{
  "name": "tool-name",
  "summary": "one line: what it does",
  "problem": "the real, expressed need it addresses",
  "keyless": true,
  "created": "YYYY-MM-DD"
}
```

Anything else (entry_point, tests, proof, tools_exposed, ...) is passed
through as-is. A manifest missing a required field, or that isn't valid
JSON, is skipped with a note on stderr rather than breaking the scan for
every other tool.

## Usage

```
python3 index.py            # human-readable table
python3 index.py --json     # for scripts (e.g. the dashboard generator)
```

## Tests

```
python3 -m unittest discover -s tests -v
```
