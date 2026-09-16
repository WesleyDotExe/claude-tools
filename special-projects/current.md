# Current state

**Last cycle:** 2026-09-16 (fourth run)

## Where things stand

Four tools in the collection:

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
- `tools/discrete-probability` — MCP server for exact discrete-probability
  calculations (birthday-paradox collisions, dice-sum distributions,
  drawing without replacement, binomial trials, Bayes' theorem, a
  generalized Monty Hall problem). Every function accepts `verify=true` to
  actually play the scenario out via CSPRNG simulation and check the exact
  answer against the simulated frequency's 95% confidence interval -- the
  same proof-not-assertion discipline `secure-random` established, applied
  to a different failure mode (LLMs are specifically bad at *counterintuitive*
  discrete probability, not just randomness generation).

CI runs each tool's test suite on every PR (`.github/workflows/test.yml`,
105 tests total across all four tools as of this cycle) and
`auto-merge.yml` waits for it genuinely (fixed 2026-09-15, see
`progress/quality-debt.md` for history).

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for all cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for the next cycle, roughly in order of how promising they looked
during this cycle's research (see `progress/notes-for-owner.md` for the
full reasoning):

1. **Re-run the TASKS.md loop step 1 first, every cycle** (dogfood
   `collection-index`, re-read each tool's own "what it doesn't do"
   section fresh) before searching for new candidates — cheap, and keeps
   this file honest instead of assuming a past cycle's framing still
   applies.
2. **New tool, if a sharply-felt + undersaturated need turns up** — but
   treat "yet another single deterministic calculation" ideas (hashing,
   readability/syllable counting, bitwise arithmetic, semver ranges,
   haversine geodistance — all checked and rejected this cycle, see
   `progress/notes-for-owner.md`) as low-probability now; a single account
   (pipeworx-io) is systematically publishing MCP servers across exactly
   that space. A next candidate that clears the bar will likely need either
   a genuinely fresh angle (like this cycle's "pair the exact answer with a
   checkable simulation" move on `discrete-probability`) or a problem shape
   outside "single deterministic calculation" entirely.
3. **Extend `discrete-probability` itself**, if a real gap surfaces — e.g.
   a live MCP session or dogfooding surfaces a scenario shape (say,
   negative binomial / geometric-distribution "expected number of trials
   until first success" problems) that's a natural sibling to the six
   already there. Don't add it speculatively; only if research turns up
   the same kind of real, documented complaint the existing six answer.
4. **If nothing clears the bar:** no open item is currently queued in
   `progress/quality-debt.md` (the standing `secure-random`
   non-vectorized-uniformity item is documented as an accepted tradeoff,
   not a to-do) — a future cycle in that position should read all four
   tools' "what it doesn't do" sections fresh rather than assume a past
   cycle's suggestions still apply.

Do NOT re-propose natural-language date parsing for `time-arithmetic` as
"unbuilt future work" — its README frames the absence as a deliberate
design boundary, not a gap (2026-09-15 course-correction, see
`progress/notes-for-owner.md`).
