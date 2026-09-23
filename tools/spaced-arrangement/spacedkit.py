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

`maximize_min_distance` answers the question `arrange_with_spacing` deliberately
leaves open: given only the items (no caller-chosen min_distance), find the LARGEST
min_distance for which a valid arrangement exists, and prove it's the largest --
the rigorous formalization of "spread categories as evenly as possible" that this
tool's own README flagged as a gap, done by binary search over the same exhaustive
feasibility proof `arrange_with_spacing` already makes for one fixed min_distance
(feasibility is monotonic in min_distance, so binary search is sound), with the
final answer proven optimal either structurally (min_distance already hit the
n-1 ceiling) or by exhausting the search tree one distance higher and finding
nothing.

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
# Optimal ("spread as evenly as possible") mode: the largest min_distance for
# which a valid arrangement still exists, found by binary search over
# arrange_with_spacing's own exhaustive feasibility proof.
# ---------------------------------------------------------------------------


def maximize_min_distance(items: list, max_search_nodes: int = 200_000) -> dict:
    """Find the LARGEST min_distance for which a valid arrangement of `items` exists,
    and return that arrangement plus a proof that no larger value is achievable. This is
    the rigorous formalization of "spread categories as evenly as possible" that
    `arrange_with_spacing` deliberately doesn't attempt on its own (it only checks a
    single caller-given min_distance): Spotify's own published shuffle fix works by
    generating many candidate orderings and picking the one with the best spread -- this
    finds the best-spread one directly and PROVES it's the best, rather than sampling and
    hoping.

    Feasibility at a given min_distance is monotonic: any arrangement valid at distance d
    is automatically valid at every smaller d' too (the same gaps are still >= d'), so the
    largest feasible d can be found by binary search over arrange_with_spacing's own
    budgeted-exhaustive-search feasibility check, each call still genuinely proving
    feasibility or infeasibility at that one value exactly as arrange_with_spacing does
    standalone -- this is a search *over* that proof, not a relaxation of it. The final
    answer is proven optimal by then exhausting the search tree one distance higher (or,
    when the found distance already equals n-1, by the trivial structural fact that no two
    of n positions can ever be more than n-1 apart, regardless of arrangement).

    If every category appears at most once, there are no same-category pairs at all, so
    every ordering already satisfies any min_distance -- reported as `unconstrained` rather
    than a made-up finite number.
    """
    ids, categories = _validate_items(items)
    _validate_budget(max_search_nodes)

    n = len(ids)
    counts = Counter(categories.values())
    rng = secrets.SystemRandom()

    if max(counts.values()) <= 1:
        arrangement = list(ids)
        rng.shuffle(arrangement)
        verification = verify_arrangement(items, 1, arrangement)
        return {
            "unconstrained": True,
            "reason": "every category appears at most once -- there are no same-category "
            "pairs at all, so every ordering already satisfies any min_distance. 'Maximum "
            "spacing' has no meaningful finite answer here; any arrangement (this one "
            "included) is already optimal.",
            "arrangement": arrangement,
            "max_min_distance": None,
            "verification": verification,
        }

    # min_distance=1 is always feasible (see arrange_with_spacing) -- start the search there.
    ok1, best_arrangement, expanded1, exceeded1 = _search_arrangement(ids, categories, 1, max_search_nodes, rng)
    if exceeded1:
        raise ValueError(
            f"search exceeded max_search_nodes={max_search_nodes} while testing "
            "min_distance=1, the smallest possible value -- try raising max_search_nodes"
        )
    if not ok1:  # pragma: no cover -- min_distance=1 is always feasible by construction
        raise AssertionError("internal error: min_distance=1 must always be feasible")
    best_d = 1
    total_nodes = expanded1

    low, high = 1, n - 1
    while low < high:
        mid = (low + high + 1) // 2
        ok, arrangement, expanded, exceeded = _search_arrangement(ids, categories, mid, max_search_nodes, rng)
        total_nodes += expanded
        if exceeded:
            raise ValueError(
                f"search exceeded max_search_nodes={max_search_nodes} while testing "
                f"min_distance={mid} during the binary search for the maximum feasible "
                "spacing; feasibility at that value could not be determined either way -- "
                "try raising max_search_nodes"
            )
        if ok:
            low = mid
            best_d, best_arrangement = mid, arrangement
        else:
            high = mid - 1

    verification = verify_arrangement(items, best_d, best_arrangement)
    if not verification["valid"]:  # pragma: no cover -- would indicate a solver bug
        raise AssertionError(
            "internal error: maximize_min_distance's own arrangement failed independent verification"
        )

    result = {
        "unconstrained": False,
        "max_min_distance": best_d,
        "arrangement": best_arrangement,
        "verification": verification,
        "total_search_nodes_expanded": total_nodes,
    }

    if best_d >= n - 1:
        result["proof_of_optimality"] = {
            "method": "structural",
            "reason": f"max_min_distance={best_d} already equals n-1={n - 1}, the absolute "
            "ceiling for the distance between any two positions among n items (the two "
            "farthest-apart positions in any ordering are index 0 and index n-1). No "
            "arrangement of these items could ever do better, so no further search is "
            "needed to prove optimality.",
        }
    else:
        ok_next, _, expanded_next, exceeded_next = _search_arrangement(
            ids, categories, best_d + 1, max_search_nodes, rng
        )
        total_nodes += expanded_next
        result["total_search_nodes_expanded"] = total_nodes
        if exceeded_next:
            raise ValueError(
                f"search exceeded max_search_nodes={max_search_nodes} while proving "
                f"min_distance={best_d + 1} is infeasible (the optimality proof for "
                f"max_min_distance={best_d}); try raising max_search_nodes"
            )
        if ok_next:  # pragma: no cover -- would indicate a binary-search bug
            raise AssertionError("internal error: binary search returned a non-maximal min_distance")
        result["proof_of_optimality"] = {
            "method": "exhaustive_search",
            "checked_min_distance": best_d + 1,
            "reason": f"min_distance={best_d + 1} was proven infeasible by exhausting its entire "
            "search tree -- the same exhaustion-is-proof discipline arrange_with_spacing uses "
            "directly -- so max_min_distance is genuinely the largest achievable value, not just "
            "the largest one this search happened to try.",
            "search_nodes_expanded": expanded_next,
        }

    return result


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
