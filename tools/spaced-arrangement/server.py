"""MCP server exposing spacedkit's spaced-arrangement solver and its verifier.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from mcp.server.mcpserver import MCPServer

import spacedkit

server = MCPServer(
    name="spaced-arrangement",
    instructions=(
        "Construct an ordering of items such that no two items of the same category are "
        "within min_distance positions of each other, and prove it -- a fifth problem shape "
        "in this collection: combinatorial GENERATION under a guaranteed invariant, distinct "
        "from a single calculation, static constraint satisfaction, sequential action search, "
        "or structural graph algorithms. Real and widely documented: a uniformly random "
        "shuffle of a category-heavy list (a playlist by artist, a task queue by type, an "
        "interview schedule by department) clusters same-category items together far more "
        "than people expect, which is exactly why Spotify and Apple both rewrote their "
        "shuffle algorithms, and why 'reorganize so no two equal items are within k "
        "positions' is a classic, named algorithmic problem (LeetCode 767/621/358). Call "
        "describe_arrangement_format first to see the small fixed JSON vocabulary. "
        "arrange_with_spacing solves it via budgeted backtracking search (CSPRNG-randomized "
        "tie-breaking so repeated calls give different valid orderings, budgeted by "
        "max_search_nodes the same way graph-algorithms' graph_coloring is): exhausting the "
        "whole search tree without a valid completion PROVES no arrangement exists (a simple "
        "per-category frequency check is necessary but NOT sufficient once 3+ categories are "
        "involved -- see the README), while running out of budget first raises instead of "
        "guessing. verify_arrangement independently re-checks any claimed arrangement against "
        "the direct definition -- no search, a different code path than the solver. "
        "generate_arrangement_problem gives a seeded, reproducible instance to experiment with."
    ),
)


@server.tool()
def describe_arrangement_format() -> dict:
    """Describe the fixed JSON vocabulary for items/min_distance, plus a tiny worked
    example. Call this before the other tools if you're building an items list from
    scratch."""
    return spacedkit.describe_arrangement_format()


@server.tool()
def arrange_with_spacing(items: list[dict], min_distance: int = 2, max_search_nodes: int = 200_000) -> dict:
    """Construct an ordering of items so no two items of the SAME category are within
    min_distance positions of each other (min_distance=2 means 'no two adjacent'), via
    budgeted backtracking search with CSPRNG-randomized tie-breaking (repeated calls on
    the same input return different, independently valid orderings). Returns the
    ordering plus an embedded independent verification if one exists, or arrangable:
    false with a proof (the whole search tree was exhausted) if none does. Raises
    instead of guessing if max_search_nodes runs out before resolving either way.
    """
    return spacedkit.arrange_with_spacing(items, min_distance, max_search_nodes)


@server.tool()
def verify_arrangement(items: list[dict], min_distance: int, arrangement: list[str]) -> dict:
    """Independently check a claimed arrangement (the solver's own, a hand-written one,
    or a model's guess) against the direct definition: it's a permutation of the given
    item ids, and every pair of same-category items is at least min_distance positions
    apart. No search at all -- a structurally different, much simpler code path than the
    backtracking solver.
    """
    return spacedkit.verify_arrangement(items, min_distance, arrangement)


@server.tool()
def generate_arrangement_problem(num_items: int, num_categories: int, seed: int | None = None) -> dict:
    """Generate a random, reproducible (seeded) items list -- num_items items spread
    across num_categories categories, every category used at least once -- ready to feed
    into arrange_with_spacing. Uses a seeded stdlib RNG, not a CSPRNG: reproducible
    instance generation, not a security context. Feasibility for any given min_distance
    isn't guaranteed by the generator -- that's what arrange_with_spacing's own search
    (and its exhaustive infeasibility proof) determines.
    """
    return spacedkit.generate_arrangement_problem(num_items, num_categories, seed)


if __name__ == "__main__":
    server.run(transport="stdio")
