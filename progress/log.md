# Progress log

Newest entry on top. One entry per cycle: what was done, honestly.

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
