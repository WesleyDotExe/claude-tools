# Current state

**Last cycle:** 2026-09-15 (third run)

## Where things stand

Three tools in the collection, all hardened this cycle:

- `tools/collection-index` — reads `tools/*/manifest.json`, the source of
  truth the dashboard (and future runs) read from instead of re-scanning
  the repo.
- `tools/time-arithmetic` — MCP server for deterministic date/time/timezone
  math (DST, month rollover, cross-timezone diff). Deliberately does not
  parse natural-language dates -- see its README's "What it doesn't do".
- `tools/secure-random` — MCP server for CSPRNG-backed randomness (dice,
  integers, floats, shuffling, passwords, tokens, UUIDs, weighted picks)
  plus `verify_uniformity` and `verify_weighted_distribution`, chi-square
  tests that prove output isn't biased instead of asserting it.

CI now actually runs each tool's test suite on every PR
(`.github/workflows/test.yml`) and `auto-merge.yml` genuinely waits for it
(the previous "waits for checks matching a name that no workflow produced,
so merges instantly" gap, and a related event-race bug, are both fixed —
see `progress/quality-debt.md`).

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for all cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for the next cycle, roughly in order of how promising they looked
during this cycle's research (see `progress/notes-for-owner.md` for the
full reasoning):

1. **New tool, if a sharply-felt + undersaturated need turns up.** Two
   cycles in a row now, the obvious "AI can't do X reliably" ideas (word
   counting, diffing, unit/subnet conversion, cron parsing, calculators,
   regex/ReDoS, WCAG contrast) all turned out to be heavily covered by
   existing MCP servers elsewhere. Check saturation early, before
   investing a full cycle in one candidate.
2. Re-run the TASKS.md loop step 1 (dogfood `collection-index`) first,
   every cycle, before searching for new candidates — it's cheap and
   keeps this file honest.
3. If nothing clears the bar again: there isn't an obvious next
   hardening/extension item queued in `progress/quality-debt.md` right
   now (both open items from the last two cycles are fixed as of this
   cycle) — a future cycle in that position should read all three tools'
   "what it doesn't do" sections fresh, rather than assume last cycle's
   suggestions still apply (this cycle found one, the time-arithmetic
   NL-date idea, that didn't — see `progress/notes-for-owner.md`).

Do NOT re-propose natural-language date parsing for `time-arithmetic` as
"unbuilt future work" — its README frames the absence as a deliberate
design boundary, not a gap (2026-09-15 course-correction, see
`progress/notes-for-owner.md`).
