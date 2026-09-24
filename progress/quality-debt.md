# Quality debt

Honest list of known gaps and shortcuts. Not urgent by default — surfaced
so a future cycle (or the owner) can decide whether to pay them down.

## `discrete-probability`'s `compare_two_proportions` only handles independent (unpaired) samples, and its permutation test has a size-dependent budget

Added this cycle (2026-09-24): `compare_two_proportions` assumes the two
groups are independent (two different cohorts/strategies/variants) — it is
not the right test for paired/matched data (the same subjects measured
twice, e.g. before/after), which needs McNemar's test, not built. Also, the
`verify=true` permutation test's cost scales with `verify_trials *
min(trials_a, trials_b)`, capped at 10,000,000 (roughly a few seconds to
~10s at the cap, benchmarked locally at ~1.3M `secrets.randbelow` calls/sec
in this container) — a caller with both very large sample sizes and a large
`verify_trials` will need to lower `verify_trials`, the same "budget raises
instead of running unboundedly long" contract the rest of this collection's
search/simulation budgets already follow. Not fixed because no real need for
either has surfaced yet (the sourcing wishlist item was specifically about
independent win-rate comparisons); worth a future cycle's attention if one
does. Separately, worth knowing for anyone extending this: the z-test's
p-value and the permutation test's are legitimately different quantities
(a large-sample normal approximation vs. an exact permutation-null
estimate) and can diverge by several points of p even when both are
computed correctly — confirmed by hand-deriving the exact permutation
p-value via the hypergeometric distribution for a 300-vs-300 case. The
`verify=true` response reports whether the two *agree on the significance
call*, not whether they're numerically equal — see
`special-projects/wishlist.md`'s `[stats-normal-vs-exact-pvalue]` entry for
the general lesson for any future significance-test tool in this
collection.

## `graph-algorithms`' `assignment_problem` only handles the square (n-to-n) case, and general (non-bipartite) matching isn't supported at all

Added this cycle (2026-09-22): `maximum_bipartite_matching` and
`assignment_problem` only work on **bipartite** graphs (two distinct
sides, `left_nodes`/`right_nodes`) — general matching within a single set
of nodes (e.g. "pair up these 10 people, some pairs incompatible, to
maximize total compatibility," which needs Edmonds' blossom algorithm, a
structurally harder algorithm that has to handle odd cycles) isn't built.
`assignment_problem` also requires `len(left_nodes) == len(right_nodes)`
exactly — no rectangular (unequal-size) or partial-assignment mode (e.g.
"5 workers, 8 tasks, assign as many as profitable"); a caller has to pad
with dummy zero-weight nodes themselves. Not fixed because both are
genuinely separate, harder problems (blossom algorithm's odd-cycle
handling is a different beast entirely from augmenting-path search over a
bipartite graph; rectangular assignment needs the LP-duality proof to
handle "free" unmatched potentials correctly, more design work than fit in
one cycle) and no real need for either has surfaced yet — worth a future
cycle's dedicated attention if one does. Also: `assignment_problem`'s
solver uses a large internal sentinel cost (`_ASSIGNMENT_BIG_M = 1e9`) to
steer the Hungarian algorithm away from missing (disallowed) edges, which
is why edge weights are capped at magnitude 1000 and node count at 60 per
side — comfortably separated numerically, but a caller who genuinely needs
larger weights or more nodes will hit these caps; they're sanity bounds
(the same stance every other search/optimization cap in this collection
takes), not tuned performance limits, and could be raised (along with
`_ASSIGNMENT_BIG_M`) if a real need for bigger instances surfaces.

## Fixed this cycle (2026-09-23): `spaced-arrangement` had no soft "spread evenly" mode

Was: `arrange_with_spacing` guaranteed every pair of same-category items is
at least `min_distance` apart, and nothing more — it didn't try to spread
categories as evenly as possible *beyond* that minimum (e.g. preferring a
perfectly uniform interleave over a merely-valid one when both satisfy the
constraint). Real playlist-shuffle systems (Spotify's rebuilt shuffle, per
the previous cycle's research, already cited in this tool's own README)
optimize a softer "feels well-distributed" objective on top of the hard
non-adjacency constraint, generating many candidates and picking the
best-spread one.

Fixed by adding `maximize_min_distance`: given only the items (no
caller-chosen `min_distance`), it finds the LARGEST `min_distance` for
which a valid arrangement exists — the rigorous formalization of "spread as
evenly as possible" as maximizing the *worst-case* (minimum) same-category
gap — via binary search over `arrange_with_spacing`'s own exhaustive
feasibility proof (feasibility is monotonic in `min_distance`, so this is
sound: found in O(log n) feasibility checks, each one still a genuine
budgeted exhaustive search, not a relaxation of the proof discipline). The
final answer's optimality is itself proven: either **structurally** (the
found value already equals `n - 1`, the absolute ceiling for the distance
between any two of `n` positions) or by one more **exhaustive search** one
distance higher, confirmed infeasible. 9 new unit tests (34 total, up from
25) plus a live MCP session (`proof/run_2026-09-23.txt`) covering the
unconstrained case (every category appears once, so there's no meaningful
finite answer), both optimality-proof paths, and an independent
re-confirmation of the "one more is infeasible" claim via a direct
`arrange_with_spacing` call rather than trusting `maximize_min_distance`'s
own internal proof step.

**Still not fixed, deliberately out of scope this cycle:** per-category
priority/weighting (every category is still treated identically — there's
no way to say "this category should appear earlier" or matter more than
another), and multi-dimensional spacing (avoiding both same-artist AND
same-genre clustering at once, as two separate invariants enforced
together). Both are genuinely separate design problems from "maximize a
single scalar objective over the existing single-invariant search," and no
real need for either has surfaced yet — worth a future cycle's attention if
one does.

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
