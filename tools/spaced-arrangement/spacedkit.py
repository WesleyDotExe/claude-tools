"""Combinatorial generation under a guaranteed spacing invariant, + independent verifier.

This is a fifth problem *shape* in this collection, distinct from the other
four: `secure-random`/`discrete-probability`/`time-arithmetic` are each a
single deterministic calculation; `logic-grid-solver` is constraint
satisfaction over a static assignment; `strips-planner` is sequential action
search over cumulative world-state; `graph-algorithms` is structural
traversal/optimization over an explicit graph. This tool instead
*constructs* a combinatorial object (an ordering of items) that is
guaranteed, by proof, to satisfy an invariant -- no two items of the same
category ever appear within `min_distance` positions of each other -- rather
than searching for or calculating a single answer to a fixed question.

The problem is real and widely documented, not invented for this cycle: a
uniformly random shuffle of a category-heavy list clusters same-category
items together far more often than people expect ("three songs by the same
artist in a row" reads as broken, not random). Spotify and Apple both
rewrote their shuffle algorithms specifically because of this complaint
(Spotify's own engineering write-ups and years of community-forum threads
document it), and the general problem -- rearrange a multiset so that no two
equal items are within k positions of each other -- is a classic, named
algorithmic problem (LeetCode 767 "Reorganize String", 621 "Task Scheduler",
358 "Rearrange String k Distance Apart") precisely because getting it right
by hand (or by an LLM just "shuffling" in its head) is easy to get
plausibly-looking-random but actually wrong.

`arrange_with_spacing` solves it via budgeted backtracking search (branch on
every category whose cooldown has expired, most-remaining-count first for
speed, full backtracking on failure for completeness -- the same
`max_search_nodes` contract `graph-algorithms`' `graph_coloring` and
`strips-planner`'s BFS already established: exhausting the whole search tree
without a valid completion is a *proof* no arrangement exists, running out
of budget first is inconclusive and raises rather than guessing). Multiple
categories interacting under a distance-k constraint is genuinely more
subtle than the well-known single-category "no two adjacent" case: a
per-category "count <= ceil(n/min_distance)" check is *necessary* but, once
more than two categories are involved, is demonstrably NOT sufficient (see
the test suite's `k=3` three-category counterexample) -- which is exactly
why this tool proves infeasibility by full search exhaustion instead of a
closed-form formula that would be quietly wrong on some inputs.

`verify_arrangement` independently re-checks any claimed arrangement (the
solver's own, or a hand-written/model-proposed one) against the direct
definition: no search at all, a structurally different, much simpler code
path than the backtracking solver.

Tie-breaking during search uses a CSPRNG (`secrets.SystemRandom`, the same
primitive `secure-random` is built on) rather than a fixed heuristic order,
so repeated calls on the same input return different, independently-valid
arrangements -- "provably spaced apart" AND "actually feels shuffled",
which is the whole point. `generate_arrangement_problem` uses a seeded
stdlib RNG instead (reproducible instance generation, not a security
context), the same convention `graph-algorithms`' `generate_random_graph`
and `strips-planner`'s Blocksworld generator already use.

Stdlib only. No network, no account, no dependency beyond `mcp` for the
server wrapper.
"""
from __future__ import annotations

import random
import secrets
from collections import Counter

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_MAX_ITEMS = 300


def _validate_items(items) -> tuple[list[str], dict[str, str]]:
    if not isinstance(items, list) or not (2 <= len(items) <= _MAX_ITEMS):
        raise ValueError(f"items must be a list of 2 to {_MAX_ITEMS} {{id, category}} objects")
    ids: list[str] = []
    categories: dict[str, str] = {}
    for i, it in enumerate(items):
        if not isinstance(it, dict) or "id" not in it or "category" not in it:
            raise ValueError(f"items[{i}] must be an object with 'id' and 'category'")
        iid, cat = it["id"], it["category"]
        if not isinstance(iid, str) or not iid:
            raise ValueError(f"items[{i}].id must be a non-empty string")
        if not isinstance(cat, str) or not cat:
            raise ValueError(f"items[{i}].category must be a non-empty string")
        if iid in categories:
            raise ValueError(f"duplicate item id: {iid!r}")
        ids.append(iid)
        categories[iid] = cat
    return ids, categories


def _validate_min_distance(min_distance) -> None:
    if not isinstance(min_distance, int) or isinstance(min_distance, bool) or min_distance < 1:
        raise ValueError("min_distance must be an int >= 1")


def _validate_budget(max_search_nodes) -> None:
    if not isinstance(max_search_nodes, int) or isinstance(max_search_nodes, bool) or max_search_nodes < 1:
        raise ValueError("max_search_nodes must be an int >= 1")


# ---------------------------------------------------------------------------
# Format description
# ---------------------------------------------------------------------------


def describe_arrangement_format() -> dict:
    """Return the fixed JSON vocabulary for items/min_distance, plus a tiny worked example."""
    example_items = [
        {"id": "t1", "category": "ArtistA"},
        {"id": "t2", "category": "ArtistA"},
        {"id": "t3", "category": "ArtistB"},
        {"id": "t4", "category": "ArtistC"},
        {"id": "t5", "category": "ArtistA"},
    ]
    return {
        "items": "A list of 2.." + str(_MAX_ITEMS) + " objects {\"id\": string (unique), "
        "\"category\": string}. 'category' is whatever must not repeat too closely -- artist "
        "for a playlist, department for an interview schedule, task type for a cooldown "
        "queue, letter for a classic string-rearrangement puzzle.",
        "min_distance": "An int >= 1: how many index positions must separate two items of the "
        "SAME category. min_distance=2 means 'no two adjacent' (the common case -- a truly "
        "random shuffle of a category-heavy list clusters same-category items back to back, "
        "which reads as broken rather than random -- this is exactly the complaint behind "
        "Spotify's and Apple's own shuffle rewrites). min_distance=k>2 spaces items at least "
        "k apart (e.g. a task scheduler's cooldown, or a PIN-testing sequence).",
        "example_items": example_items,
        "example_min_distance": 2,
    }


# ---------------------------------------------------------------------------
# Budgeted backtracking search: place items one position at a time, branching
# over every category whose cooldown has expired (most-remaining-count first,
# CSPRNG tie-broken), full backtracking on dead ends.
# ---------------------------------------------------------------------------


def _node_locally_feasible(pos: int, n: int, remaining: dict, last_pos: dict, min_distance: int) -> bool:
    """Cheap NECESSARY condition, checked at every search node: for each category still
    holding items, is there even room left to place all of them, min_distance apart,
    before the sequence ends? A true prune (never rules out a reachable solution), used
    only to cut dead branches faster -- the recursive backtracking below is what actually
    makes exhaustion a proof, this is purely a speed optimization."""
    for c, ids in remaining.items():
        r = len(ids)
        if r == 0:
            continue
        earliest = max(pos, last_pos[c] + min_distance)
        needed_span_end = earliest + (r - 1) * min_distance
        if needed_span_end > n - 1:
            return False
    return True


def _search_arrangement(ids: list[str], categories: dict[str, str], min_distance: int, node_budget: int, rng):
    """Exhaustive (budgeted) backtracking search for a valid arrangement. Returns
    (found, arrangement_or_None, nodes_expanded, budget_exceeded). Every candidate
    category is tried at every position before backtracking, so failure after full
    exhaustion (budget_exceeded=False) is a genuine proof no arrangement exists -- not
    just a heuristic giving up."""
    n = len(ids)
    remaining: dict[str, list[str]] = {}
    for iid in ids:
        remaining.setdefault(categories[iid], []).append(iid)
    last_pos = {c: -min_distance for c in remaining}  # so every category is free at pos 0
    arrangement: list[str] = []
    expanded = 0
    exceeded = False

    def backtrack(pos: int) -> bool:
        nonlocal expanded, exceeded
        expanded += 1
        if expanded > node_budget:
            exceeded = True
            return False
        if pos == n:
            return True
        if not _node_locally_feasible(pos, n, remaining, last_pos, min_distance):
            return False
        candidates = [c for c, its in remaining.items() if its and pos - last_pos[c] >= min_distance]
        if not candidates:
            return False
        rng.shuffle(candidates)  # randomize tie order first (stable sort keeps it for ties)
        candidates.sort(key=lambda c: -len(remaining[c]))  # most-remaining-first: fast + complete
        for c in candidates:
            idx = rng.randrange(len(remaining[c]))
            iid = remaining[c].pop(idx)
            prev_last = last_pos[c]
            last_pos[c] = pos
            arrangement.append(iid)
            if backtrack(pos + 1):
                return True
            arrangement.pop()
            last_pos[c] = prev_last
            remaining[c].insert(idx, iid)
            if exceeded:
                return False
        return False

    ok = backtrack(0)
    return ok, (list(arrangement) if ok else None), expanded, exceeded


def arrange_with_spacing(items: list, min_distance: int = 2, max_search_nodes: int = 200_000) -> dict:
    """Construct an ordering of `items` such that no two items of the SAME category are
    within `min_distance` positions of each other, via budgeted backtracking search
    (CSPRNG-randomized tie-breaking, so repeated calls give different valid orderings).
    If a valid ordering exists, returns it along with an embedded independent
    verification. If NO valid ordering exists, the entire search tree was exhausted --
    that's a proof, not a guess (a per-category frequency check alone is necessary but
    NOT sufficient once more than two categories are involved -- see the module
    docstring). If the search budget runs out before resolving either way, raises
    instead of silently claiming an answer."""
    ids, categories = _validate_items(items)
    _validate_min_distance(min_distance)
    _validate_budget(max_search_nodes)

    rng = secrets.SystemRandom()
    ok, arrangement, expanded, exceeded = _search_arrangement(ids, categories, min_distance, max_search_nodes, rng)

    if ok:
        verification = verify_arrangement(items, min_distance, arrangement)
        if not verification["valid"]:
            raise AssertionError(  # pragma: no cover -- would indicate a solver bug
                "internal error: solver's own arrangement failed independent verification"
            )
        return {
            "arrangable": True,
            "arrangement": arrangement,
            "search_nodes_expanded": expanded,
            "verification": verification,
        }

    if exceeded:
        raise ValueError(
            f"search exceeded max_search_nodes={max_search_nodes} without determining whether a "
            "valid arrangement exists; feasibility could not be determined either way -- try "
            "raising max_search_nodes"
        )

    counts = Counter(categories.values())
    worst_category, worst_count = counts.most_common(1)[0]
    return {
        "arrangable": False,
        "reason": "the entire search tree was explored without finding a valid arrangement -- "
        f"proven impossible with min_distance={min_distance}, not just unfound within a search "
        "budget. (Note: no single category here necessarily exceeds a simple ceil(n/min_distance) "
        "frequency bound -- with 3+ categories that per-category check is necessary but not "
        "sufficient, which is exactly why this is proven by full search exhaustion.)",
        "search_nodes_expanded": expanded,
        "num_items": len(ids),
        "category_counts": dict(sorted(counts.items())),
        "most_frequent_category": worst_category,
        "most_frequent_count": worst_count,
    }


def verify_arrangement(items: list, min_distance: int, arrangement: list) -> dict:
    """Independently check a claimed arrangement (the solver's own, or a hand-written/
    model-proposed one) against the direct definition: it's a permutation of the given
    item ids, and every pair of same-category items is at least min_distance positions
    apart. No search at all -- a structurally different, much simpler code path than the
    backtracking solver."""
    ids, categories = _validate_items(items)
    _validate_min_distance(min_distance)
    if not isinstance(arrangement, list) or not all(isinstance(x, str) for x in arrangement):
        raise ValueError("arrangement must be a list of item id strings")

    if sorted(arrangement) != sorted(ids):
        return {
            "valid": False,
            "reason": "arrangement is not a permutation of the given item ids",
            "missing_ids": sorted(set(ids) - set(arrangement)),
            "unexpected_ids": sorted(set(arrangement) - set(ids)),
        }

    positions_by_category: dict[str, list[int]] = {}
    for i, iid in enumerate(arrangement):
        positions_by_category.setdefault(categories[iid], []).append(i)

    violations = []
    for cat, positions in positions_by_category.items():
        positions.sort()
        for a, b in zip(positions, positions[1:]):
            if b - a < min_distance:
                violations.append(
                    {
                        "category": cat,
                        "item_a": arrangement[a],
                        "item_b": arrangement[b],
                        "position_a": a,
                        "position_b": b,
                        "distance": b - a,
                        "required_min_distance": min_distance,
                    }
                )

    return {
        "valid": not violations,
        "violations": violations,
        "proof_method": "directly checks every pair of positions holding the same category is "
        "at least min_distance apart -- the definition of a valid spaced arrangement, "
        "independent of however the arrangement was produced.",
    }


# ---------------------------------------------------------------------------
# Seeded, reproducible instance generator
# ---------------------------------------------------------------------------


def generate_arrangement_problem(num_items: int, num_categories: int, seed: int | None = None) -> dict:
    """Generate a random, reproducible (seeded) items list -- num_items items spread
    across num_categories categories (every category used at least once), ready to feed
    into arrange_with_spacing. Uses a seeded stdlib RNG, not secure-random's CSPRNG: this
    is reproducible instance generation, not a security context. The random category
    distribution is NOT guaranteed feasible for any particular min_distance -- that's the
    point: arrange_with_spacing's own search (and its exhaustive infeasibility proof) is
    what determines feasibility, not the generator."""
    if not isinstance(num_items, int) or not (2 <= num_items <= _MAX_ITEMS):
        raise ValueError(f"num_items must be an int between 2 and {_MAX_ITEMS}")
    if not isinstance(num_categories, int) or not (1 <= num_categories <= num_items):
        raise ValueError("num_categories must be an int between 1 and num_items")

    rng = random.Random(seed)
    category_names = [f"cat{i + 1}" for i in range(num_categories)]
    assigned = list(category_names)  # every category appears at least once
    assigned += [rng.choice(category_names) for _ in range(num_items - num_categories)]
    rng.shuffle(assigned)
    items = [{"id": f"item{i + 1}", "category": assigned[i]} for i in range(num_items)]

    return {
        "items": items,
        "seed": seed,
        "num_items": num_items,
        "num_categories": num_categories,
        "category_counts": dict(sorted(Counter(assigned).items())),
    }
