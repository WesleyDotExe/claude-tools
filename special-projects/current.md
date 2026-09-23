# Current state

**Last cycle:** 2026-09-23 (eleventh run)

## Where things stand

Still eight tools in the collection (no new tool this cycle -- extended an
existing one instead, per TASKS.md rule 9's "extend rather than duplicate/
deepen if nothing new clears the bar" guidance, same outcome shape as
cycles four and ten):

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
  a small fixed JSON vocabulary. `solve_planning_problem` proves its plan
  is shortest-possible, or proves the goal is unreachable by exhausting
  the entire reachable state space. `verify_plan` independently replays
  any candidate plan step by step. `generate_blocks_world_problem` gives a
  seeded, reproducible Blocksworld instance.
- `tools/graph-algorithms` — MCP server for the classic graph algorithms:
  `shortest_path`, `topological_sort`, `minimum_spanning_tree`, `max_flow`,
  `graph_coloring` + `chromatic_number`, `maximum_bipartite_matching`, and
  `assignment_problem` -- each solved via one algorithm and independently
  checked via a second, structurally different one (Bellman-Ford,
  direct-definition, cycle-property exchange, max-flow min-cut, DSATUR +
  backtracking exhaustion, Koenig's theorem, LP duality respectively).
  `generate_random_graph` gives a seeded, reproducible graph. Unchanged
  this cycle -- see cycle ten's entry in `special-projects/cycles.json` for
  the bipartite-matching/assignment-problem build.
- `tools/spaced-arrangement` — MCP server that constructs an ordering of
  items so no two items of the same category land within `min_distance`
  positions of each other, and proves it (budgeted backtracking search,
  CSPRNG-randomized tie-breaking, `max_search_nodes` contract matching
  `graph-algorithms`/`strips-planner`: full search-tree exhaustion proves
  infeasibility, running out of budget raises instead of guessing).
  `verify_arrangement` independently re-checks any claimed arrangement.
  `generate_arrangement_problem` gives a seeded, reproducible instance.
  **New this cycle:** `maximize_min_distance` -- given only the items (no
  caller-chosen `min_distance`), finds the LARGEST `min_distance` for which
  a valid arrangement exists and proves it's the largest, via binary
  search over the existing exhaustive feasibility proof (feasibility is
  monotonic in `min_distance`, so this is sound: O(log n) feasibility
  checks, each one still a genuine budgeted exhaustive search). The final
  answer's optimality is itself proven -- structurally when it hits the
  `n-1` ceiling (the farthest two of `n` positions can ever be), or by one
  more exhaustive search one distance higher that comes back impossible.
  This is the rigorous formalization of "spread categories as evenly as
  possible" that this tool's own README had flagged as a gap since it was
  built -- and it directly completes the technique its own cited source
  (Spotify's 2026 engineering write-up: generate many candidate shuffles,
  pick the best-spread one) already described, by finding the best-spread
  one directly via proof instead of by sampling.

CI runs each tool's test suite on every PR (`.github/workflows/test.yml`,
281 tests total across all eight tools as of this cycle: 272 from before
plus 9 new ones for `spaced-arrangement`'s `maximize_min_distance`) and
`auto-merge.yml` waits for it genuinely.

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for all cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for cycle 12, roughly in order of how promising they looked during
this cycle's research:

1. **Re-run the TASKS.md loop step 1 first, every cycle** (dogfood
   `collection-index`, re-read each tool's own "what it doesn't do"
   section fresh) before searching for new candidates -- this cycle
   confirmed the collection-index output still matches `tools/*/manifest.json`
   exactly, and the root README's tool list was already in sync (last
   cycle's fix held).
2. **This cycle again found its win by extending an existing tool, not by
   finding a new problem shape.** Two extend-candidates were checked and
   explicitly deferred again for lack of a *fresh, sourced* "LLMs get this
   wrong" complaint (not lack of a real underlying problem):
   - **General (non-bipartite) graph matching** (Edmonds' blossom
     algorithm) in `graph-algorithms` -- real applications exist (stable
     roommates, non-bipartite observational-study matching), but still no
     sharp real-world "an LLM/tool failed at this" source, same verdict as
     `progress/quality-debt.md`'s existing entry. Worth building only if a
     future cycle's search finds one.
   - **Rectangular/partial assignment** (unequal left/right sizes) in
     `graph-algorithms`'s `assignment_problem` -- same verdict: real OR
     problem, no fresh LLM-failure source found this cycle either.
3. **A promising-looking NEW tool idea was checked and rejected for
   saturation, not lack of a source:** cross-timezone meeting/availability
   finding (intersect N people's busy-interval lists across timezones and
   DST, entirely from structured JSON input, no calendar credentials).
   This cycle found a genuinely sharp, concrete source -- a MindStudio
   write-up documenting Claude Code's OWN `check_availability` tool
   computing "end of day" in UTC instead of the user's local timezone,
   silently returning one slot instead of seven -- but the underlying
   free/busy-interval-intersection *algorithm* turned out to be
   implemented by several existing MCP servers already (`mcp-calendar`,
   `when2meet-mcp`, `mcp-office-suite`'s `free_busy`, `pim-agents`'
   `findFreeSlots`), even setting aside the ones that need real calendar
   credentials. **Do not re-propose this without a genuinely differentiated
   angle** (e.g. a proof/verification angle none of those offer, the way
   this collection differentiates elsewhere) -- the plain "intersect busy
   intervals across timezones" shape itself is not unclaimed.
4. **`spaced-arrangement`'s remaining real gaps** (see its README's "What
   it doesn't do", updated this cycle): per-category priority/weighting
   (no way to say a category should appear earlier or matter more), and
   multi-dimensional spacing (e.g. avoid both same-artist AND same-genre
   too close at once, as two invariants enforced together). The "spread
   evenly" gap itself is now closed (`maximize_min_distance`, this cycle).
5. **`graph-algorithms`'s real remaining gaps** (see its README's "What it
   doesn't do", unchanged): general (non-bipartite) matching and
   rectangular/partial assignment -- see item 2 above, same verdict.
6. **Keep looking for genuinely different problem shapes** before reaching
   for another instance of a shape already covered: calculation, static
   CSP (`logic-grid-solver`), sequential action search (`strips-planner`),
   structural graph algorithms (`graph-algorithms`), and combinatorial
   generation under a guaranteed invariant (`spaced-arrangement`, now also
   covering an *optimization* variant of that same shape via
   `maximize_min_distance`). No new seventh shape was identified this
   cycle either -- three cycles running now. A future cycle may need to
   search substantially harder or more laterally (e.g. non-English-language
   sources, non-Reddit/non-GitHub complaint venues, or a deliberately
   different search strategy) before accepting a fourth straight
   extend/harden cycle, OR treat "extend/harden is a fully legitimate,
   repeatable outcome" (which TASKS.md rule 9 explicitly allows) as simply
   the collection's steady state once seven-ish tools deep.
7. **Do not re-propose Secret Santa / derangement-with-exclusions
   generation** as a new tool -- checked 2026-09-23; real and commonly
   requested, but the documented AI pain point found was privacy (a
   volunteer sees all pairings), not a correctness failure, and the
   underlying problem is already solvable as a special case of
   `graph-algorithms`' own `maximum_bipartite_matching` (bipartite perfect
   matching between givers/receivers with excluded edges removed) -- no
   differentiated new-tool angle.
8. **Do not re-propose bill-splitting/debt-simplification** (saturated),
   pairwise/covering-array test generation (saturated by PictMCP), regex
   generation/ReDoS (saturated), synthetic-data generation with guaranteed
   correlation (saturated), OR-Tools-based optimization / bin-packing /
   knapsack / job-shop scheduling (checked again 2026-09-23, same verdict:
   real but saturated by OR-Tools-based MCP servers, and a poor fit for
   this collection's stdlib-only discipline), round-robin scheduling, or
   cryptarithmetic (all checked and rejected in earlier cycles).
9. **Apportionment/seat-allocation (D'Hondt, Sainte-Laguë, Hamilton) and
   stable matching (Gale-Shapley)** — plausible shapes, checked again as
   recently as 2026-09-22, still no sharp real "LLMs get this wrong"
   complaint found. Worth revisiting only with a real source.
10. **Do not re-propose sudoku/latin-square/maze generation** (overlaps
    logic-grid-solver, saturated elsewhere).
11. **MCP mechanics notes for live-session proofs:** use
    `result.content[0].text` parsed as JSON if `structured_content` is
    `None`; use `result.is_error` (snake_case), not `result.isError`; the
    local container needs `pip install --user mcp cffi` first. This
    cycle's `mcp` version was still 2.2.0, same behavior as documented
    previously.
12. **If nothing clears the bar:** re-read all eight tools' "what it
    doesn't do" sections fresh, and diff the root README's tool list
    against `tools/*/manifest.json` -- both checked and confirmed in sync
    this cycle (no repeat of the cycle-ten `spaced-arrangement`-missing
    incident).

Do NOT re-propose natural-language date parsing for `time-arithmetic` — its
README frames the absence as a deliberate design boundary, not a gap
(2026-09-15 course-correction, see `progress/notes-for-owner.md`).
