# Quality debt

Honest list of known gaps and shortcuts. Not urgent by default — surfaced
so a future cycle (or the owner) can decide whether to pay them down.

## `spaced-arrangement`'s `min_distance` is a hard constraint only, with no soft "spread evenly" mode or per-category priority

`arrange_with_spacing` guarantees every pair of same-category items is at
least `min_distance` apart, and nothing more — it doesn't try to spread
categories as evenly as possible *beyond* that minimum (e.g. preferring a
perfectly uniform interleave over a merely-valid one when both satisfy the
constraint), and it has no way to say "this category should appear earlier"
or weight categories against each other. Real playlist-shuffle systems
(Spotify's rebuilt shuffle, per this cycle's research) optimize a softer
"feels well-distributed" objective on top of the hard non-adjacency
constraint, generating many candidates and picking the best-spread one.
Not fixed because it's a genuinely different, harder problem (an
optimization over valid arrangements, not just find-one-that's-valid) and
the exhaustive-proof discipline this collection uses for feasibility
doesn't obviously extend to "provably most even" without a lot more design
work — worth a future cycle's dedicated attention if a real need for it
surfaces, not a quick add-on.

## Fixed this cycle (2026-09-20): `graph-algorithms` had no graph coloring, despite being documented in the same benchmarks that motivated the tool

Was: graph coloring (find the minimum number of colors so no two adjacent
nodes match) is real and sharply documented as an LLM failure right
alongside shortest path/topological sort/MST/max flow in the same
2025/2026 graph-reasoning benchmarks this tool's README cites, but wasn't
built in the tool's first cycle -- deliberately deferred rather than
folded in half-attentively alongside four other algorithm families (see
the previous version of this entry, and `special-projects/current.md`'s
2026-09-19 next-step list).

Fixed by adding `graph_coloring` (backtracking search: DSATUR variable
ordering + forward checking, budgeted by `max_search_nodes` -- exhausting
the whole search tree without a colorable branch is a proof the color
count is too few, running out of budget first raises instead of guessing,
the same contract `strips-planner`'s `max_states`/`max_depth` already
established), `verify_coloring` (independent direct-definition check, no
search), and `chromatic_number` (the minimum colors needed: a lower bound
proven for free by exhibiting a clique, then backtracking search upward
from there, so every smaller color count it rules out along the way is
proven uncolorable by full exhaustion, not merely unfound). 17 new unit
tests (61 total, up from 44) plus a live MCP session
(`proof/run_2026-09-20.txt`), including the deliberately-chosen odd-cycle
(5-cycle) case whose clique bound alone (2) doesn't already equal its
chromatic number (3), so real exhaustive search at k=2 is genuinely
exercised rather than the proof always coming from the clique bound alone.

## `graph-algorithms`'s implementations are plain Python, not vectorized or tuned for large graphs

`shortest_path` (Dijkstra with a binary heap), `minimum_spanning_tree`
(Kruskal with union-find), and `max_flow` (Edmonds-Karp, O(VE^2) worst
case) are all correct, standard-textbook implementations, but plain
Python loops over adjacency lists/dicts rather than anything vectorized
(NumPy adjacency matrices, etc.). Fine for the sizes these tools are
meant for (tens to low hundreds of nodes -- the kind of graph a person or
a model would plausibly describe by hand or ask about in a session), not
tuned for large-scale graph processing. Not fixed for the same reason
`secure-random`'s `verify_uniformity` stays a plain Python loop: adding a
numeric dependency would break this collection's "stdlib only, keyless, no
dependency beyond `mcp`" property, and the tradeoff (stay dependency-free
vs. faster large-N) favors staying dependency-free unless a real need for
much larger graphs surfaces.

## `strips-planner`'s BFS is exponential in the worst case, capped by `max_states`/`max_depth`, not by a smarter search

`solve_planning_problem` uses plain breadth-first search over the grounded
state space -- correct, and it's what makes the "shortest plan" and
"proven unreachable" guarantees possible, but it explores every reachable
state at each depth rather than using a heuristic (A*) to focus the search.
For the domains this tool is meant for (the Blocksworld generator caps at
8 blocks; hand-written custom domains are on the caller), the state space
stays small enough that this doesn't matter in practice -- the proof
transcript solves a 5-block generated instance and the 3-block Sussman
anomaly comfortably within default budgets. Not fixed because a real need
hasn't surfaced yet: adding a heuristic (e.g. relaxed-plan/FF-style) would
help scale to much larger domains, at the cost of real complexity and a
step away from "this collection's tools stay simple enough to read and
trust in one sitting." Worth reconsidering only if a future cycle's actual
use hits the `max_states`/`max_depth` ceiling on a domain that can't
reasonably be made smaller.

## `logic-grid-solver` doesn't support "between" (three-item) or quantified clues

The 10-clue vocabulary (`position`, `same_position`, `different_position`,
`immediately_left_of`, `immediately_right_of`, `left_of`, `right_of`,
`next_to`, `not_next_to`, `distance`) covers ordinary logic grid puzzle
phrasings, but not a genuinely three-way clue like "there is exactly one
house between the red house and the blue house" in the fully general case
(distinguishable from `distance` only when direction also matters), nor
disjunctive/quantified clues ("at least one of X or Y holds"). Not fixed
because it's outside what real "zebra puzzle" clue sets typically need —
`describe_clue_types` and the README are explicit about this boundary so a
future cycle doesn't mistake it for an oversight. If a genuine puzzle needs
that expressiveness, that's exactly the z3/ASP solvers' job, at the cost of
their own documented formalization-failure problem.

## Fixed this cycle (2026-09-15): no CI actually ran tests before auto-merge

Was: `.github/workflows/auto-merge.yml` waits for check runs matching
`/deploy|build|test/i` on the PR's head commit, but no workflow produced a
check with one of those names, so the "wait for checks to pass" step found
zero relevant checks and merged immediately without ever running a test.

Fixed by adding `.github/workflows/test.yml` (job name `test`, matches the
existing regex) that runs `python3 -m unittest discover -s tests` for every
`tools/*/tests/` directory plus a `collection-index` sanity check, on every
`pull_request` and on push to `main`.

While fixing it, found and fixed a second, subtler bug in the same file:
`auto-merge.yml` runs on `pull_request_target` (fires immediately when a PR
opens) while `test.yml` runs on the separate `pull_request` event — a race.
The old loop treated "no relevant check run exists yet" as "nothing to wait
for" and merged instantly, which meant even a correctly-named test workflow
could lose the race and never get waited on if its check run hadn't
registered in the few hundred milliseconds before `auto-merge.yml`'s first
poll. Fixed with a grace period (`GRACE_ITERATIONS`, 60s) before the loop
concludes there's truly nothing to wait for. Not covered by an automated
test (it's GitHub Actions timing behavior, hard to unit test locally) — the
real proof is this cycle's own PR going through the now-live `test` check
before merging; worth eyeballing that PR's checks tab to confirm.

## `secure-random`'s `verify_uniformity` is O(samples) in Python, not vectorized

At the high end of its accepted range (up to 2,000,000 samples) it's a
plain Python loop calling `secrets.randbelow` per draw — correct, but slow
compared to, say, filling a NumPy array. Not a real problem at the sample
sizes the tool is meant for (thousands, to answer "is this range biased?"
in a reasonable diagnostic run), and adding NumPy would break the
"stdlib only, keyless, no dependency beyond `mcp`" property the whole
collection is built on. Documented, not fixed, because the tradeoff (stay
dependency-free vs. faster large-N) favors staying dependency-free.

## Fixed this cycle (2026-09-15): `pick_random`'s uniform-only sampling

Was: `pick_random` (in `tools/secure-random`) only did uniform selection --
no weighted/biased sampling, even though callers sometimes want that
("pick a winner weighted by ticket count").

Fixed by adding an optional `weights` parameter to `pick_random` (both
unique and with-replacement modes) and a new `verify_weighted_distribution`
tool that chi-square-tests real draws against the requested weights,
extending the same proof-not-assertion pattern `verify_uniformity` already
used for the uniform case. 13 new unit tests plus a live MCP session
(`proof/run_2026-09-15.txt`).
