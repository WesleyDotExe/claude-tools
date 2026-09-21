# Current state

**Last cycle:** 2026-09-21 (ninth run)

## Where things stand

Eight tools in the collection:

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
  `shortest_path` (Dijkstra, verified via an independent Bellman-Ford
  recomputation against the formal optimality conditions), `topological_sort`
  (Kahn's algorithm, returning a concrete cycle as proof when the graph
  isn't a DAG), `minimum_spanning_tree` (Kruskal's algorithm, verified via
  the cycle-property exchange argument), `max_flow` (Edmonds-Karp,
  always paired with a minimum cut whose equal capacity IS the optimality
  proof via the max-flow min-cut theorem), and, as of this cycle,
  `graph_coloring` (DSATUR + forward-checking backtracking, budgeted by
  `max_search_nodes`, verified via `verify_coloring`'s direct-definition
  check) plus `chromatic_number` (the minimum colors needed: a clique
  gives a lower bound for free, no search required, then backtracking
  search upward proves every smaller count impossible by full exhaustion,
  not just unfound). `generate_random_graph` gives a seeded, reproducible
  graph. This is a fourth genuinely different problem shape in the
  collection: structural traversal/optimization over an explicit graph,
  not sequential action search (`strips-planner`), constraint satisfaction
  over a static assignment (`logic-grid-solver`), or a single calculation
  (the other three).
- `tools/spaced-arrangement` — MCP server that constructs an ordering of
  items so no two items of the same category land within `min_distance`
  positions of each other, and proves it (budgeted backtracking search,
  CSPRNG-randomized tie-breaking via `secrets.SystemRandom` so repeated
  calls give different valid orderings, `max_search_nodes` contract
  matching `graph-algorithms`' `graph_coloring`/`strips-planner`'s BFS:
  full search-tree exhaustion proves infeasibility, running out of budget
  raises instead of guessing). `verify_arrangement` independently
  re-checks any claimed arrangement against the direct definition, no
  search. `generate_arrangement_problem` gives a seeded, reproducible
  instance. This is a **sixth** genuinely different problem shape:
  combinatorial *generation* under a guaranteed invariant — constructing an
  object proven to satisfy a property, not calculating one answer
  (`secure-random`/`discrete-probability`/`time-arithmetic`), checking a
  static assignment (`logic-grid-solver`), searching sequential actions
  (`strips-planner`), or traversing/optimizing an explicit graph
  (`graph-algorithms`). Built because a uniformly random shuffle of a
  category-heavy list clusters same-category items together far more than
  people expect (documented for years in Spotify's own community forums
  and 2026 engineering coverage of Spotify rebuilding shuffle around this
  exact complaint) — and because a per-category frequency check alone is
  *necessary but not sufficient* once 3+ categories are involved (a
  concrete counterexample is in the test suite), so real exhaustive search,
  not a formula, is what actually proves infeasibility correctly.

CI runs each tool's test suite on every PR (`.github/workflows/test.yml`,
244 tests total across all eight tools as of this cycle: 219 from before
plus 25 new ones for `spaced-arrangement`) and `auto-merge.yml` waits for
it genuinely.

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
2. **`spaced-arrangement` is now built** (this cycle) — don't re-propose
   "avoid adjacent repeats" / declumping-shuffle / task-scheduler-cooldown
   as an unbuilt gap. If a future cycle wants to go further on the same
   tool, real remaining gaps (see its README's "What it doesn't do"):
   `min_distance` is a hard constraint only, with no "spread as evenly as
   possible beyond the minimum" soft-optimization mode, and no per-category
   priority/weighting (e.g. "front-load this category earlier"). Also
   real, but out of scope so far: multi-dimensional spacing (e.g. avoid
   both same-artist AND same-genre too close at once).
3. **Graph coloring is built** (`graph_coloring`, `verify_coloring`,
   `chromatic_number` in `tools/graph-algorithms`, 2026-09-20) — don't
   re-propose it. Next real gaps there: maximum matching or LP-style
   network optimization (see that tool's README).
4. **Keep looking for genuinely different problem shapes** before reaching
   for another instance of a shape already covered: calculation
   (`secure-random`/`discrete-probability`/`time-arithmetic`), static CSP
   (`logic-grid-solver`), sequential action search (`strips-planner`),
   structural graph algorithms (`graph-algorithms`), and now combinatorial
   generation under a guaranteed invariant (`spaced-arrangement`). No
   obviously-unexplored seventh shape was identified this cycle — the next
   cycle may need to search harder for one, or lean on TASKS.md rule 9
   (deepen/extend) more than usual. Exact symbolic/algebraic manipulation
   (checked 2026-09-20, saturated + poor stdlib fit) and computational
   geometry (checked 2026-09-20, no sharp source found) — don't re-propose
   without a genuinely new angle or source.
5. **Do not re-propose pairwise/covering-array test generation** — real
   need (see `progress/notes-for-owner.md`'s 2026-09-21 entry for the
   source), but `PictMCP` (github.com/takeyaqa/PictMCP) already covers it
   over MCP with no differentiated angle found. Same for regex
   generation/ReDoS (saturated, checked 2026-09-15 and again 2026-09-21)
   and synthetic-data generation with guaranteed correlation structure
   (saturated, checked 2026-09-21).
6. **Do not re-propose sudoku/latin-square/maze *generation*** as an
   unbuilt gap without a genuinely differentiated angle — checked again as
   recently as 2026-09-19 and still overlaps `logic-grid-solver`'s
   existing CSP shape while being heavily saturated by non-MCP generators.
   See `progress/notes-for-owner.md`'s 2026-09-19 entry.
7. **When next building a live-session proof for any tool**, check
   `result.content[0].text` (parsed as JSON) if `structured_content` is
   `None` rather than assuming it's populated, and use `result.is_error`
   (snake_case), not `result.isError`; the local container also needs
   `pip install --user mcp cffi` before an MCP server will even import
   (the `cryptography` package needs `cffi` or it PanicExceptions on
   import) — see `progress/notes-for-owner.md`'s 2026-09-18 and 2026-09-19
   entries.
8. **Do not re-propose OR-Tools-based combinatorial optimization**, round-
   robin tournament scheduling, or cryptarithmetic solving as unbuilt gaps
   — all checked and rejected in earlier cycles, see
   `progress/notes-for-owner.md` and `special-projects/cycles.json`'s
   2026-09-17/18 entries.
9. **If nothing clears the bar:** read all eight tools' "what it doesn't
   do" sections fresh rather than assume a past cycle's suggestions still
   apply, per rule 9.

Do NOT re-propose natural-language date parsing for `time-arithmetic` — its
README frames the absence as a deliberate design boundary, not a gap
(2026-09-15 course-correction, see `progress/notes-for-owner.md`).
