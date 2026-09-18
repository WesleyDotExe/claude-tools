# Current state

**Last cycle:** 2026-09-18 (sixth run)

## Where things stand

Six tools in the collection:

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
  ("zebra") puzzles via constraint propagation (arc consistency + MRV
  backtracking). `solve_logic_grid` proves uniqueness by continuing the
  search for a second solution; `verify_logic_grid_solution` independently
  re-checks any proposed grid via a different code path.
- `tools/strips-planner` — MCP server that exactly solves STRIPS-style
  planning problems (a sequence of actions from an initial state to a
  goal) via real breadth-first search over a grounded state space, given
  a small fixed JSON vocabulary (facts, action schemas with
  preconditions/add/delete, optional `"not"`-negation) instead of PDDL/
  ADL. `solve_planning_problem` proves its plan is shortest-possible, or
  proves the goal is unreachable by exhausting the entire reachable state
  space (distinct from a too-small search budget, which raises instead of
  guessing). `verify_plan` independently replays any candidate plan step
  by step via a separate, simpler forward-simulation code path.
  `generate_blocks_world_problem` gives a seeded, reproducible instance of
  the classic Blocksworld benchmark domain. This is a genuinely different
  problem shape from every other tool here: sequential action search over
  cumulative, interdependent state, not a static constraint assignment
  (`logic-grid-solver`) or a single calculation (the other three).

CI runs each tool's test suite on every PR (`.github/workflows/test.yml`,
158 tests total across all six tools as of this cycle: 133 from before plus
`strips-planner`'s 25) and `auto-merge.yml` waits for it genuinely.

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
2. **Keep looking for genuinely different problem shapes**, the move that
   worked again this cycle (planning/state-space search, after
   `logic-grid-solver`'s constraint satisfaction). Shapes not yet explored
   in this collection: combinatorial generation under constraints (e.g.
   generating structures with a guaranteed property, not just
   counting/searching them), or "memory over many items" tasks (holding
   and cross-referencing a large structured record set consistently)
   rather than search or calculation. Don't reach for another CSP or
   another single-formula calculator by default -- both shapes are already
   represented here and the "single deterministic calculation" shape is
   documented as actively saturated across the wider MCP ecosystem (see
   `progress/notes-for-owner.md`'s 2026-09-15/16/17 entries).
3. **Extend `strips-planner`, if a real gap surfaces** — e.g. a
   dogfooding session turns up a domain that genuinely needs typed
   objects, disjunctive preconditions, or action costs (currently
   unbuilt, and deliberately so per its README's "what it doesn't do" —
   don't re-propose these as unbuilt gaps without a concrete need driving
   it; that's what a full PDDL/ADL planner is for). A* with a real
   heuristic (vs. plain BFS) would only matter if a real domain's state
   space is too large for BFS within a sane budget — not worth adding
   speculatively.
4. **When next building a live-session proof for any tool**, check
   `result.content[0].text` (parsed as JSON) if `structured_content` is
   `None` rather than assuming it's populated — see
   `progress/notes-for-owner.md`'s 2026-09-18 entry; this affected every
   tool's output under the `mcp==2.2.0` version installed this cycle, not
   just `strips-planner`.
5. **Do not re-propose sudoku, round-robin tournament scheduling, or
   cryptarithmetic (SEND+MORE=MONEY) solving** as unbuilt gaps — all three
   were checked this cycle and rejected (sudoku/cryptarithmetic overlap
   `logic-grid-solver`'s existing CSP shape and are heavily saturated by
   non-MCP solvers; round-robin scheduling didn't clear the "sharply
   documented LLM failure" bar). See `special-projects/cycles.json`'s
   2026-09-18 entry for the full reasoning.
6. **Do not re-propose OR-Tools-based combinatorial optimization** as an
   unbuilt gap — checked and rejected 2026-09-17, see
   `progress/notes-for-owner.md`.
7. **If nothing clears the bar:** read all six tools' "what it doesn't do"
   sections fresh rather than assume a past cycle's suggestions still
   apply, per rule 9.

Do NOT re-propose natural-language date parsing for `time-arithmetic` — its
README frames the absence as a deliberate design boundary, not a gap
(2026-09-15 course-correction, see `progress/notes-for-owner.md`).
