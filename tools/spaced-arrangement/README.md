# spaced-arrangement

An MCP server that constructs an ordering of items so that no two items of
the same category ever land too close together -- and proves it -- instead
of asking a language model to "just shuffle it" and hope the same artist,
task type, or department doesn't end up clustered together by chance.

## What it solves

A uniformly random shuffle of a category-heavy list clusters same-category
items together far more often than intuition expects. "Three songs by the
same artist in a row" is the textbook example, and it's not a hunch: Spotify
and Apple both rewrote their shuffle algorithms specifically because of it.
Spotify's own community forums are full of years of threads like ["shuffle
playlist seems to play the same songs"](https://community.spotify.com/t5/Your-Library/shuffle-playlist-seems-to-play-the-same-songs/td-p/5507802)
and ["Shuffle mode playing the same songs all the time"](https://community.spotify.com/t5/Desktop-Windows/Shuffle-mode-playing-the-same-songs-all-the-time/td-p/5280042),
and Spotify's 2026 engineering coverage describes a rebuilt shuffle that
[generates hundreds of candidate orderings and picks the one with the best
spread](https://www.techbuzz.ai/articles/spotify-fixes-shuffle-s-repetition-problem-with-smarter-algorithm)
rather than trusting a single random permutation. The general version of
this problem -- rearrange a multiset so no two equal items are within `k`
positions of each other -- is a classic, *named* algorithmic problem
precisely because it's easy to get plausibly-random-looking but actually
wrong: LeetCode 767 "Reorganize String" (`k`=2, "no two adjacent"), 621
"Task Scheduler" (a cooldown-window variant), and 358 "Rearrange String k
Distance Apart" (the fully general case this tool solves) are staples of
technical interviews for exactly that reason. A 2023 technical write-up,
["An algorithm for shuffling playlists"](https://ruuda.nl/2023/an-algorithm-for-shuffling-playlists),
independently makes the same point: even Spotify's and Apple's published
shuffle fixes aren't provably optimal at avoiding adjacent repeats.

This is a genuinely different problem *shape* than the rest of this
collection: `secure-random`/`discrete-probability`/`time-arithmetic` are
each a single deterministic calculation; `logic-grid-solver` is constraint
satisfaction over a *static* assignment (every clue is checked against one
fixed grid); `strips-planner` is sequential action search over cumulative
world-state; `graph-algorithms` is structural traversal/optimization over
an explicit graph. This tool *constructs* a combinatorial object -- an
ordering -- that's guaranteed by proof to satisfy an invariant, rather than
computing or searching for a single fixed answer. It's also genuinely more
subtle than it looks once more than two categories are involved: checking
"does any one category appear too often" (`count <= ceil(n / min_distance)`)
is a **necessary** condition, but with three or more categories it is
demonstrably **not sufficient** -- see `tests/test_spacedkit.py`'s
`test_multi_category_infeasible_despite_per_category_count_passing` for a
concrete 7-item, 3-category counterexample where every category
individually passes that check yet no valid arrangement exists. That's
exactly why this tool proves infeasibility by exhausting a real search
instead of trusting a closed-form formula that would be silently wrong on
some inputs.

This cycle's search found no MCP server -- keyless or otherwise -- offering
this as a generic tool. Existing Spotify-control MCP servers only toggle
real Spotify's own built-in shuffle mode (they don't implement the spacing
algorithm themselves); existing pairwise/covering-array test-generation MCP
servers (e.g. `PictMCP`, wrapping Microsoft's PICT) solve a *different*
combinatorial problem (covering every pair of parameter values at least
once), not minimum-distance spacing.

## How it works

`arrange_with_spacing` solves via **budgeted backtracking search**: at each
position, every category whose "cooldown" (`min_distance` since its last
placement) has expired is a candidate; candidates are tried most-remaining-
count-first for speed (this alone resolves the overwhelming majority of
real inputs immediately, with no actual backtracking), but on a dead end the
search genuinely backtracks and tries the next candidate -- so success is
always a genuine, verified answer, and *failure only after every candidate
at every node has been exhausted* is a **proof** no arrangement exists, not
a heuristic giving up. This is the same `max_search_nodes` budget contract
`graph-algorithms`' `graph_coloring` and `strips-planner`'s BFS solver
already established: exhausting the whole search tree within budget is
proof of infeasibility; running out of budget first is inconclusive and
**raises** instead of silently guessing "impossible." Tie-breaking uses a
CSPRNG (`secrets.SystemRandom`, the same primitive `secure-random` is built
on), not a fixed heuristic order or a seed, so repeated calls on the same
input return *different*, independently-valid arrangements -- provably
correctly spaced AND actually shuffled, which is the whole point.

`verify_arrangement` independently re-checks any claimed arrangement (the
solver's own output, a hand-written one, or a model's guess) against the
direct definition -- every pair of same-category items at least
`min_distance` apart -- with no search at all, a structurally different,
much simpler code path than the backtracking solver.

`generate_arrangement_problem` gives a seeded, reproducible instance (a
category distribution that may or may not turn out to be feasible for any
particular `min_distance` -- that's for `arrange_with_spacing` itself to
determine and prove, not something the generator decides in advance), the
same role `graph-algorithms`' `generate_random_graph` and
`strips-planner`'s Blocksworld generator play for their own tools.

`maximize_min_distance` (added 2026-09-23) answers the question
`arrange_with_spacing` deliberately leaves open: given only the items, no
caller-chosen `min_distance`, find the **largest** `min_distance` for which
a valid arrangement exists, and prove it's the largest. This is the
rigorous version of "spread categories as evenly as possible" this README
used to flag as a gap -- and it's the same idea Spotify's own rebuilt
shuffle uses (generating many candidate orderings and picking the one with
the best spread), except here the "best" one is found directly by search
and *proven* best, not sampled and hoped for. It works by **binary search**
over `arrange_with_spacing`'s own exhaustive feasibility proof: feasibility
at a given `min_distance` is monotonic (any arrangement valid at distance
`d` is automatically valid at every smaller `d'`, since the same gaps are
still `>= d'`), so the largest feasible value can be found in
O(log n) feasibility checks rather than trying every value from 1 upward.
Each individual check is still a genuine, budgeted exhaustive search --
this is a search *over* that proof, not a relaxation of it. The final
answer's optimality is itself proven, not just found: either **structurally**
(the answer already equals `n - 1`, the absolute ceiling for the distance
between any two of `n` positions -- no arrangement could ever do better,
so no more searching is needed), or by one more **exhaustive search** one
distance higher that comes back impossible. If every category appears at
most once, there are no same-category pairs to space at all -- every
ordering already satisfies any `min_distance` -- and this is reported as
`unconstrained` explicitly rather than returning a meaningless number.

## Tools exposed

| Tool | Purpose |
|---|---|
| `describe_arrangement_format` | The fixed JSON vocabulary for `items`/`min_distance`, plus a worked example. Call this first. |
| `arrange_with_spacing` | Construct a spaced ordering via budgeted backtracking search (CSPRNG tie-breaking). Returns the ordering with an embedded independent verification, or `arrangable: false` proven by full search exhaustion. |
| `verify_arrangement` | Independently check any claimed ordering (the solver's own, hand-written, or model-proposed) against the direct definition -- no search. |
| `maximize_min_distance` | Find the LARGEST `min_distance` achievable (no caller-chosen value needed) and prove it's the largest, via binary search over the same exhaustive feasibility proof. The rigorous "spread as evenly as possible" mode. |
| `generate_arrangement_problem` | A seeded, reproducible items list to experiment with. |

### The format, briefly

```json
{
  "items": [
    {"id": "t1", "category": "ArtistA"},
    {"id": "t2", "category": "ArtistA"},
    {"id": "t3", "category": "ArtistB"},
    {"id": "t4", "category": "ArtistC"},
    {"id": "t5", "category": "ArtistA"}
  ],
  "min_distance": 2
}
```

`min_distance` is how many index positions must separate two items of the
*same* category. `min_distance=2` is the common "no two adjacent" case (a
playlist where the same artist shouldn't play back to back); larger values
space things further apart (a task scheduler's cooldown window, or a PIN-
testing sequence). Call `describe_arrangement_format` for the exact rules.

## What it doesn't do

It doesn't parse a prose request ("shuffle my playlist but not the same
artist twice in a row") into this JSON vocabulary -- like the rest of this
collection, it computes once the input is already unambiguous, not from
prose. `maximize_min_distance` (added 2026-09-23) covers "spread as evenly
as possible" in the specific sense of maximizing the *worst-case* (minimum)
gap between same-category items -- but it still doesn't support weighting
some categories to appear earlier or mattering more than others (every
category is treated identically), and it doesn't do multi-dimensional
spacing (e.g. "no two items within `min_distance` of the same artist AND
no two within a *different* `min_distance` of the same genre, at once" --
one invariant at a time only). Items are capped at 300 (a sanity bound for
exhaustive backtracking search, not a tuned performance limit, the same
stance `logic-grid-solver`'s 12-position cap and `strips-planner`'s
`max_states`/`max_depth` take on their own search spaces) -- comfortably
past playlist- or task-queue-scale inputs a person would plausibly describe
by hand. The search is exponential in the worst case like any exact
backtracking search; the most-remaining-first ordering keeps the typical
case fast (the proof transcript's 18-item/4-category generated instance
resolves in 19 search nodes), but a dense, adversarially tight instance
close to the feasibility boundary can still exhaust `max_search_nodes` --
raise it, or accept an inconclusive result staying inconclusive rather than
silently wrong.

## Files

- `spacedkit.py` -- the actual logic: input validation, the budgeted
  backtracking solver and its CSPRNG-randomized tie-breaking, the
  independent direct-definition verifier, the binary-search-based
  `maximize_min_distance` optimizer, and the seeded instance generator.
  Stdlib only, no dependency beyond `mcp` for the server wrapper. Usable
  standalone.
- `server.py` -- a thin MCP server (stdio transport) wrapping `spacedkit.py`.
- `tests/test_spacedkit.py` -- 34 unit tests (25 from before, 9 new for
  `maximize_min_distance`): a tight-but-feasible 3-A/1-B/1-C case at the
  `min_distance=2` boundary; a 3-category, 3-each, `min_distance=3` case
  using the classic `a,b,c,a,b,c,a,b,c` spread; the trivial `min_distance=1`
  case; CSPRNG randomness confirmed to actually vary across repeated calls
  (not just claimed to); a simple infeasible case (one category too
  frequent) proven by full search exhaustion; **the multi-category
  counterexample** where every category individually passes the naive
  `count <= ceil(n/min_distance)` check yet no arrangement exists -- proven
  only by real search, not formula; a too-small `max_search_nodes` budget
  raising instead of guessing; `verify_arrangement` accepting the solver's
  own output, catching a deliberately bad guess (with the exact violating
  pair and distance named), catching a non-permutation (missing/extra ids),
  and checked at the exact `min_distance` boundary (valid) and one short of
  it (invalid); input validation for every malformed-input path; the seeded
  generator's reproducibility, category coverage, and composability with
  `arrange_with_spacing`/`verify_arrangement`; and for
  `maximize_min_distance`: the `unconstrained` case (every category appears
  once, including a mixed single-item-category case), the **structural**
  optimality proof (2 same-category items among 4 total hits the `n-1`
  ceiling exactly), the **exhaustive-search** optimality proof (the
  3-category/3-each case, where `min_distance+1` is genuinely re-checked and
  found infeasible), a direct comparison confirming it never does worse than
  a plain `arrange_with_spacing` call on the same input, an end-to-end run on
  a generated instance, and a too-small `max_search_nodes` budget raising
  instead of guessing.
- `proof/run_2026-09-21.txt` -- the original tool's proof: the full test run
  plus a live MCP client session over stdio (worked example solved and
  independently verified, a deliberately bad guess caught by
  `verify_arrangement`, a generated instance solved and independently
  verified, the multi-category infeasibility proof shown live, a too-small
  `max_search_nodes` budget coming back as a genuine MCP tool error, and two
  repeated calls producing two different valid arrangements).
- `proof/run_2026-09-23.txt` -- this cycle's proof for `maximize_min_distance`:
  the full (34-test) test run, plus a live MCP client session over stdio
  covering all five cases above -- the unconstrained case, the structural
  optimality proof, the exhaustive-search optimality proof (with the
  returned arrangement independently re-verified via `verify_arrangement`
  AND the claimed-infeasible-at-one-more distance independently re-confirmed
  via a direct `arrange_with_spacing` call, not just trusting
  `maximize_min_distance`'s own internal proof step), a 20-item/5-category
  generated instance solved end to end, and a too-small `max_search_nodes`
  budget coming back as a genuine MCP tool error.

## Try it without MCP

```
python3 -c "
import json, spacedkit
items = [
    {'id': 't1', 'category': 'ArtistA'}, {'id': 't2', 'category': 'ArtistA'},
    {'id': 't3', 'category': 'ArtistB'}, {'id': 't4', 'category': 'ArtistC'},
    {'id': 't5', 'category': 'ArtistA'},
]
print(json.dumps(spacedkit.arrange_with_spacing(items, min_distance=2), indent=2))
"
```

## Run the tests

```
python3 -m unittest discover -s tests -v
```

## Run as an MCP server

```
pip install -r requirements.txt
python3 server.py
```

Point an MCP client at it, e.g. in Claude Desktop/Code's MCP config:

```json
{
  "mcpServers": {
    "spaced-arrangement": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/spaced-arrangement/server.py"]
    }
  }
}
```
