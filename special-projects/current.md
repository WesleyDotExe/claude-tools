# Current state

**Last cycle:** 2026-09-14 (second run)

## Where things stand

Three tools in the collection:

- `tools/collection-index` — reads `tools/*/manifest.json`, the source of
  truth the dashboard (and future runs) read from instead of re-scanning
  the repo.
- `tools/time-arithmetic` — MCP server for deterministic date/time/timezone
  math (DST, month rollover, cross-timezone diff).
- `tools/secure-random` — MCP server for CSPRNG-backed randomness (dice,
  integers, floats, shuffling, passwords, tokens, UUIDs) plus
  `verify_uniformity`, a from-scratch chi-square test that proves a range's
  output isn't biased instead of asserting it.

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for both cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for the next cycle, roughly in order of how promising they looked
during this cycle's research (see `progress/notes-for-owner.md` for the
full reasoning):

1. **New tool, if a sharply-felt + undersaturated need turns up.** The
   obvious "AI can't do X reliably" ideas (word/character counting, text
   diffing, unit/subnet conversion, cron parsing, calculators) are now
   heavily covered by existing MCP servers elsewhere — worth checking a
   candidate's saturation before investing a full cycle, the way this
   cycle did before landing on randomness.
2. **Extend `time-arithmetic`** with natural-language relative-date parsing
   ("next Friday", "in 3 business days", "end of next quarter") — flagged
   as future work in that tool's README ("What it doesn't do"), keyless,
   and builds on existing, tested code rather than starting cold.
3. **Extend `secure-random`** with weighted/biased sampling (`pick_random`
   currently only does uniform selection) if a real use case for it
   surfaces, or with a `verify_uniformity`-style checkable-proof pattern
   applied to some other "trust the tool, not the model" domain.
4. Re-run the TASKS.md loop step 1 (dogfood `collection-index`) first,
   every cycle, before any of the above — it's cheap and keeps this file
   honest.

If nothing clears the bar in a given cycle: TASKS.md rule 9 — deepen,
harden, or extend an existing tool rather than shipping filler.
