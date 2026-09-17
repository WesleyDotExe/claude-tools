"""Exact solver + independent verifier for logic grid ("zebra") puzzles.

This exists because language models are specifically bad at this puzzle
shape, not just at probability or arithmetic: research on constraint
satisfaction puzzles (e.g. the SAS "Zebra Puzzle Terminator" writeup, and
academic studies of GPT-4o on logic grid puzzles) finds models can break a
puzzle's clues down individually but fail the iterative cross-checking
needed to keep every deduction consistent with every other clue -- reported
success rates as low as 8% on grid logic puzzles of the classic five-house
shape. The general fix in the literature is to hand the puzzle to a real
constraint/SAT/SMT solver, but that requires the model to first translate
the puzzle into SMT-LIB or ASP -- and a separate line of research
("LLM-as-formalizer consistently underperforms LLM-as-solver") shows models
are *also* unreliable at that translation step. This module sidesteps both
failure modes: clues are expressed in a small, fixed JSON vocabulary (see
`describe_clue_types`) that maps almost mechanically from an English clue
("the green house is immediately left of the white house"), so the only
job left for the model is transcription, not formalization -- and solving
happens here, exactly, via backtracking search, not via the model's own
reasoning.

Every puzzle has N positions (1..N, e.g. "houses left to right") and one or
more categories, each a list of exactly N distinct items assigned bijectively
to positions. `solve` finds the (hopefully unique) assignment satisfying
every clue, and *proves* uniqueness by continuing the search for a second,
distinct solution instead of just stopping at the first one it finds -- the
same proof-not-assertion discipline `tools/discrete-probability` and
`tools/secure-random` already apply to their own failure modes, applied here
to "is this puzzle actually well-posed." `verify_solution` independently
re-derives every clue's truth value from a plain position grid (a different
code path and data representation than the solver's internal search state),
so a claimed solution -- the solver's own, or a guess supplied by a caller --
can be checked on its own rather than trusted because the solver said so.

Stdlib only. No network, no account, no dependency beyond `mcp` for the
server wrapper.
"""
from __future__ import annotations

CLUE_TYPES = {
    "position": {
        "fields": ["item", "position"],
        "description": "item is at the given 1-indexed position.",
        "example": {"type": "position", "item": ["nationality", "Norwegian"], "position": 1},
    },
    "same_position": {
        "fields": ["a", "b"],
        "description": "a and b are at the same position (e.g. 'the Brit lives in the red house').",
        "example": {"type": "same_position", "a": ["color", "Red"], "b": ["nationality", "Brit"]},
    },
    "different_position": {
        "fields": ["a", "b"],
        "description": "a and b are at different positions.",
        "example": {"type": "different_position", "a": ["pet", "Dogs"], "b": ["pet", "Cats"]},
    },
    "immediately_left_of": {
        "fields": ["a", "b"],
        "description": "a's position + 1 == b's position (a is directly left of b).",
        "example": {"type": "immediately_left_of", "a": ["color", "Green"], "b": ["color", "White"]},
    },
    "immediately_right_of": {
        "fields": ["a", "b"],
        "description": "a's position - 1 == b's position (a is directly right of b).",
        "example": {"type": "immediately_right_of", "a": ["color", "White"], "b": ["color", "Green"]},
    },
    "left_of": {
        "fields": ["a", "b"],
        "description": "a's position < b's position (a is somewhere left of b, not necessarily adjacent).",
        "example": {"type": "left_of", "a": ["color", "Blue"], "b": ["color", "Red"]},
    },
    "right_of": {
        "fields": ["a", "b"],
        "description": "a's position > b's position (a is somewhere right of b, not necessarily adjacent).",
        "example": {"type": "right_of", "a": ["color", "Red"], "b": ["color", "Blue"]},
    },
    "next_to": {
        "fields": ["a", "b"],
        "description": "a and b are at adjacent positions, either order.",
        "example": {"type": "next_to", "a": ["nationality", "Norwegian"], "b": ["color", "Blue"]},
    },
    "not_next_to": {
        "fields": ["a", "b"],
        "description": "a and b are not at adjacent positions.",
        "example": {"type": "not_next_to", "a": ["pet", "Horses"], "b": ["pet", "Zebra"]},
    },
    "distance": {
        "fields": ["a", "b", "n"],
        "description": "the positions of a and b differ by exactly n (generalizes next_to, which is distance=1).",
        "example": {"type": "distance", "a": ["color", "Red"], "b": ["color", "Blue"], "n": 2},
    },
}


def describe_clue_types() -> dict:
    """Return the supported clue-type vocabulary: fields, meaning, and a worked example
    for each. An item reference (`a`, `b`, or `item`) is always `[category, item]`.
    """
    return {"clue_types": CLUE_TYPES}


def _validate_categories(categories: dict) -> int:
    if not isinstance(categories, dict) or not categories:
        raise ValueError("categories must be a non-empty object mapping category name -> list of items")
    n = None
    for cat, items in categories.items():
        if not isinstance(items, list) or not items:
            raise ValueError(f"category '{cat}' must be a non-empty list of items")
        if len(set(items)) != len(items):
            raise ValueError(f"category '{cat}' has duplicate items: {items}")
        if n is None:
            n = len(items)
        elif len(items) != n:
            raise ValueError(
                f"all categories must have the same number of items (positions); "
                f"'{cat}' has {len(items)}, expected {n}"
            )
    if n > 12:
        raise ValueError(f"{n} positions is too large for exhaustive backtracking search (max 12)")
    return n


def _as_endpoint(ref, categories: dict, where: str) -> tuple:
    if not isinstance(ref, (list, tuple)) or len(ref) != 2:
        raise ValueError(f"{where} must be a [category, item] pair, got {ref!r}")
    cat, item = ref
    if cat not in categories:
        raise ValueError(f"{where} references unknown category '{cat}'")
    if item not in categories[cat]:
        raise ValueError(f"{where} references unknown item '{item}' in category '{cat}'")
    return (cat, item)


def _validate_and_parse_clues(clues: list, categories: dict, n: int) -> list:
    if not isinstance(clues, list) or not clues:
        raise ValueError("clues must be a non-empty list")
    parsed = []
    for i, clue in enumerate(clues):
        where = f"clues[{i}]"
        if not isinstance(clue, dict) or "type" not in clue:
            raise ValueError(f"{where} must be an object with a 'type' field")
        t = clue["type"]
        if t not in CLUE_TYPES:
            raise ValueError(f"{where} has unknown type '{t}'; see describe_clue_types()")
        spec = dict(clue)
        if t == "position":
            item = _as_endpoint(clue.get("item"), categories, f"{where}.item")
            pos = clue.get("position")
            if not isinstance(pos, int) or not (1 <= pos <= n):
                raise ValueError(f"{where}.position must be an int between 1 and {n}")
            spec["item"] = item
            spec["endpoints"] = [item]
        else:
            a = _as_endpoint(clue.get("a"), categories, f"{where}.a")
            b = _as_endpoint(clue.get("b"), categories, f"{where}.b")
            if a == b:
                raise ValueError(f"{where}: a and b refer to the same item")
            spec["a"] = a
            spec["b"] = b
            spec["endpoints"] = [a, b]
            if t == "distance":
                dn = clue.get("n")
                if not isinstance(dn, int) or not (1 <= dn <= n - 1):
                    raise ValueError(f"{where}.n must be an int between 1 and {n - 1}")
                spec["n"] = dn
        parsed.append(spec)
    return parsed


def _clue_holds(clue: dict, pos: dict) -> bool:
    """Evaluate one clue against a fully (for its endpoints) assigned position map.
    `pos` maps (category, item) -> 1-indexed position.
    """
    t = clue["type"]
    if t == "position":
        return pos[clue["item"]] == clue["position"]
    a, b = pos[clue["a"]], pos[clue["b"]]
    if t == "same_position":
        return a == b
    if t == "different_position":
        return a != b
    if t == "immediately_left_of":
        return a + 1 == b
    if t == "immediately_right_of":
        return a - 1 == b
    if t == "left_of":
        return a < b
    if t == "right_of":
        return a > b
    if t == "next_to":
        return abs(a - b) == 1
    if t == "not_next_to":
        return abs(a - b) != 1
    if t == "distance":
        return abs(a - b) == clue["n"]
    raise AssertionError(f"unhandled clue type {t!r}")  # pragma: no cover -- guarded by validation


def _relation_holds(clue: dict, pa: int, pb: int) -> bool:
    """Evaluate a binary clue's relation directly on two candidate positions --
    used by the constraint-propagation search below. Deliberately a separate
    implementation from `_clue_holds` (which operates on a position-lookup dict and
    is used only by `verify_solution`'s independent check), so a bug in one isn't
    self-confirmed by the other.
    """
    t = clue["type"]
    if t == "same_position":
        return pa == pb
    if t == "different_position":
        return pa != pb
    if t == "immediately_left_of":
        return pa + 1 == pb
    if t == "immediately_right_of":
        return pa - 1 == pb
    if t == "left_of":
        return pa < pb
    if t == "right_of":
        return pa > pb
    if t == "next_to":
        return abs(pa - pb) == 1
    if t == "not_next_to":
        return abs(pa - pb) != 1
    if t == "distance":
        return abs(pa - pb) == clue["n"]
    raise AssertionError(f"unhandled clue type {t!r}")  # pragma: no cover -- guarded by validation


def solve(
    categories: dict,
    clues: list,
    prove_unique: bool = True,
    max_solutions: int = 2,
    max_nodes: int = 200_000,
) -> dict:
    """Solve a logic grid puzzle via constraint propagation (arc consistency between
    every clue and the "each category is a bijection to positions" constraint,
    iterated to a fixpoint) plus backtracking search on the most-constrained
    remaining item whenever propagation alone doesn't finish the job. This is the
    standard technique real zebra-puzzle solvers use -- plain brute-force
    backtracking without propagation is asymptotically hopeless even for the
    classic 5-house, 5-category puzzle.

    If `prove_unique`, the search continues past the first solution looking for a
    second, distinct one (stopping at `max_solutions` or `max_nodes`), so the result
    can state whether the puzzle is actually well-posed (exactly one solution) rather
    than just returning *a* solution and hoping the clues pinned it down.

    Raises ValueError if the clues are unsatisfiable (no solution exists) or if the
    input is malformed.
    """
    n = _validate_categories(categories)
    parsed_clues = _validate_and_parse_clues(clues, categories, n)
    if max_solutions < 1:
        raise ValueError("max_solutions must be >= 1")
    cap = max(2, max_solutions) if prove_unique else 1

    cat_names = list(categories.keys())
    binary_clues = [c for c in parsed_clues if c["type"] != "position"]

    domains: dict[tuple, set] = {}
    for cat, items in categories.items():
        for item in items:
            domains[(cat, item)] = set(range(1, n + 1))
    for c in parsed_clues:
        if c["type"] == "position":
            domains[c["item"]] &= {c["position"]}

    def propagate(dom: dict) -> bool:
        """Arc-consistency fixpoint. Returns False the moment any domain empties out
        (a proven contradiction) or two items in one category are forced to the same
        position (violates the bijection every category must be)."""
        changed = True
        while changed:
            changed = False
            for cat, items in categories.items():
                singles = {}
                for item in items:
                    d = dom[(cat, item)]
                    if not d:
                        return False
                    if len(d) == 1:
                        singles[item] = next(iter(d))
                used_vals = list(singles.values())
                if len(set(used_vals)) != len(used_vals):
                    return False
                used_set = set(used_vals)
                for item in items:
                    if item in singles:
                        continue
                    key = (cat, item)
                    before = len(dom[key])
                    dom[key] -= used_set
                    if not dom[key]:
                        return False
                    if len(dom[key]) < before:
                        changed = True
            for c in binary_clues:
                a, b = c["a"], c["b"]
                da, db = dom[a], dom[b]
                new_da = {pa for pa in da if any(_relation_holds(c, pa, pb) for pb in db)}
                if not new_da:
                    return False
                new_db = {pb for pb in db if any(_relation_holds(c, pa, pb) for pa in da)}
                if not new_db:
                    return False
                if len(new_da) < len(da):
                    dom[a] = new_da
                    changed = True
                if len(new_db) < len(db):
                    dom[b] = new_db
                    changed = True
        return True

    solutions: list[dict] = []
    nodes = [0]
    incomplete = [False]

    def search(dom: dict) -> bool:
        """Returns True to signal the caller should stop searching (cap or node budget reached)."""
        nodes[0] += 1
        if nodes[0] > max_nodes:
            incomplete[0] = True
            return True
        if not propagate(dom):
            return False
        unresolved = [(k, d) for k, d in dom.items() if len(d) > 1]
        if not unresolved:
            solutions.append({k: next(iter(d)) for k, d in dom.items()})
            return len(solutions) >= cap
        key, _ = min(unresolved, key=lambda kv: len(kv[1]))
        for val in sorted(dom[key]):
            branched = {k: (set(v) if k != key else {val}) for k, v in dom.items()}
            if search(branched):
                return True
        return False

    search(domains)

    if not solutions:
        if incomplete[0]:
            raise ValueError(
                f"search exceeded max_nodes={max_nodes} without finding a solution; "
                "the puzzle may be unsatisfiable or too large for this solver"
            )
        raise ValueError("no solution satisfies all clues (the clue set is contradictory/over-constrained)")

    solution_by_position = _pos_map_to_grid(solutions[0], cat_names, n)
    verification = verify_solution(categories, clues, solution_by_position)
    if not verification["all_satisfied"]:
        raise AssertionError(  # pragma: no cover -- would indicate a solver bug, not a puzzle-input problem
            "internal error: solver's own solution failed independent verification"
        )

    result = {
        "positions": n,
        "categories": cat_names,
        "solution_by_position": solution_by_position,
        "solution_by_category": {
            cat: {item: p for (c, item), p in solutions[0].items() if c == cat} for cat in cat_names
        },
        "verification": verification,
        "nodes_explored": nodes[0],
    }

    if prove_unique:
        if incomplete[0] and len(solutions) < 2:
            result["unique"] = None
            result["search_incomplete"] = True
            result["note"] = (
                f"stopped after exploring {max_nodes} search nodes without finding a second "
                "solution or exhausting the space; uniqueness could not be proven either way"
            )
        else:
            result["unique"] = len(solutions) == 1
            if len(solutions) > 1:
                result["alternate_solution_by_position"] = _pos_map_to_grid(solutions[1], cat_names, n)
                result["note"] = (
                    "the clues do not pin down a unique solution -- at least one alternate "
                    "solution also satisfies every clue, see alternate_solution_by_position"
                )
    return result


def _pos_map_to_grid(pos: dict, cat_names: list, n: int) -> dict:
    grid = {str(p): {} for p in range(1, n + 1)}
    for (cat, item), p in pos.items():
        grid[str(p)][cat] = item
    return grid


def verify_solution(categories: dict, clues: list, solution_by_position: dict) -> dict:
    """Independently check a candidate solution against every clue and against basic
    well-formedness (every category's items each appear exactly once across positions).

    This does not reuse the solver's internal search state -- it re-derives each item's
    position by scanning `solution_by_position` fresh, the same way an external caller
    (or a model checking its own guess) would have to. Usable standalone: pass a
    hand-written or model-proposed grid and get back a clue-by-clue pass/fail instead of
    trusting the guess on its own say-so.

    `solution_by_position` maps position (1-indexed, as an int or string) -> {category:
    item}, i.e. the same shape `solve()` returns as `solution_by_position`.
    """
    n = _validate_categories(categories)
    parsed_clues = _validate_and_parse_clues(clues, categories, n)

    if not isinstance(solution_by_position, dict):
        raise ValueError("solution_by_position must be an object mapping position -> {category: item}")

    grid = {}
    for p_key, row in solution_by_position.items():
        try:
            p = int(p_key)
        except (TypeError, ValueError):
            raise ValueError(f"solution_by_position key '{p_key}' is not a valid position number")
        if not (1 <= p <= n):
            raise ValueError(f"solution_by_position position {p} is out of range 1..{n}")
        if not isinstance(row, dict):
            raise ValueError(f"solution_by_position[{p_key}] must be an object mapping category -> item")
        grid[p] = row

    structural_errors = []
    if set(grid.keys()) != set(range(1, n + 1)):
        structural_errors.append(f"expected exactly positions 1..{n}, got {sorted(grid.keys())}")
    item_position: dict = {}
    for cat, items in categories.items():
        seen = {}
        for p in range(1, n + 1):
            if p not in grid:
                continue
            row = grid[p]
            if cat not in row:
                structural_errors.append(f"position {p} is missing category '{cat}'")
                continue
            val = row[cat]
            if val not in items:
                structural_errors.append(f"position {p} has unknown item '{val}' for category '{cat}'")
                continue
            if val in seen:
                structural_errors.append(
                    f"category '{cat}' item '{val}' appears at both position {seen[val]} and {p}"
                )
            seen[val] = p
            item_position[(cat, val)] = p
        missing = set(items) - set(seen)
        if missing:
            structural_errors.append(f"category '{cat}' is missing item(s) {sorted(missing)} from the grid")

    clue_results = []
    for i, clue in enumerate(parsed_clues):
        eps = clue["endpoints"]
        if any(ep not in item_position for ep in eps):
            clue_results.append(
                {"index": i, "type": clue["type"], "satisfied": None, "reason": "referenced item missing from grid"}
            )
            continue
        satisfied = _clue_holds(clue, item_position)
        clue_results.append({"index": i, "type": clue["type"], "satisfied": satisfied})

    all_clues_satisfied = all(r["satisfied"] is True for r in clue_results)
    return {
        "well_formed": not structural_errors,
        "structural_errors": structural_errors,
        "clue_results": clue_results,
        "all_satisfied": all_clues_satisfied and not structural_errors,
    }
