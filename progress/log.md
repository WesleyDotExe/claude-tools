# Progress log

Newest entry on top. One entry per cycle: what was done, honestly.

## 2026-09-25 — thirteenth run

- Ran `tools/collection-index/index.py` first: still 8 tools, output
  matches `tools/*/manifest.json` exactly. Re-read `special-projects/
  current.md`, `progress/quality-debt.md`, and `special-projects/
  wishlist.md` per the loop.
- `wishlist.md` had two open items left over from last cycle
  (`[build-env]`, `[mcp-proof]`), deliberately not built as `tools/`
  entries because their caller is this repo's own build process. Last
  cycle's `current.md` said to build them only on a genuine *second*
  recurrence from a different cycle. This cycle supplied exactly that:
  a fresh container had neither `mcp` nor `cffi` installed (confirmed via
  `python3 -c "import mcp"` failing before installing, the same error
  `[build-env]` already named), and writing this cycle's own live-session
  proof needed the same "parse `content[0].text` as JSON by hand"
  workaround `[mcp-proof]` described.
- No fresh wishlist item and no new web search this cycle turned up a
  new-tool candidate with a named *external* caller beyond what
  `current.md`'s next-step list had already checked and deferred (the
  saturated shapes, the deferred `graph-algorithms`/`spaced-arrangement`
  extensions, the availability-finder rejected for saturation) — so this
  cycle followed TASKS.md rule 10 (harden/extend/distribute over
  inventing a need) and built the confirmed internal friction instead of
  shipping filler.
- Built `scripts/mcp_dev_setup.sh` (idempotent `pip install --user mcp
  cffi` preflight, skips work already done) and `scripts/mcp_client.py`
  (a reusable stdio MCP client: `run_calls()` for library use, plus a
  CLI with `list-tools`, `call`, and `run` subcommands). `run_calls`
  extracts a typed result from a `CallToolResult` — `structured_content`
  first, falling back to parsing the text content block(s) as JSON when
  a tool doesn't produce structured output — the exact `[mcp-proof]`
  footgun. `run` replays a whole JSON list of `{"label", "tool", "args"}`
  calls against one server in one shared session and prints/saves them
  in this repo's existing `--- label ---\n<value>` proof-file shape, so
  a proof no longer needs a one-off throwaway script.
- Dogfooded it immediately (TASKS.md step 6: use an existing/new tool to
  build or test another): drove both `tools/secure-random/server.py` and
  `tools/discrete-probability/server.py` live through `mcp_client.py`'s
  CLI (`list-tools`, `call`, and `run`), including a deliberately invalid
  call to each surfacing as a real MCP tool error rather than a crash,
  and `compare_two_proportions`'s worked example reproducing last cycle's
  exact numbers. Saved as `scripts/proof/run_2026-09-25.txt`.
- Wrote `scripts/README.md` documenting both scripts (usage, the
  `calls.json` format, the proof reference) alongside the pre-existing,
  previously-undocumented `build_dashboard.py`/`build_site.py`.
- No CI changes: `mcp` stays a dev-only dependency, exactly as each
  `tools/*/requirements.txt` already treats it, so `.github/workflows/
  test.yml`'s `tools/*/tests` loop is untouched and doesn't need `mcp`
  installed. `scripts/` isn't a `tools/*/tests` directory, so nothing
  here needed wiring into CI.
- Moved both `[build-env]` and `[mcp-proof]` to `wishlist.md`'s Done
  section, referencing the two scripts and the proof file.
- Updated `progress/notes-for-owner.md` (explaining the "no ninth tool
  this cycle" decision and the recurrence check that justified building
  now rather than last cycle), `special-projects/current.md`,
  `special-projects/cycles.json`. Root `README.md` unchanged — this
  cycle didn't add or change a `tools/` entry, only internal build
  tooling.
- Rebuilt `_site/dashboard.html` via `scripts/build_site.py` — runs
  cleanly, confirmed gitignored and not staged.
- Checked prior tools for actual use since shipping: no evidence either
  way is visible from inside this repo (no caller-side telemetry) —
  same limitation noted in earlier cycles' logs. Nothing indicates any
  of the eight `tools/*` MCP servers has gone stale enough to retire.

## 2026-09-24 — twelfth run

- Ran `tools/collection-index/index.py` first (still 8 tools, matches
  `tools/*/manifest.json`), then re-read `special-projects/current.md`,
  `progress/quality-debt.md`, `progress/notes-for-owner.md`, per the loop.
- This cycle's real difference from the last several: `special-projects/
  wishlist.md` had just been created directly by the owner (commit `3fcf0d9`,
  not a prior agent run) with three real, concrete, sourced items — the
  first time this loop's step 2 ("read the wishlist first") actually had
  live signal to read instead of an empty file. Picked `[balance-stats]`
  over the other two open items (`[build-env]`, `[mcp-proof]`) because it's
  the only one with a *named external caller* per TASKS.md rule 3 (the
  owner's AI TCG balance-testing run) — the other two are real friction but
  are about this repo's own build process, not something another agent
  calls over MCP, so they were documented rather than built as tools (see
  `notes-for-owner.md`).
- Extended `tools/discrete-probability` (rather than a ninth tool) with
  `compare_two_proportions`: a two-proportion z-test (p-value), a Wilson CI
  per group, a Newcombe (1998) hybrid-score CI for the difference (reusing
  the tool's own existing `_wilson_interval`, built cycle four), and a plain
  verdict. Added two new stdlib-only helpers it needed: `_norm_cdf`
  (`math.erf`) and `_norm_ppf` (Peter Acklam's rational inverse-normal-CDF
  approximation, ~1.15e-9 accurate) so `confidence` isn't hardcoded to 95%.
  `verify=true` runs an independent CSPRNG permutation (label-reshuffling)
  test via a new `_partial_sample_sum` helper (partial Fisher-Yates, swaps
  undone in place — O(min(trials_a, trials_b)) per trial, no per-trial
  O(n) copy), budget-capped at `verify_trials * min(trials_a, trials_b) <=
  10,000,000` (benchmarked locally: ~1.3M `secrets.randbelow` calls/sec in
  this container, so the cap keeps a single call to a few/~10 seconds).
- **Caught and fixed a real design issue while building, before committing,
  not after shipping:** the first draft's `verify=true` output asserted the
  z-test's p-value should fall inside a confidence interval around the
  permutation test's empirical p-value estimate — and a real worked example
  (186/300 vs 165/300) failed that check even though both computations were
  correct. Hand-derived the true exact permutation p-value via the
  hypergeometric distribution for that exact case (0.09741, independent of
  any of this tool's own code) and confirmed the permutation test's
  empirical estimate was correct (within its own CI of that value) while
  the z-test's pooled-normal-approximation p-value (0.0819) is a
  legitimately different, smaller quantity — a well-known asymptotic-vs-exact
  gap, not a bug. Redesigned the check around
  `agrees_on_significance_call` (do the two methods reach the same
  significant/not-significant conclusion) with an explanatory note in the
  tool's own response, instead of a check that would have flagged
  correct code as broken. Recorded the general lesson in
  `special-projects/wishlist.md`'s new `[stats-normal-vs-exact-pvalue]` entry
  for any future significance-test tool in this collection.
- 15 new unit tests (`tools/discrete-probability/tests/test_probkit.py`; 56
  in this tool now, up from 41; 296 across all eight tools now, up from
  281): known-by-hand z-test formula cross-check, each group's Wilson CI
  cross-checked directly against `_wilson_interval`, `_norm_ppf` against
  known textbook z-scores and confirmed as `_norm_cdf`'s numerical inverse,
  the permutation test's Monte Carlo estimate checked against a
  hand-derived exact hypergeometric-tail p-value on a small case
  (independent of `probkit.py`'s own code), input validation, the
  permutation budget cap raising instead of running unboundedly long, and
  `agrees_on_significance_call` holding for both a clear gap and a clear
  non-gap.
- Ran the full repo test suite locally: 296 tests, all green.
- Installed `mcp`+`cffi` locally, wrote a real stdio MCP client driver, and
  drove the live server: `list_tools`, the wishlist's own 186/300-vs-165/300
  worked example (with and without `verify=true`), a clear real gap,
  identical proportions correctly reported not-significant, a deliberately
  invalid input and a deliberately oversized permutation budget both coming
  back as genuine MCP tool errors, and `monty_hall` confirmed still working
  unchanged. Saved as
  `tools/discrete-probability/proof/run_2026-09-24.txt`.
- Updated: `tools/discrete-probability/{probkit.py,server.py,README.md,
  manifest.json,tests/test_probkit.py}`, `progress/quality-debt.md` (new
  entry), `README.md` (root tool list), `special-projects/{wishlist.md,
  cycles.json,current.md}`, `progress/notes-for-owner.md`.
- Rebuilt `_site/dashboard.html` via `scripts/build_site.py` — runs
  cleanly, confirmed gitignored and not staged.

## 2026-09-23 — eleventh run

- Ran `tools/collection-index/index.py` first (still 8 tools, output
  matches `tools/*/manifest.json` exactly), then re-read
  `special-projects/current.md`, `progress/notes-for-owner.md`,
  `progress/quality-debt.md`, and every tool's own "What it doesn't do"
  section fresh, per the loop. Root README's tool list already matched
  `tools/*/manifest.json` (confirmed by diff, not just a skim).
- Web-searched 13 queries across several candidate directions. Checked and
  rejected: general non-bipartite graph matching / Edmonds' blossom
  algorithm (real applications exist -- stable roommates, non-bipartite
  observational-study matching -- but still no sharp "LLMs/tools get this
  wrong" source, same verdict as the existing `quality-debt.md` entry);
  rectangular/partial assignment for unequal worker/task counts (same —
  real OR problem, no fresh LLM-failure source); Secret Santa / derangement-
  with-exclusions generation (real need, but the documented AI pain point
  is privacy — a volunteer sees all pairings — not correctness, and it's
  already solvable as a special case of `graph-algorithms`' own
  `maximum_bipartite_matching`); OR-Tools-style bin-packing/knapsack/job-
  shop (re-confirmed still saturated + a poor stdlib-only fit, per prior
  cycles' verdicts).
- The most promising NEW-tool candidate this cycle was cross-timezone
  meeting/availability finding (intersecting several people's busy
  intervals across timezones and DST from structured JSON, no calendar
  credentials). Found a genuinely sharp, concrete source: a MindStudio
  write-up documenting Claude Code's *own* `check_availability` tool
  computing "end of day" in UTC instead of the user's Central-time zone,
  silently returning one slot instead of seven. But further search found
  the underlying free/busy-interval-intersection *algorithm* already
  implemented by several existing MCP servers even among keyless-input
  ones (`mcp-calendar`, `when2meet-mcp`, `mcp-office-suite`'s `free_busy`,
  `pim-agents`' `findFreeSlots`) — saturated, not rejected for lack of a
  source.
- Per TASKS.md rule 9, deepened `spaced-arrangement` instead: added
  `maximize_min_distance`, which finds the LARGEST `min_distance` achievable
  for a given items list (no caller-chosen value needed) via binary search
  over the tool's own existing exhaustive feasibility proof, and proves the
  answer optimal — structurally (hits the `n-1` positional ceiling) or via
  one more exhaustive search. This closes a gap the tool's own README and
  `progress/quality-debt.md` had explicitly flagged since it was built
  ("no soft spread-evenly-beyond-the-minimum mode"), using the exact
  source already cited for the tool (Spotify's 2026 rebuilt-shuffle
  write-up: generate many candidates, pick the best-spread one) — this
  finds the best-spread one directly via proof, instead of by sampling.
- 9 new unit tests (34 total in `spaced-arrangement`, up from 25; 281
  across all eight tools, up from 272). While writing them, caught and
  fixed a real bug before committing: the initial `min_distance=1`
  feasibility check wasn't distinguishing "budget genuinely exhausted"
  from "structurally infeasible" (which `min_distance=1` never can be) —
  an undersized `max_search_nodes` was raising the wrong internal
  assertion instead of the intended budget error.
- Ran the full repo test suite locally (`python3 -m unittest discover -s
  tests` per `tools/*/tests`, matching `.github/workflows/test.yml`): 281
  tests, all green.
- Installed `mcp`+`cffi` locally (`pip install --user mcp cffi`), wrote a
  real stdio MCP client driver, and drove the live server: `list_tools`,
  the unconstrained case, the structural optimality proof, the exhaustive-
  search optimality proof (with the returned arrangement independently
  re-verified via `verify_arrangement` AND the "one more is infeasible"
  claim independently re-confirmed via a direct, separate
  `arrange_with_spacing` call), a 20-item/5-category generated instance end
  to end, and a too-small `max_search_nodes` budget coming back as a
  genuine MCP tool error. Saved as
  `tools/spaced-arrangement/proof/run_2026-09-23.txt`.
- Updated: `tools/spaced-arrangement/{spacedkit.py,server.py,README.md,
  manifest.json,tests/test_spacedkit.py}`, `progress/quality-debt.md`
  (marked the "spread evenly" gap fixed, documented what's still open),
  `README.md` (root tool list), `special-projects/cycles.json` (new
  eleventh-run entry), `special-projects/current.md`,
  `progress/notes-for-owner.md`. No CI workflow changes needed —
  `.github/workflows/test.yml` already auto-discovers `tools/*/tests`, and
  this cycle extended an existing tool rather than adding a new one.
- Rebuilt `_site/dashboard.html` via `scripts/build_site.py` — runs
  cleanly, confirmed gitignored and not staged.

## 2026-09-22 — tenth run

- Ran `tools/collection-index/index.py` first (8 tools), then re-read
  `special-projects/current.md`, `progress/notes-for-owner.md`,
  `progress/quality-debt.md`, and every tool's own "What it doesn't do"
  section fresh, per the loop. `current.md` flagged no obviously-unexplored
  new problem shape this cycle, so this cycle searched for a real gap
  within an existing shape rather than forcing a new one.
- Web-searched 12 queries. Checked and rejected: bill-splitting / debt
  simplification (real, well-documented need, but `expense-splitter-mcp`
  and several Splitwise-wrapper MCP servers already implement the standard
  greedy debt-simplification algorithm — saturated); apportionment/
  seat-allocation methods (D'Hondt, Sainte-Laguë, Hamilton — real methods,
  but no sharply-articulated "LLMs get this wrong" source found, only
  reference material); stable matching / Gale-Shapley (same — no sharp
  real-complaint source found this cycle). Found a genuinely strong one:
  the weighted bipartite assignment problem. `jeremylach2/fantasyFootballMCP`'s
  own README states plainly that handing a model 16 players and slot-
  eligibility rules and asking it to solve the assignment problem in
  context costs ~31,900 tokens and still gets it wrong, because the
  correct answer is a maximum-weight bipartite matching, not a sort — its
  own worked example shows a naive/greedy lineup scoring 20 points against
  the optimum's 29. No generic (non-domain-specific), keyless MCP server
  for bipartite matching or the assignment problem was found (only that
  one fantasy-football-specific tool, and `mcp-solver`, which needs
  SMT-LIB/CP formalization — the same "LLM-as-formalizer is also
  unreliable" problem this collection's other tools already sidestep).
  This also directly closes a gap `tools/graph-algorithms/README.md`
  already named explicitly as open ("No maximum matching or general
  LP-style network optimization") since the graph-coloring cycle. See
  `special-projects/cycles.json`'s 2026-09-22 entry and
  `progress/notes-for-owner.md` for the full search/reasoning.
- Extended `tools/graph-algorithms` (per TASKS.md rule 1's "extend rather
  than duplicate" guidance, and the tool's own already-flagged gap) rather
  than building a seventh tool: added `maximum_bipartite_matching` (Kuhn's
  algorithm: DFS augmenting-path search) and `verify_bipartite_matching`
  (a structurally different BFS alternating-path search — Berge's theorem
  — returning a concrete augmenting path when the matching is NOT maximum,
  or constructing a same-size minimum vertex cover via Koenig's theorem,
  independently rechecked edge-by-edge, when it is); `assignment_problem`
  (the classic O(n^3) Hungarian algorithm for the square n-to-n weighted
  assignment problem, minimize or maximize, missing edges simply
  disallowed — infeasibility, when no full assignment avoiding them
  exists, is independently confirmed by reusing `maximum_bipartite_matching`
  over the real edges alone, the collection building on itself per
  TASKS.md step 6) and `verify_assignment` (a pure LP-duality /
  complementary-slackness certificate check — given `potentials`, never
  re-runs the Hungarian algorithm at all, the same role `max_flow`'s
  min-cut proof already plays for a different problem). Added
  `describe_bipartite_format` for the new `left_nodes`/`right_nodes`/
  `edges` vocabulary (deliberately different from `describe_graph_format`'s
  single `nodes` list, since left and right are different roles, not a
  symmetric undirected graph).
- Added 28 unit tests (`tools/graph-algorithms/tests/test_graphkit.py`; 89
  in this tool now, up from 61; 272 across all eight tools now, up from
  244): a known non-perfect maximum matching and a known perfect matching
  when one exists; `verify_bipartite_matching` catching a reused node and
  a fake edge, and returning a concrete augmenting-path witness for a
  deliberately non-maximum guess; a known textbook 3x3 assignment-problem
  cost matrix brute-forced BY HAND over all 6 permutations for both
  minimize (9) and maximize (21), matching the solver exactly; an
  infeasible case independently confirmed via `maximum_bipartite_matching`'s
  own matching size; `verify_assignment` rejecting an all-zero-potentials
  certificate AND rejecting the solver's own genuine potentials applied to
  a different, deliberately suboptimal assignment; a hand-built
  counterexample proving the naive "greedily take the globally cheapest
  edge first" heuristic totals 9 while the true optimum is 7 — reproducing
  the exact shape of failure `fantasyFootballMCP`'s README documents for
  real; input validation for every new malformed-input path.
- Installed `mcp` + `cffi` locally (per the known container gotcha) and
  wrote a real stdio MCP client driver, saved as
  `tools/graph-algorithms/proof/run_2026-09-22.txt`: `list_tools`
  (confirming the five new tools), `describe_bipartite_format`, the known
  bipartite matching solved and proven maximum via Koenig's theorem live,
  a deliberately non-maximum guess caught with its augmenting-path
  witness, the known 3x3 assignment problem solved for both minimize and
  maximize with their LP-duality proofs shown, the greedy-vs-optimal
  counterexample solved live, an infeasible assignment case correctly
  reported, `verify_assignment` correctly rejecting a bad certificate and
  accepting the solver's own genuine one, a deliberately invalid input
  (unequal left/right sizes) correctly coming back as a real MCP tool
  error instead of a wrong answer, and `shortest_path` confirmed still
  working unchanged alongside the five new tools.
- Full repo test suite green locally: 272 tests across all eight tools
  (`for d in tools/*/tests; do (cd "$(dirname "$d")" && python3 -m
  unittest discover -s tests); done`).
- Found and fixed a small pre-existing gap while updating the root
  `README.md`: `spaced-arrangement` (built cycle nine) was missing from
  its tool list entirely — added it alongside this cycle's
  `graph-algorithms` update. Not caught by any test (it's documentation,
  not code) — caught only by actually re-reading the file this cycle
  rather than assuming it was current.
- Updated `special-projects/cycles.json` (this cycle's entry) and rebuilt
  the dashboard (`python3 scripts/build_site.py`); updated
  `special-projects/current.md`, this file, and
  `progress/quality-debt.md`/`progress/notes-for-owner.md`.

## 2026-09-21 — ninth run

- Ran `tools/collection-index/index.py` first (7 tools), then re-read
  `special-projects/current.md`, `progress/notes-for-owner.md`,
  `progress/quality-debt.md`, and every tool's own "What it doesn't do"
  section fresh, per the loop.
- Web-searched 14 queries chasing the "combinatorial generation under a
  guaranteed invariant" shape `current.md` flagged as unexplored. Checked
  and rejected: pairwise/covering-array test generation (real — a Ministry
  of Testing write-up shows ChatGPT giving all 32 combos of 5 booleans
  instead of a 6-row pairwise covering array — but `PictMCP` already wraps
  Microsoft's PICT for exactly this over MCP); regex generation/ReDoS
  (already rejected in an earlier cycle, re-confirmed still saturated);
  synthetic dataset generation with a guaranteed exact correlation
  structure (real technique — Cholesky-based Generative Correlation
  Manifolds — but multiple existing MCP servers already do it). Found a
  genuinely open one: arranging a category-heavy list so no two
  same-category items land too close together — real and sharply
  documented (years of Spotify community-forum "shuffle keeps repeating
  the same artist" threads, Spotify's own 2026 engineering coverage of
  rebuilding shuffle around this, a classic named algorithmic problem —
  LeetCode 767/621/358 — for exactly this reason), and no existing MCP
  server (keyless or otherwise) offers it generically. See
  `special-projects/cycles.json`'s 2026-09-21 entry and
  `progress/notes-for-owner.md` for the full search/reasoning.
- Built `tools/spaced-arrangement`: a new MCP server (`spacedkit.py`) with
  `describe_arrangement_format`, `arrange_with_spacing` (budgeted
  backtracking search, CSPRNG-randomized tie-breaking via
  `secrets.SystemRandom`, `max_search_nodes` contract matching
  `graph-algorithms`' `graph_coloring`/`strips-planner`'s BFS — full search
  exhaustion proves infeasibility, running out of budget raises instead of
  guessing), `verify_arrangement` (independent direct-definition check, no
  search), and `generate_arrangement_problem` (seeded stdlib RNG, same
  convention as `generate_random_graph`).
- Verified this is genuinely non-trivial, not a thin wrapper: constructed
  and tested a 7-item, 3-category counterexample (`3xA, 3xB, 1xC,
  min_distance=3`) where every category individually passes the naive
  `count <= ceil(n/min_distance)` check yet no arrangement exists — proven
  only by real exhaustive search, confirmed impossible in just 4 search
  nodes.
- Added 25 unit tests (`tools/spaced-arrangement/tests/test_spacedkit.py`;
  244 across all eight tools now, up from 219): the boundary-tight feasible
  case, the trivial `min_distance=1` case, CSPRNG randomness actually
  confirmed to vary across repeated calls, the multi-category
  counterexample above, a too-small search budget raising instead of
  guessing, `verify_arrangement` catching a deliberately bad guess and a
  non-permutation, input validation for every malformed path, and the
  seeded generator's reproducibility/coverage/composability.
- Installed `mcp` + `cffi` locally (per the known container gotcha, see
  `progress/notes-for-owner.md`'s 2026-09-18 entry) and wrote a real stdio
  MCP client driver, saved as
  `tools/spaced-arrangement/proof/run_2026-09-21.txt`: `list_tools`, the
  worked example solved and independently verified, a bad guess caught,
  the multi-category infeasibility proof shown live over the real
  transport, a too-small budget correctly surfacing as an MCP tool error,
  and two repeated calls on the same input producing two different valid
  arrangements (CSPRNG shuffling genuinely observed, not just claimed).
- Full repo test suite green locally: 244 tests across all eight tools
  (`for d in tools/*/tests; do (cd "$(dirname "$d")" && python3 -m
  unittest discover -s tests); done`).
- Updated `special-projects/cycles.json` (this cycle's entry) and rebuilt
  the dashboard (`python3 scripts/build_site.py`); updated
  `special-projects/current.md`, this file, and
  `progress/quality-debt.md`/`progress/notes-for-owner.md`.

## 2026-09-20 — eighth run

- Ran `tools/collection-index/index.py` first, per the loop: 7 tools
  existed. Re-read `special-projects/current.md`'s next-step list, which
  flagged graph coloring (deferred from the previous cycle when
  `graph-algorithms` was first built) as the most-ready option.
- Web-searched three fresh angles before committing to that: general "I
  wish Claude could" threads (unproductive, mostly SEO/explainer content,
  same finding as several earlier cycles), symbolic/computer algebra
  (simplify/factor/solve — real, documented failure via the ASyMOB
  benchmark, but saturated by sympy-mcp/math-mcp/scimath-mcp/symkit-mcp/
  MCP_Math and a poor fit for this collection's stdlib-only discipline
  since it needs SymPy), and computational geometry (convex hull/polygon
  intersection — plausible shape, but no sharply-documented "LLMs fail at
  this" source found, and PostGIS MCP already exposes convex hull). See
  `progress/notes-for-owner.md`'s 2026-09-20 entry for the full reasoning.
- Picked graph coloring: real (same 2025/2026 graph-reasoning benchmark
  suite that motivated `graph-algorithms` itself documents it), extends an
  existing tool rather than risking duplication, and the design was
  already sketched out in the previous cycle's `progress/quality-debt.md`
  entry (DSATUR + forward-checking backtracking, a `max_search_nodes`
  budget matching `strips-planner`'s contract, a minimality proof via a
  clique lower bound plus exhaustive uncolorability at every smaller color
  count) — cleared TASKS.md's feasibility gate cleanly.
- Built `graph_coloring` (bounded-k backtracking solver), `verify_coloring`
  (independent direct-definition check, no search), and `chromatic_number`
  (minimum-colors search: proves its lower bound for free by exhibiting a
  clique, then searches upward, proving every smaller count impossible by
  full search-tree exhaustion rather than a budget cutoff) in
  `tools/graph-algorithms/graphkit.py`, wired into `server.py` as three new
  MCP tools.
- Added 17 unit tests (61 total, up from 44) to
  `tools/graph-algorithms/tests/test_graphkit.py`: a triangle colorable
  with 3 colors but proven uncolorable with 2, a bipartite 4-cycle colored
  with 2, weight/directedness confirmed ignored, a too-small search budget
  raising instead of guessing; `verify_coloring` catching a shared color,
  a missing node, an unexpected node, a bad color type, and accepting both
  int and string labels; chromatic numbers for a triangle (3, proven by
  the clique bound alone) and a 4-cycle (2, same), plus a 5-cycle (3) --
  deliberately chosen because it's triangle-free (clique bound only 2), so
  it's the one case that actually exercises real exhaustive search at k=2
  rather than the proof coming from the clique bound alone; a generated
  random graph's chromatic number cross-checked by confirming one fewer
  color is genuinely uncolorable.
- Drove the live MCP server over stdio with a real client (not just
  scaffolding): all three new tools plus a pre-existing one
  (`shortest_path`) called and captured in
  `tools/graph-algorithms/proof/run_2026-09-20.txt`, including the
  too-small-budget case correctly coming back as an MCP tool error
  (`is_error: true`) instead of a silently wrong "not colorable" answer.
- Updated `tools/graph-algorithms/README.md` and `manifest.json`
  (`tools_exposed`, `updated` date, `proof` path), root `README.md`,
  `progress/quality-debt.md` (moved the graph-coloring entry from "not
  fixed" to "fixed this cycle"), `progress/notes-for-owner.md`, appended
  this cycle to `special-projects/cycles.json`, rebuilt
  `_site/dashboard.html`.

## 2026-09-19 — seventh run

- This session's designated branch had already been merged into `main`
  (all 5 prior cycles' work) and the branch deleted by the time this run
  started, so per the standing merged-branch protocol, restarted the
  branch fresh from `main` before doing any new work — nothing lost, just
  a fresh base.
- Ran `tools/collection-index/index.py` first, per the loop: 6 tools
  existed, nothing screamed out to extend over a fresh candidate.
- Searched broadly first ("I wish Claude could...", general LLM-limitation
  reddit/forum queries, long-conversation entity-tracking research) — these
  mostly surfaced generic MCP-marketing content or a much larger, fuzzier
  problem (conversational memory) than this collection's "small fixed
  vocabulary, exact answer, independently checkable" shape fits. Narrowed
  to graph algorithms after finding four separate purpose-built 2025/2026
  benchmarks (GraphArena, GraphOmni, GrAlgoBench, GTA) specifically
  measuring LLM accuracy on shortest path/topological sort/MST/max flow,
  all reporting sharp accuracy drops past a handful of nodes.
- Checked existing MCP coverage before building: found `mcp-solver`
  (requires SMT-LIB/ASP formalization — the same LLM-as-formalizer problem
  `logic-grid-solver`/`strips-planner` already sidestep) and a research
  prototype requiring a live Neo4j Graph Data Science instance (not
  keyless). No MCP server exposing plain graph algorithms through a simple
  node/edge JSON vocabulary with an independent verifier was found —
  confirmed real gap. See `special-projects/cycles.json` for the full
  search/reasoning record, including why sudoku/latin-square/maze
  *generation* was checked again and still rejected as overlapping
  `logic-grid-solver`'s shape.
- Built `tools/graph-algorithms`: `graphkit.py` (four algorithm/verifier
  pairs — Dijkstra verified via independent Bellman-Ford, Kahn's verified
  against the direct topological-order definition with a concrete DFS-
  found cycle as proof of non-DAG-ness, Kruskal verified via the
  cycle-property exchange argument, Edmonds-Karp verified via flow
  conservation plus the max-flow min-cut theorem — stdlib only) and
  `server.py` (MCP stdio wrapper, 10 tools).
- Wrote 44 unit tests (`tests/test_graphkit.py`): known-by-hand answers on
  small hand-checkable graphs for all four algorithms, each verifier
  independently catching a deliberately wrong/suboptimal/infeasible
  candidate answer, and shared input validation (self-loops, duplicate
  nodes, unknown node references, negative weights where disallowed,
  duplicate flow edges, missing capacity).
- Drove the live MCP server over stdio with a real client (not just
  scaffolding): `list_tools` + all 10 tools called, including a
  deliberately invalid negative-weight input confirmed to come back as an
  MCP tool error (`is_error: true`) rather than a wrong answer — captured
  in `tools/graph-algorithms/proof/run_2026-09-19.txt`.
- Full repo test suite green locally: 202 tests across all seven tools
  (158 from before + graph-algorithms' 44).
- Wrote `tools/graph-algorithms/README.md`, added it to the root README's
  tool list, appended the cycle to `special-projects/cycles.json`, updated
  `special-projects/current.md`, and rebuilt `_site/dashboard.html` via
  `scripts/build_site.py` (gitignored, not committed).
- Deliberately did NOT build graph coloring in the same cycle even though
  it's also documented in the same benchmarks — it's NP-hard and needs its
  own backtracking-search-with-budget story to build fully rather than as
  an afterthought; recorded as an explicit option for a future cycle in
  `special-projects/current.md` and this tool's own README.

## 2026-09-18 — sixth run

- Ran `tools/collection-index/index.py` first, per the loop: 5 tools
  existed, nothing to extend that clearly beat a fresh candidate.
- Searched deliberately for a problem shape that isn't a single
  calculation *or* static constraint satisfaction, per the previous
  cycle's own note-for-owner (don't just repeat the CSP move that produced
  `logic-grid-solver`). Sudoku surfaced as a real, sharply-documented LLM
  failure but was rejected as too close to `logic-grid-solver`'s own shape
  and heavily saturated by non-MCP solvers. Round-robin tournament
  scheduling and cryptarithmetic (SEND+MORE=MONEY) were both checked and
  rejected too -- see `special-projects/cycles.json` for the full
  reasoning on all three.
- Landed on **planning**: finding a sequence of state-changing actions
  from an initial state to a goal. Kambhampati et al.'s PlanBench/
  Blocksworld research documents LLMs failing reliably at this past a
  handful of objects -- a genuinely different failure mode (can't hold
  cumulative, interdependent state across a sequence) than anything
  already in this collection. Found exactly one existing MCP server for
  general planning (`byte4ever/gp`, Go/Graphplan), and it requires PDDL/
  ADL input -- which "LLM-as-formalizer" research shows models are also
  bad at producing, so it doesn't actually close the gap for a calling
  model. No keyless MCP server was found exposing planning through a
  small, fixed JSON vocabulary with an independent verifier.
- Built `tools/strips-planner`: `planner.py` (fact/action-schema
  validation and grounding, a breadth-first-search solver that proves its
  plan is shortest-possible or proves the goal unreachable by exhausting
  the reachable state space, a deliberately separate step-by-step
  `verify_plan` forward simulator, and a seeded Blocksworld instance
  generator) and `server.py` (MCP stdio wrapper, 4 tools). Mirrors
  `logic-grid-solver`'s "small fixed vocabulary instead of a formal
  language" and "proof, not assertion" moves, applied to a genuinely
  different algorithm (BFS state-space search, not arc-consistency +
  backtracking).
- Wrote 25 unit tests (`tests/test_planner.py`), including the classic
  Sussman anomaly solved and checked against its known-optimal 6-action
  plan, `verify_plan` independently re-confirming the solver's own plan
  and separately catching five different kinds of broken/invalid plans, a
  contradictory goal proven unreachable via full state-space exhaustion
  (distinct from a too-small search budget, which raises instead of
  guessing), and the Blocksworld generator's reproducibility and
  solvability checked across ten seeds.
- Drove the live MCP server over stdio with a real client (not just
  scaffolding): `tools/strips-planner/proof/run_2026-09-18.txt` --
  `list_tools`, `describe_planning_format`, the Sussman anomaly solved and
  independently re-verified, a deliberately broken plan caught with its
  exact unmet precondition named, a generated 5-block instance (seed
  2026) solved and verified end to end, a provably unsolvable goal
  correctly reported as such, and a too-small search budget correctly
  coming back as an MCP tool error instead of a silent wrong answer.
- **Found (not a bug in this tool, but worth recording) while building the
  proof:** the installed `mcp==2.2.0` doesn't populate
  `structuredContent`/`outputSchema` for any tool in this server, nor
  (spot-checked) for `logic-grid-solver`'s own tools under the same
  installed version -- every tool's JSON only comes back in the text
  content block. Correct data either way; recorded in
  `progress/notes-for-owner.md` so a future cycle's proof-gathering script
  doesn't assume `structured_content` and produce a misleadingly empty
  proof.
- Updated `tools/strips-planner/README.md` and `manifest.json`, root
  `README.md`'s tool list, appended this cycle to
  `special-projects/cycles.json`, rebuilt `_site/dashboard.html`.

## 2026-09-17 — fifth run: built logic-grid-solver

- Ran `tools/collection-index/index.py` first, per the loop: 4 tools
  existed. Nothing overlapped a fresh candidate need.
- Per the previous cycle's `notes-for-owner.md` warning that "single
  deterministic calculation" MCP ideas are actively saturated, deliberately
  searched for a different problem *shape* this cycle rather than another
  calculator. General "wish Claude could" and unit-conversion searches were
  unproductive. Two real candidates surfaced: NP-hard combinatorial
  optimization (knapsack/bin-packing) and logic grid ("zebra") puzzles.
  Optimization is real (EHOP benchmark, "A Knapsack by Any Other Name") but
  already served by two existing MCP servers built on Google OR-Tools (MCP
  Optimizer, Opti-MCP), and OR-Tools' native-binary dependency cuts against
  this collection's stdlib-only discipline. Logic grid puzzles are also
  real and more sharply differentiated: research on GPT-4o found success
  rates as low as 8% on this exact puzzle shape (a distinct failure mode
  from arithmetic — it's the iterative cross-checking of many simultaneous
  constraints that fails, not the math), and while general constraint
  solvers exist as MCP servers (`z3-solver-mcp-server`, `mcp-solver`), they
  require the calling model to first translate the puzzle into SMT-LIB/ASP
  — and separate research on "LLM-as-formalizer" shows models are
  specifically bad at that translation step too, so those tools just move
  the failure earlier. No MCP server exposing a logic-grid-specific solver
  with a simple structured clue vocabulary (the `same_house`/`next_to`/
  `left_of` shape a few non-MCP web solvers already use) was found.
- Built `tools/logic-grid-solver`: `puzzlekit.py` (a 10-type clue
  vocabulary — `position`, `same_position`, `different_position`,
  `immediately_left_of`, `immediately_right_of`, `left_of`, `right_of`,
  `next_to`, `not_next_to`, `distance` — solved via constraint propagation:
  arc consistency between every clue and each category's
  bijection-to-positions constraint, iterated to a fixpoint, with MRV
  backtracking when propagation alone doesn't finish) and `server.py` (MCP
  stdio wrapper exposing `describe_clue_types`, `solve_logic_grid`,
  `verify_logic_grid_solution`). `solve_logic_grid` proves uniqueness by
  default (keeps searching for a second, distinct solution instead of
  stopping at the first), and `verify_logic_grid_solution` independently
  re-derives every clue's truth value from a plain grid — a different code
  path from the solver's own search state — so it can check any proposed
  answer, including a hand-written guess, standalone.
- Wrote 28 unit tests (`tests/test_puzzlekit.py`): the classic 5-house
  Einstein zebra puzzle solved and checked against its published answer
  (German owns the zebra, Norwegian drinks water), uniqueness proven, all
  15 of its clues independently re-verified; every clue type exercised on a
  small hand-checkable puzzle; contradictory clues raising instead of
  returning a wrong answer; an under-constrained puzzle correctly reported
  as *not* unique with a concrete alternate solution; the verifier catching
  a deliberately wrong guess and malformed grids instead of rubber-stamping
  them; input validation for every malformed-input path; a `max_nodes`
  budget cap that fails predictably instead of hanging.
- Drove the live MCP server over stdio with a real client: `list_tools`,
  `describe_clue_types`, the zebra puzzle solved (5 search nodes, proven
  unique) and independently re-verified, a deliberately wrong guess caught
  by the verifier, an under-constrained puzzle correctly reported as not
  unique with its alternate solution, and contradictory clues coming back
  as an MCP tool error instead of a silently wrong answer.
  `tools/logic-grid-solver/proof/run_2026-09-17.txt`.
- **Caught and fixed two real bugs while building, not after shipping.**
  (1) The first backtracking implementation only restored its
  dependency-counter on backtrack for clues that had become fully checked,
  not every clue touched by an assignment — caught immediately by the test
  suite as a `KeyError` crash on the very first run, not by the live
  session. (2) That same naive backtracking (correct, but pruning only via
  incremental clue checks with no real constraint propagation) took over
  25 seconds and still hadn't solved the classic 5×5 zebra puzzle within a
  3,000,000-node budget — replaced with the arc-consistency
  constraint-propagation approach described above, which solves the same
  puzzle in 5 nodes and under 2ms.
- Updated root `README.md`, appended this cycle to
  `special-projects/cycles.json`, rebuilt `_site/dashboard.html`, updated
  `special-projects/current.md`.

## 2026-09-16 — fourth run: built discrete-probability

- Ran `tools/collection-index/index.py` first, per the loop: 3 tools
  existed. Nothing overlapped a fresh candidate need.
- Web-searched several candidate angles: general "wish Claude/ChatGPT
  could" complaints, hashing/checksums, readability/syllable counting,
  bitwise arithmetic, semver ranges, haversine geodistance, and discrete
  probability. The first six all landed on the same saturation outcome as
  the last two cycles -- notably discovering that a single account
  (pipeworx-io) already publishes dedicated MCP servers for
  readability/text-stats, semver, and geodistance, which is a stronger
  signal than before that the obvious "AI can't do X" calculator-shaped
  gaps are being actively picked over across the whole MCP ecosystem.
- Discrete probability broke the streak: a 2026 paper on counterintuitive
  discrete-probability problems (arxiv.org/pdf/2606.07516) found models
  average 0.96 accuracy on standard probability problems but only 0.59 on
  counterintuitive ones, and the "LLMs Can't Do Probability" writeup
  (brainsteam.co.uk) documents the same failure informally, with an active
  Hacker News discussion. Existing calculator MCP servers expose raw
  combinatorics primitives (nCr, nPr, factorial) but not pre-composed
  scenarios like the birthday paradox or Monty Hall, and none found pair
  the answer with a Monte Carlo cross-check.
- Built `tools/discrete-probability`: `probkit.py` (six exact functions --
  `birthday_collision`, `dice_sum_distribution`, `hypergeometric_probability`,
  `binomial_probability`, `bayes_update`, a generalized `monty_hall` -- using
  `fractions.Fraction`/`math.comb` for exact arithmetic, plus a from-scratch
  Wilson score confidence interval) and `server.py` (MCP stdio wrapper).
  Every function accepts `verify=true` to actually play the scenario out via
  CSPRNG draws (`secrets`, the same source `tools/secure-random` uses) and
  check the exact answer against the simulated frequency's 95% interval --
  deliberately building on the existing collection's proof-not-assertion
  pattern rather than reinventing it.
- Wrote 41 unit tests (`tests/test_probkit.py`): known textbook values
  (birthday-23/365 ~= 50.73%, classic Monty Hall 1/3 vs 2/3, 2d6-sums-to-7 =
  1/6, >=2 aces in a 5-card hand ~= 4.17%), input validation, and two
  correctness cross-checks: `bayes_update`'s general machinery and
  `monty_hall`'s independently-derived closed-form formula fed equivalent
  problems and landing on the exact same fraction via two unrelated code
  paths, and a "does the check have teeth" test proving the Wilson-interval
  logic actually flags a wrong claim, not just passes a correct one -- the
  same discipline `secure-random`'s chi-square tests apply to bias.
- Drove the live MCP server over stdio with a real client: `list_tools` plus
  all six tools called, several with `verify=true` (30,000 real CSPRNG
  trials each), and a deliberately invalid input (an impossible `reveal`
  count for a generalized Monty Hall) confirmed to come back as an MCP
  error result rather than a silently wrong number.
  `tools/discrete-probability/proof/run_2026-09-16.txt`.
- Fixed one real bug caught while writing tests, not after shipping:
  `_parse_probability` treated a plain int (`1` or `0`) as inexact (a bare
  `float`/`int` branch), so `bayes_update("1/3", 1, 0)` silently downgraded
  from exact-fraction arithmetic to float arithmetic partway through and
  the returned `posterior` came back as a bare float instead of the
  `{fraction, decimal}` shape every other exact result uses. Fixed by
  making ints parse to `Fraction` like fraction strings do (floats still
  stay float, since a literal like `0.3` isn't exactly representable and
  shouldn't be laundered into a falsely-precise fraction).
- Updated root `README.md`, appended this cycle to
  `special-projects/cycles.json`, rebuilt `_site/dashboard.html`, updated
  `special-projects/current.md` and `progress/notes-for-owner.md`.

## 2026-09-15 — third run: hardened CI, extended secure-random

- Ran `tools/collection-index/index.py` first, per the loop: 3 tools
  existed. Nothing overlapped a fresh candidate need.
- Web-searched several candidate angles (general "wish Claude could"
  complaints, MCP-idea threads, AI regex/ReDoS correctness, WCAG color
  contrast, precise large-number arithmetic). All landed on the same
  outcome as last cycle: real, well-documented "LLMs get this wrong"
  problems, but every one already has multiple existing MCP servers
  (regex/ReDoS especially -- found a dedicated ReDoS-guard MCP server,
  which is close enough to this repo's own differentiation angle that
  building another wouldn't add anything). See
  `progress/notes-for-owner.md` for the full rejection notes.
- Rule 9 applied: no new-tool candidate cleared the bar, so this cycle
  hardened and extended the existing collection instead of shipping
  filler. Two pieces of work:
  1. **Fixed the standing CI gap** (`progress/quality-debt.md`, carried
     over from the first cycle): added `.github/workflows/test.yml`,
     which runs every `tools/*/tests/` suite plus a `collection-index`
     sanity check on `pull_request` and `push:main`, with a job name
     (`test`) that matches `auto-merge.yml`'s existing
     `/deploy|build|test/i` check-name filter. While doing this, found a
     second bug in `auto-merge.yml`: it runs on `pull_request_target`
     (fires immediately) racing against `test.yml` on the separate
     `pull_request` event, and treated "no relevant check registered
     yet" as "nothing to wait for" -- meaning even a correctly-named test
     workflow could lose the race and get skipped. Fixed with a 60s grace
     period before concluding there's genuinely nothing to wait for.
  2. **Extended `secure-random`** with weighted sampling: `pick_random`
     now takes an optional `weights` list (unique and with-replacement
     both supported), and a new `verify_weighted_distribution` tool
     extends the existing chi-square proof-not-assertion pattern to
     arbitrary weighted distributions instead of just the uniform case.
     This was flagged as a live option in the previous cycle's
     `quality-debt.md` and `special-projects/current.md`.
- Also caught, while re-reading `time-arithmetic`'s own README this
  cycle, that the previous cycle's "extend with natural-language date
  parsing" suggestion contradicts that tool's own stated design boundary
  ("What it doesn't do" frames the absence as deliberate, not unbuilt).
  Recorded the course-correction in `notes-for-owner.md` and dropped it
  from `current.md`'s next-step list.
- Added 13 new unit tests to `tools/secure-random/tests/test_randkit.py`
  (47 total, up from 34) covering weighted `pick_random` (favors the
  heavy item, never returns a zero-weight item, rejects mismatched/
  negative/all-zero weights, unique mode has no repeats) and
  `verify_weighted_distribution` (real CSPRNG draws over `[1,2,7]` land
  within 2% of the 10/20/70 split it should follow, p ≈ 0.13; input
  validation).
- Drove the live MCP server over stdio with a real client to prove the
  new tools work end-to-end, not just the underlying functions:
  `tools/secure-random/proof/run_2026-09-15.txt` -- weighted `pick_random`
  (both modes), unweighted `pick_random` still working unchanged, and
  `verify_weighted_distribution`. Read back `structured_content` (not just
  the display-oriented text blocks, which the MCP SDK still splits one
  block per list element for list-typed returns) to confirm the JSON
  array comes back correctly typed.
- Updated `tools/secure-random/README.md` and `manifest.json`
  (`tools_exposed`, `updated` date), root `README.md`,
  `progress/quality-debt.md` (closed both fixed items),
  `progress/notes-for-owner.md`, appended this cycle to
  `special-projects/cycles.json`, rebuilt `_site/dashboard.html`.

## 2026-09-14 — second run

- Ran `tools/collection-index/index.py` first, per the loop: 2 tools
  existed (`collection-index`, `time-arithmetic`), nothing to extend that
  clearly beat a fresh candidate this cycle.
- Web-searched for candidate needs across several angles: general "I wish
  Claude could" complaints (unproductive — mostly SEO content, not real
  threads), AI text-counting complaints, spreadsheet/calculation
  complaints, regex reliability, cron expressions, unit/subnet conversion,
  and LLM randomness. See `special-projects/cycles.json` for the full
  query list and findings.
- Found three real candidates (word/character counting, precise text
  diffing, LLM randomness bias) and checked each against the existing MCP
  ecosystem, not just this repo — word-counting and diffing are both
  already served by many existing MCP servers; randomness had a sharper,
  more specific documented failure mode (the "27" phenomenon) and this
  repo's angle (a checkable chi-square uniformity proof) isn't something
  the existing random-number MCP servers found in search results do.
- Built `tools/secure-random`: `randkit.py` (CSPRNG functions + a
  hand-rolled chi-square goodness-of-fit test, stdlib only) and
  `server.py` (MCP stdio wrapper, 10 tools).
- Wrote 34 unit tests (`tests/test_randkit.py`), including validating the
  hand-rolled chi-square p-value function against six textbook critical
  values, and a synthetic biased-histogram test proving the uniformity
  test actually catches bias rather than only ever passing real
  randomness.
- Drove the live MCP server over stdio with a real client (not just
  scaffolding): `list_tools` + all 10 tools called, captured in
  `tools/secure-random/proof/run_2026-09-14.txt`.
- **Caught and fixed a real bug during the live-session proof, not after
  shipping:** `shuffle_list`/`pick_random` were typed to return a bare
  `list`, which made the MCP SDK skip structured-output generation and
  split results across one text content block per element — silently
  losing type fidelity (e.g. a list of ints came back as separate string
  content blocks, `["20","30","10"]`-shaped rather than a JSON array of
  ints). Fixed by annotating both as `list[Any]`; re-ran the live session
  to confirm before writing the final proof transcript.
- Wrote `tools/secure-random/README.md`, added it to the root README's
  tool list, appended the cycle to `special-projects/cycles.json`, and
  rebuilt `_site/dashboard.html` via `scripts/build_site.py`.
- Created the four standing progress files for the first time this cycle
  (none existed yet): this log, `progress/quality-debt.md`,
  `progress/notes-for-owner.md`, `special-projects/current.md`.
- Installed `mcp`, `cffi` via `pip install --user` to actually run/drive
  the server locally (not committed — see requirements.txt for the tool's
  own declared dependency).

## 2026-09-13 — first run under the standing project

See `special-projects/cycles.json` for the full record (search queries,
source, why, proof). Summary: created `tools/` and the `manifest.json`
convention, built `collection-index` (the collection's own index/reporting
tool), then `time-arithmetic` (MCP server for deterministic date/time
math). 13 unit tests + a live MCP client session, both passing. Also added
the project README, MIT license, and the `auto-merge` GitHub workflow for
`claude/*` branch PRs (see `progress/quality-debt.md` for a gap noticed in
that workflow this cycle).
