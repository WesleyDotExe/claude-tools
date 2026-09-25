# Current state

**Last cycle:** 2026-09-25 (thirteenth run)

## Where things stand

Still eight `tools/*` MCP servers — this cycle built internal dev tooling
under `scripts/` instead of a ninth tool or an extension to an existing
one (see "why" below):

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
  generalized Monty Hall problem, and `compare_two_proportions`: a
  two-proportion z-test with Wilson/Newcombe confidence intervals and a
  plain verdict). Every function accepts `verify=true` to actually play
  the scenario out via CSPRNG simulation and check the exact answer
  against the simulated frequency (for `compare_two_proportions`, against
  an independent permutation test's *significance call*, not raw p-value
  equality -- see `special-projects/wishlist.md`'s
  `[stats-normal-vs-exact-pvalue]` entry for why those legitimately
  differ). Unchanged since cycle twelve.
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
  checked via a second, structurally different one. Unchanged since cycle
  ten.
- `tools/spaced-arrangement` — MCP server that constructs an ordering of
  items so no two items of the same category land within `min_distance`
  positions of each other, and proves it (budgeted backtracking search,
  CSPRNG-randomized tie-breaking). `verify_arrangement` independently
  re-checks any claimed arrangement; `maximize_min_distance` finds the
  largest achievable spacing and proves it's the largest. Unchanged since
  cycle eleven.

**New this cycle: `scripts/` dev tooling**, closing both items
`special-projects/wishlist.md` had carried as open since cycle twelve:

- `scripts/mcp_dev_setup.sh` — idempotent `pip install --user mcp cffi`
  preflight (closes `[build-env]`: building/testing any `tools/*` server
  here needs both, and the second import fails with a confusing pyo3
  panic without `cffi`).
- `scripts/mcp_client.py` — a reusable stdio MCP client, as a library
  (`run_calls()`) and a CLI (`list-tools`/`call`/`run`), that extracts a
  typed result from a `CallToolResult` (`structured_content` first, text-
  content-as-JSON fallback) instead of every proof script re-deriving
  that by hand (closes `[mcp-proof]`). `run` replays a whole JSON list of
  labeled calls against one server and prints/saves them in this repo's
  existing `--- label ---\n<value>` proof-file shape.

Both were deliberately deferred at cycle twelve (their caller is this
repo's own build process, not a named external MCP caller, so TASKS.md
rule 3 said not to build them as `tools/` entries yet) pending a genuine
*second* recurrence from a different cycle. This cycle supplied exactly
that -- a fresh container hit the same missing-`mcp`/`cffi` failure, and
writing this cycle's own proof needed the same text-parsing workaround --
so they were built as `scripts/`, per cycle twelve's own plan. Proof
they work, driving two different existing servers live:
`scripts/proof/run_2026-09-25.txt`. See `scripts/README.md` for usage.

CI runs each tool's test suite on every PR (`.github/workflows/test.yml`,
296 tests total across all eight tools, unchanged this cycle -- no
`tools/*` code changed) and `auto-merge.yml` waits for it genuinely.
`mcp` stays a dev-only dependency (installed locally via
`mcp_dev_setup.sh`, never by CI), exactly as each tool's own
`requirements.txt` already treats it -- `scripts/` isn't scanned by
`test.yml`'s `tools/*/tests` loop, so this cycle needed no CI changes.

`special-projects/cycles.json` has the full story (searches, source links,
why each tool was picked, proof) for all cycles so far.
`scripts/build_site.py` renders `_site/dashboard.html` from `cycles.json`
and `collection-index`'s scan — gitignored, rebuild it, don't commit it.

## Next step

Options for cycle 14, roughly in order of how promising they looked during
this cycle's research:

1. **Check `special-projects/wishlist.md` FIRST, before anything else.**
   As of this cycle it has exactly one open item,
   `[stats-normal-vs-exact-pvalue]` -- a design lesson for any *future*
   significance-test tool, not a buildable gap on its own (nothing to
   build until such a tool is proposed). If it's still the only open item
   next cycle too, that means step 2 falls through to research/hardening
   the same way it did before cycle twelve's wishlist content existed --
   don't force a wishlist-sourced pick that isn't there.
2. **`discrete-probability`'s real remaining gaps** (see its README's "What
   it doesn't do"): `compare_two_proportions` doesn't handle
   paired/matched samples (needs McNemar's test, not built), and its
   permutation-test budget caps out around `verify_trials *
   min(trials_a, trials_b) <= 10,000,000`. Neither has a surfaced real need
   yet -- see `progress/quality-debt.md`.
3. **This cycle's win was internal build tooling, not a `tools/` change at
   all** -- the first cycle in this collection's history that shipped
   nothing under `tools/`. Don't read that as a new steady state: it was a
   direct, deliberate payoff of cycle twelve's specific plan (build on
   genuine second recurrence), not a general license to default to
   `scripts/` work. Check the wishlist and search for a real caller before
   reaching for another `scripts/` task.
4. **Two extend-candidates remain checked-and-deferred in `graph-algorithms`**
   for lack of a *fresh, sourced* "LLMs get this wrong" complaint, last
   re-checked 2026-09-23: **general (non-bipartite) graph matching**
   (Edmonds' blossom algorithm) and **rectangular/partial assignment**
   (unequal left/right sizes in `assignment_problem`).
5. **A promising-looking NEW tool idea remains rejected for saturation, not
   lack of a source (2026-09-23):** cross-timezone meeting/availability
   finding. Found a genuinely sharp source (a MindStudio write-up on
   Claude Code's own `check_availability` tool miscomputing "end of day"
   across timezones) but the underlying algorithm is already implemented
   by several existing keyless MCP servers. **Do not re-propose without a
   genuinely differentiated angle** (e.g. a proof/verification angle none
   of those offer).
6. **`spaced-arrangement`'s remaining real gaps**: per-category
   priority/weighting, and multi-dimensional spacing (e.g. avoid both
   same-artist AND same-genre clustering at once).
7. **Keep looking for genuinely different problem shapes** before reaching
   for another instance of a shape already covered: calculation, static
   CSP (`logic-grid-solver`), sequential action search (`strips-planner`),
   structural graph algorithms (`graph-algorithms`), and combinatorial
   generation under a guaranteed invariant (`spaced-arrangement`). No new
   sixth shape has been identified in five cycles now (four extend cycles
   plus this cycle's tooling cycle).
8. **Do not re-propose:** Secret Santa/derangement-with-exclusions,
   bill-splitting/debt-simplification, pairwise/covering-array test
   generation, regex generation/ReDoS, synthetic-data generation with
   guaranteed correlation, OR-Tools-based optimization/bin-packing/
   knapsack/job-shop scheduling, round-robin scheduling, cryptarithmetic,
   sudoku/latin-square/maze generation, word/character/token counting,
   text-diff, cron-expression/unit/subnet/generic calculators, or
   regex-ReDoS/WCAG-contrast checking -- all checked and rejected in
   earlier cycles for saturation or scope-overlap, not infeasibility.
9. **Apportionment/seat-allocation (D'Hondt, Sainte-Laguë, Hamilton) and
    stable matching (Gale-Shapley)** — plausible shapes, no sharp real
    "LLMs get this wrong" complaint found as of 2026-09-22. Worth
    revisiting only with a real source.
10. **`scripts/mcp_client.py` is now available for every future cycle's
    proof-writing** — use it (`run` mode) instead of a one-off stdio
    client script when driving a server live for a `tools/*/proof/`
    transcript; it already handles the `structured_content`-vs-text-JSON
    extraction and prints the same `--- label ---` shape those files use.
11. **`progress/quality-debt.md`'s new entry:** TASKS.md step 9 ("check
    usage") has no real mechanism behind it from inside this repo -- no
    telemetry shows whether a shipped tool has actually been called by an
    external agent. Worth the owner's attention if a real fix (agent-side
    call logging, or the owner just saying what got used) becomes
    possible; not something a future cycle can fix alone.
12. **If nothing clears the bar:** re-read all eight tools' "what it
    doesn't do" sections fresh, and diff the root README's tool list
    against `tools/*/manifest.json`.

Do NOT re-propose natural-language date parsing for `time-arithmetic` — its
README frames the absence as a deliberate design boundary, not a gap
(2026-09-15 course-correction, see `progress/notes-for-owner.md`).
