"""MCP server exposing puzzlekit's logic-grid-puzzle solver and verifier.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from mcp.server.mcpserver import MCPServer

import puzzlekit

server = MCPServer(
    name="logic-grid-solver",
    instructions=(
        "Exact solver + independent verifier for logic grid puzzles (aka "
        "'zebra puzzles' / Einstein's Riddle) -- clues like 'the green house "
        "is immediately left of the white house' or 'the Norwegian lives "
        "next to the blue house' about N positions and several categories of "
        "items assigned bijectively to them. Language models are "
        "well-documented to do badly on this puzzle shape specifically: they "
        "can break clues down individually but fail the iterative "
        "cross-checking needed to keep every deduction consistent with every "
        "other clue (reported success rates as low as 8% on grid logic "
        "puzzles). Call describe_clue_types first to see the small fixed "
        "clue vocabulary (translate each English clue into it -- this is "
        "mechanical transcription, not the hard part), then solve_logic_grid "
        "with your categories and clues. It returns the exact solution, "
        "proves whether it's the *unique* solution (not just *a* solution), "
        "and independently re-verifies every clue against the answer rather "
        "than asserting it's correct. verify_logic_grid_solution lets you "
        "(or the solver) check any proposed grid -- your own manual attempt "
        "included -- against the clues on its own, standalone."
    ),
)


@server.tool()
def describe_clue_types() -> dict:
    """List the supported clue-type vocabulary (fields, meaning, and a worked example
    for each type): position, same_position, different_position, immediately_left_of,
    immediately_right_of, left_of, right_of, next_to, not_next_to, distance. Call this
    before solve_logic_grid to see exactly how to phrase each clue -- an item reference
    is always `[category, item]`.
    """
    return puzzlekit.describe_clue_types()


@server.tool()
def solve_logic_grid(
    categories: dict[str, list[str]],
    clues: list[dict],
    prove_unique: bool = True,
    max_solutions: int = 2,
    max_nodes: int = 200000,
) -> dict:
    """Solve a logic grid puzzle. `categories` maps category name -> list of exactly N
    distinct item names (N = number of positions, e.g. 5 houses); every category must
    have the same length. `clues` is a list of clue objects in the vocabulary from
    describe_clue_types. Returns the exact solution (both as a per-position grid and
    per-category position map), an independent re-verification of every clue against
    that solution, and -- when prove_unique is true (the default) -- whether the
    puzzle actually has exactly one solution (continuing the search for a second,
    distinct one rather than stopping at the first). Raises an error if the clues are
    contradictory (no solution) or malformed (unknown category/item, out-of-range
    position, etc).
    """
    return puzzlekit.solve(categories, clues, prove_unique, max_solutions, max_nodes)


@server.tool()
def verify_logic_grid_solution(
    categories: dict[str, list[str]],
    clues: list[dict],
    solution_by_position: dict[str, dict[str, str]],
) -> dict:
    """Independently check a candidate solution against every clue and against basic
    well-formedness (every category's items each appear exactly once across
    positions). `solution_by_position` maps position (as a string, "1".."N") to
    {category: item} -- the same shape solve_logic_grid returns as
    solution_by_position. Use this to check a hand-written or model-proposed guess
    instead of trusting it on its own say-so: returns all_satisfied plus a per-clue
    pass/fail, not just a single verdict.
    """
    return puzzlekit.verify_solution(categories, clues, solution_by_position)


if __name__ == "__main__":
    server.run(transport="stdio")
