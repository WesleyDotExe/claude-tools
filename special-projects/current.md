# Current state

**Last cycle:** 2026-09-24 (twelfth run)

## Where things stand

Still eight tools in the collection (extended an existing one again this
cycle, but for a new reason this time -- see below):

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
  **New this cycle:** `compare_two_proportions` -- is the gap between two
  observed proportions (e.g. two win rates) statistically significant, or
  plausibly noise? A pooled two-proportion z-test p-value, a Wilson CI per
  group, and a Newcombe (1998) hybrid-score CI for the difference (reusing
  the tool's own `_wilson_interval`), plus a plain verdict at any
  caller-chosen confidence level (new `_norm_ppf`/`_norm_cdf` helpers, no
  scipy needed). `verify=true` runs an independent CSPRNG permutation
  (label-reshuffling) test, budget-capped like this collection's other
  search/simulation tools. Built from `special-projects/wishlist.md`'s
  `[balance-stats]` entry -- the first cycle this project's wishlist had
  real content to read. See `progress/notes-for-owner.md`'s 2026-09-24
  entry for a real design issue caught and fixed before committing (the
  z-test and exact-permutation p-values can legitimately diverge; the
  `verify=true` check compares the *significance call*, not raw numeric
  equality).
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
  since cycle ten -- see that entry in `special-projects/cycles.json` for
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
296 tests total across all eight tools as of this cycle: 281 from before
plus 15 new ones for `discrete-probability`'s `compare_two_proportions`)
and `auto-merge.yml` waits for it genuinely.

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for all cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for cycle 13, roughly in order of how promising they looked during
this cycle's research:

1. **Check `special-projects/wishlist.md` FIRST, before anything else.**
   This cycle it had real, concrete, sourced content for the first time
   (created directly by the owner, commit `3fcf0d9`) and the loop worked
   exactly as TASKS.md describes: read it, picked the one item with a named
   external caller (`[balance-stats]`), built for it. Two items remain open
   (`[build-env]`, `[mcp-proof]`) but were deliberately NOT built as MCP
   tools -- their caller is this repo's own build process, not an external
   agent invoking a tool over MCP (see `progress/notes-for-owner.md`'s
   2026-09-24 entry for the reasoning). If either recurs (a genuine second
   `+1`, from a different cycle actually re-hitting it, not just this
   cycle's first-read), consider a small script under `scripts/` or `docs`
   rather than a `tools/` entry, or reconsider whether an MCP-tool framing
   actually fits after all. A fresh wishlist item may also have appeared by
   the next cycle -- check before falling back to any of the below.
2. **`discrete-probability`'s real remaining gaps** (see its README's "What
   it doesn't do", updated this cycle): `compare_two_proportions` doesn't
   handle paired/matched samples (needs McNemar's test, not built), and its
   permutation-test budget caps out around `verify_trials *
   min(trials_a, trials_b) <= 10,000,000`. Neither has a surfaced real need
   yet -- see `progress/quality-debt.md`'s new entry.
3. **This cycle again found its win by extending an existing tool, not by
   finding a new problem shape** -- the fourth cycle running now without a
   seventh shape (see item 6 below), though this time the extension came
   from the wishlist rather than a search failing to find a new shape.
4. **Re-run the TASKS.md loop step 1 first, every cycle** (dogfood
   `collection-index`, re-read each tool's own "what it doesn't do"
   section fresh) before searching for new candidates -- this cycle
   confirmed the collection-index output still matches
   `tools/*/manifest.json` exactly, and the root README's tool list was
   already in sync.
5. **Two extend-candidates remain checked-and-deferred in `graph-algorithms`**
   for lack of a *fresh, sourced* "LLMs get this wrong" complaint (not lack
   of a real underlying problem), last re-checked 2026-09-23: **general
   (non-bipartite) graph matching** (Edmonds' blossom algorithm -- stable
   roommates, non-bipartite observational-study matching are real
   applications, still no sharp real-world failure source) and
   **rectangular/partial assignment** (unequal left/right sizes in
   `assignment_problem` -- same verdict).
6. **A promising-looking NEW tool idea remains rejected for saturation, not
   lack of a source (2026-09-23):** cross-timezone meeting/availability
   finding (intersect N people's busy-interval lists across timezones and
   DST). Found a genuinely sharp, concrete source (a MindStudio write-up
   documenting Claude Code's OWN `check_availability` tool computing "end
   of day" in UTC instead of the user's local timezone) but the underlying
   algorithm is already implemented by several existing MCP servers, even
   keyless ones (`mcp-calendar`, `when2meet-mcp`, `mcp-office-suite`'s
   `free_busy`, `pim-agents`' `findFreeSlots`). **Do not re-propose without
   a genuinely differentiated angle** (e.g. a proof/verification angle none
   of those offer).
7. **`spaced-arrangement`'s remaining real gaps** (see its README's "What
   it doesn't do"): per-category priority/weighting, and multi-dimensional
   spacing (e.g. avoid both same-artist AND same-genre clustering at once).
   The "spread evenly" gap itself is closed (`maximize_min_distance`,
   cycle eleven).
8. **Keep looking for genuinely different problem shapes** before reaching
   for another instance of a shape already covered: calculation, static
   CSP (`logic-grid-solver`), sequential action search (`strips-planner`),
   structural graph algorithms (`graph-algorithms`), and combinatorial
   generation under a guaranteed invariant (`spaced-arrangement`). No new
   seventh shape has been identified in four cycles now. Treat
   "extend/harden is a fully legitimate, repeatable outcome" (TASKS.md rule
   9) as the collection's steady state at eight tools deep unless a future
   cycle's search (or the wishlist) turns up something genuinely new.
9. **Do not re-propose:** Secret Santa/derangement-with-exclusions
   (privacy pain point, not correctness; already a special case of
   `maximum_bipartite_matching`), bill-splitting/debt-simplification,
   pairwise/covering-array test generation (PictMCP), regex generation/
   ReDoS, synthetic-data generation with guaranteed correlation, OR-Tools-
   based optimization/bin-packing/knapsack/job-shop scheduling,
   round-robin scheduling, cryptarithmetic, or sudoku/latin-square/maze
   generation -- all checked and rejected in earlier cycles for saturation
   or scope-overlap, not infeasibility.
10. **Apportionment/seat-allocation (D'Hondt, Sainte-Laguë, Hamilton) and
    stable matching (Gale-Shapley)** — plausible shapes, no sharp real
    "LLMs get this wrong" complaint found as of 2026-09-22. Worth
    revisiting only with a real source.
11. **MCP mechanics notes for live-session proofs:** use
    `result.content[0].text` parsed as JSON if `structured_content` is
    `None`; use `result.is_error` (snake_case), not `result.isError`; the
    local container needs `pip install --user mcp cffi` first. This
    cycle's `mcp` version was still 2.2.0, same behavior as documented
    previously.
12. **If nothing clears the bar:** re-read all eight tools' "what it
    doesn't do" sections fresh, and diff the root README's tool list
    against `tools/*/manifest.json` -- both checked and confirmed in sync
    this cycle.

Do NOT re-propose natural-language date parsing for `time-arithmetic` — its
README frames the absence as a deliberate design boundary, not a gap
(2026-09-15 course-correction, see `progress/notes-for-owner.md`).
