# Current state

**Last cycle:** 2026-09-29 (seventeenth run)

## Cycle 17: no new tool — added `scripts/gen_mcp_config.py` (combined MCP config + telemetry wiring, `--check` verified 8/8 servers). Next: check `read_usage_summary` for real data once the owner enables `CLAUDE_TOOLS_USAGE_LOG`; otherwise continue [distribute-and-harden] (eval harness / registry packaging).


## This cycle (16): built `[usage-telemetry]` — TASKS.md step 9 finally has a real mechanism

`special-projects/wishlist.md` had exactly one open OWNER item going into
this cycle: `[usage-telemetry]` (2026-09-26), deliberately deferred by
cycle 15 for its own design pass. It named its own caller ("the loop itself
+ the owner's agent stack") and directly closed `progress/quality-debt.md`'s
standing "check usage has no real mechanism" note — the strongest possible
TASKS.md rule-3 hit, no web search needed (rule 2).

Built `tools/usage-telemetry/`, a genuine ninth MCP server whose whole job
is reading a shared log the other eight now write to:

- **`telemetrykit.py`** (stdlib only) — `record`/`track` (a decorator
  appending `{ts, server, tool, ok, error?}` — never a payload — via a
  single `os.write` to an `O_APPEND` fd, atomic under `PIPE_BUF` across the
  several OS processes this collection's stdio servers actually are;
  a no-op unless `CLAUDE_TOOLS_USAGE_LOG` is set or a `log_path` is passed
  explicitly, so nothing changes unless a caller opts in), `summarize`
  (per-server/per-tool aggregate counts), `tail` (last N raw entries).
- **`server.py`** exposes `read_usage_summary`/`tail_usage_events`.
- **Wired into all 53 `@server.tool()` functions** across the other seven
  servers (`@track("<server-name>")` between `@server.tool()` and each
  `def`) — one shared module, not seven copies of logging code, with a
  no-op fallback if `usage-telemetry` is ever missing so any tool copied
  out of this repo standalone still works.

Along the way, found and fixed a real bug in `scripts/mcp_client.py`: it
silently dropped any caller-set env var (including this cycle's own
`CLAUDE_TOOLS_USAGE_LOG`) because `mcp`'s `stdio_client` only inherits a
small safe allowlist by default — would have made this cycle's own proof
falsely look like telemetry wasn't working. Fixed by forwarding the
caller's environment explicitly (appropriate here since it's a trusted
local dev harness driving this repo's own servers, not a client connecting
to arbitrary third-party servers).

Full end-to-end proof, not just unit tests in isolation:
`tools/usage-telemetry/proof/run_2026-09-28.txt` drives `secure-random`
and `time-arithmetic` live (two separate processes, success + a deliberate
error) into one shared log, then drives `usage-telemetry` itself and
confirms its aggregate matches exactly — both via an explicit `log_path`
and via the `CLAUDE_TOOLS_USAGE_LOG` env var (the real owner-config path).
17 new unit tests; full collection suite now 309 tests (up from 296),
all passing, no regression in any of the seven touched servers.

**Not done by this repo, and can't be:** the mechanism existing doesn't
mean anything is being collected yet — that needs `CLAUDE_TOOLS_USAGE_LOG`
actually set in the owner's real MCP client config, across every server
entry, which is outside this repo's control. See
`progress/notes-for-owner.md`'s 2026-09-28 entry. Moved `[usage-telemetry]`
to wishlist.md's Done section with that caveat spelled out, same shape as
`[ai-tcg-caller]`'s "enabling side shipped, cross-repo wiring is on someone
else" pattern last cycle.

## Before cycle 16 (state as of cycle 15, 2026-09-27)

## This cycle (15): built the enabling side of `[ai-tcg-caller]`

`special-projects/wishlist.md` gained two fresh OWNER entries since cycle
14 ([ai-tcg-caller], [usage-telemetry]) plus a standing directive
([distribute-and-harden]). `[ai-tcg-caller]` is the strongest "name the
caller" hit this collection has had (TASKS.md rule 3): an owner-named
external project (the AI TCG balance harness, TypeScript), an owner-named
tool (`discrete-probability.compare_two_proportions`), and an owner-
described exact question (a win-rate gap at 300 vs 900 seeds, ~2.9pt
standard error). Built for it, no web search needed (rule 2: a wishlist
item beats a sourced candidate).

Shipped `tools/discrete-probability/examples/ts-client/` — a minimal,
reusable Node/TypeScript client (`@modelcontextprotocol/sdk`'s `Client` +
`StdioClientTransport`, wrapped as `McpStdioSession`) so an external TS
project can call any tool on this (or any) server here and get a typed
result, preferring `structuredContent` and falling back to parsing the
text content block as JSON — the same extraction rule
`scripts/mcp_client.py` uses on the Python side, kept consistent across
both language clients. `src/example.ts` models the exact scenario
`[ai-tcg-caller]` names; `src/prove.ts` drove the live server for both the
success path and a deliberate error case (`trials_a=0` correctly throwing,
not swallowed). Proof: `tools/discrete-probability/examples/ts-client/
proof/run_2026-09-27.txt`. `discrete-probability`'s own Python code is
unchanged (all 56 unit tests still pass) — only its README and
`manifest.json` (new `examples` array entry) were touched.

**Not done by this repo, and can't be:** actually wiring this client into
AI TCG's own harness so it makes a real call. This repo has no access to
that codebase — see `progress/notes-for-owner.md`'s new entry. Moved
`[ai-tcg-caller]` to wishlist.md's Done section with that caveat spelled
out, since the deliverable the entry itself asked for ("deliver the
enabling side here") is complete.

`[usage-telemetry]` (the other fresh OWNER item) was deliberately left for
a future cycle — it needs its own design pass (where the log lives, what
it looks like across all 7 servers) rather than being squeezed in
alongside this cycle's build; see "Next step" below.

## Before cycle 15 (state as of cycle 14, 2026-09-26)

## Where things stand

Nine `tools/*` MCP servers as of cycle 16 (`usage-telemetry`, described
first below, is the newest). The rest of this list is unchanged since
cycle 14 (2026-09-26) except where noted:

- `tools/usage-telemetry` — MCP server that reads the opt-in local call
  log the other eight servers can now append to (`CLAUDE_TOOLS_USAGE_LOG`;
  `{ts, server, tool, ok, error?}`, never a payload) and aggregates it into
  real per-server, per-tool invocation counts via `read_usage_summary` and
  `tail_usage_events`. Built cycle 16 (2026-09-28) — see this file's top
  section and `progress/quality-debt.md`'s newly-fixed entry for the full
  design and what it still can't do (rotation, cross-machine aggregation,
  and — outside this repo's control — actually being turned on in the
  owner's real MCP config).

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

**Cycle 14: no new `tools/` or `scripts/` entry -- a collection-wide
verification pass, per TASKS.md rule 10.** `special-projects/wishlist.md`
still had only the one non-buildable `[stats-normal-vs-exact-pvalue]`
item, and two fresh, targeted web searches (Gale-Shapley stable matching;
generic MCP-server gaps) turned up nothing that clears rule 3's "name the
caller" bar for any of the deferred extend-candidates below. Rather than
default to another `scripts/`-tooling cycle (which the previous cycle's
own plan warned against becoming a habit) or invent a need, this cycle
ran the full 296-test suite (all pass, unchanged) and used
`scripts/mcp_client.py` -- previously only ever driven one tool at a
time, alongside a change to that tool -- as an independent, collection-
wide regression check: live-drove all 7 MCP servers' `list_tools` and
programmatically cross-checked each one against its own
`tools/*/manifest.json` `tools_exposed` field (all 7 match exactly), plus
diffed root `README.md`'s tool list against all 8 manifests (also exact
match, no drift). No bugs found. Proof: `scripts/proof/run_2026-09-26.txt`.

## Next step

Options for cycle 17, roughly in order of how promising they look:

1. **Check `special-projects/wishlist.md` FIRST, before anything else.**
   As of this cycle it has one open item left: `[stats-normal-vs-exact-
   pvalue]` (a design lesson for a not-yet-built tool, not a buildable
   gap by itself) — `[usage-telemetry]` shipped this cycle and moved to
   Done. If a fresh wishlist item has appeared since (from the owner or
   from a recurring cycle), it beats everything below per TASKS.md rule 2.
2. **`[distribute-and-harden]` (OWNER standing directive) is now the
   strongest candidate for cycle 17.** It was explicitly gated on
   `[usage-telemetry]` existing as the prerequisite for real usage data —
   that's now built, but check `read_usage_summary` first: if the owner
   has turned `CLAUDE_TOOLS_USAGE_LOG` on since this cycle (see
   `progress/notes-for-owner.md`'s 2026-09-28 entry), real call counts
   should now drive which tool gets hardened/distributed/packaged for an
   MCP registry first, rather than guessing. If it's still empty (the env
   var hasn't been wired into the owner's actual MCP config yet), that
   itself is worth restating plainly rather than treated as "no signal,
   proceed anyway" — either wait one more cycle to see if it's been
   turned on, or pick a harden/distribute target on the same reasoning
   prior cycles used before telemetry existed (most-referenced-in-
   quality-debt, or least-recently-touched).
3. **`discrete-probability`'s real remaining gaps** (see its README's "What
   it doesn't do"): `compare_two_proportions` doesn't handle
   paired/matched samples (needs McNemar's test, not built), and its
   permutation-test budget caps out around `verify_trials *
   min(trials_a, trials_b) <= 10,000,000`. Neither has a surfaced real need
   yet -- see `progress/quality-debt.md`.
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
7. **Do not re-propose:** Secret Santa/derangement-with-exclusions,
   bill-splitting/debt-simplification, pairwise/covering-array test
   generation, regex generation/ReDoS, synthetic-data generation with
   guaranteed correlation, OR-Tools-based optimization/bin-packing/
   knapsack/job-shop scheduling, round-robin scheduling, cryptarithmetic,
   sudoku/latin-square/maze generation, word/character/token counting,
   text-diff, cron-expression/unit/subnet/generic calculators, or
   regex-ReDoS/WCAG-contrast checking -- all checked and rejected in
   earlier cycles for saturation or scope-overlap, not infeasibility.
8. **Apportionment/seat-allocation (D'Hondt, Sainte-Laguë, Hamilton) and
    stable matching (Gale-Shapley)** — plausible shapes, still no sharp
    real "LLMs get this wrong" complaint as of 2026-09-26. Worth
    revisiting only with a real source.
9. **`scripts/mcp_client.py` is available for every future cycle's
    proof-writing** — use it (`run` mode) instead of a one-off stdio
    client script when driving a *Python* server live. Now forwards the
    caller's environment to the spawned server (fixed cycle 16 — see
    `progress/quality-debt.md`), so a var like `CLAUDE_TOOLS_USAGE_LOG`
    set in the shell actually reaches it. This cycle's TS example still
    needed its own equivalent extraction logic on the Node side
    (`tools/discrete-probability/examples/ts-client/src/client.ts`) since
    `mcp_client.py` is Python-only — worth generalizing only if a *second*
    TS-caller need appears (rule per this project's own pattern: don't
    build the shared version until a genuine second recurrence).
10. **`progress/quality-debt.md`'s standing entry (2026-09-27):** the TS
    example under `discrete-probability/examples/ts-client` isn't covered
    by CI (`test.yml` only runs `tools/*/tests`) -- worth a lightweight CI
    job if this "non-Python example client" pattern recurs for another
    tool.
11. **If nothing clears the bar:** re-read all nine tools' "what it
    doesn't do" sections fresh.

Do NOT re-propose natural-language date parsing for `time-arithmetic` — its
README frames the absence as a deliberate design boundary, not a gap
(2026-09-15 course-correction, see `progress/notes-for-owner.md`).
