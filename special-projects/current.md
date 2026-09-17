# Current state

**Last cycle:** 2026-09-17 (fifth run)

## Where things stand

Five tools in the collection:

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
  answer against the simulated frequency's 95% confidence interval.
- `tools/logic-grid-solver` — MCP server that exactly solves logic grid
  ("zebra") puzzles from a small fixed clue vocabulary (`same_position`,
  `next_to`, `immediately_left_of`, etc.), via constraint propagation
  (arc consistency + MRV backtracking, not brute force). `solve_logic_grid`
  proves the solution is *unique* by default (keeps searching for a second
  one instead of stopping at the first), and `verify_logic_grid_solution`
  independently re-checks any proposed grid against the clues via a
  different code path than the solver's own search state -- the same
  proof-not-assertion discipline as `secure-random`/`discrete-probability`,
  applied to a genuinely different problem shape (constraint search, not
  calculation) after the previous cycle flagged that "single deterministic
  calculation" MCP ideas are getting actively saturated across the
  ecosystem.

CI runs each tool's test suite on every PR (`.github/workflows/test.yml`,
133 tests total across all five tools as of this cycle) and
`auto-merge.yml` waits for it genuinely (fixed 2026-09-15, see
`progress/quality-debt.md` for history).

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for all cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for the next cycle, roughly in order of how promising they looked
during this cycle's research:

1. **Re-run the TASKS.md loop step 1 first, every cycle** (dogfood
   `collection-index`, re-read each tool's own "what it doesn't do"
   section fresh) before searching for new candidates.
2. **Keep chasing the "different problem shape" move that worked this
   cycle**, not another single-deterministic-calculation idea. This
   cycle's actual finding: the saturation isn't total, it's specific to
   "wrap one well-known formula/algorithm as an MCP tool." Constraint
   satisfaction (`logic-grid-solver`) was one way out; other shapes worth
   scouting next time include search/planning problems, combinatorial
   generation (not just counting), or anything where the LLM failure mode
   is "can't hold many things consistent at once" rather than "can't
   compute one formula."
3. **Extend `logic-grid-solver`**, if a real gap surfaces — e.g. a
   dogfooding session or live puzzle turns up a clue shape the current
   10-type vocabulary can't express cleanly (see
   `progress/quality-debt.md`'s "between"/quantified-clue note). Don't add
   speculative clue types; only if a real puzzle needs one.
4. **Do not re-propose OR-Tools-based combinatorial optimization** as an
   unbuilt gap — it was checked this cycle and found already served by two
   existing MCP servers (MCP Optimizer, Opti-MCP), see
   `progress/notes-for-owner.md`'s 2026-09-17 entry for the full reasoning
   and what a genuinely differentiated angle on it would need to look like.
5. **If nothing clears the bar:** read all five tools' "what it doesn't do"
   sections fresh rather than assume a past cycle's suggestions still
   apply, per rule 9.

Do NOT re-propose natural-language date parsing for `time-arithmetic` as
"unbuilt future work" — its README frames the absence as a deliberate
design boundary, not a gap (2026-09-15 course-correction, see
`progress/notes-for-owner.md`).
