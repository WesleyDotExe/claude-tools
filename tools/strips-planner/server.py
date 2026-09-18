"""MCP server exposing planner's STRIPS-style state-space planner and verifier.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from mcp.server.mcpserver import MCPServer

import planner

server = MCPServer(
    name="strips-planner",
    instructions=(
        "Exact STRIPS-style planner + independent plan verifier for "
        "'sequence of actions that reaches a goal' problems -- the classic "
        "AI-planning shape (Blocksworld, and any domain you describe the "
        "same way), not a puzzle-constraint or calculation shape. This is a "
        "documented, distinct LLM failure mode from arithmetic or "
        "constraint-satisfaction: research (Kambhampati et al.'s PlanBench, "
        "and follow-ups) shows models fail reliably on this once instances "
        "grow past a handful of objects, because a valid plan requires "
        "tracking a consistent world-state across many interdependent "
        "steps and backtracking when an early choice turns out to block a "
        "later goal -- something autoregressive generation doesn't do. Call "
        "describe_planning_format first to see the small fixed JSON "
        "vocabulary for facts/actions/goals (translating a domain into it "
        "is mechanical, not the hard part), then solve_planning_problem. "
        "It runs real breadth-first search over the grounded state space, "
        "so the plan it returns is PROVEN shortest (optimal action count), "
        "and if no plan exists it PROVES that by exhausting the entire "
        "reachable state space rather than just giving up. verify_plan lets "
        "you (or the solver) independently replay any candidate plan -- "
        "your own manual attempt included -- against the domain, one action "
        "at a time, and see exactly which step fails if it's invalid. "
        "generate_blocks_world_problem gives you a ready-to-use instance of "
        "the classic Blocksworld benchmark domain (seeded, reproducible) if "
        "you want a domain to plan in without writing one yourself."
    ),
)


@server.tool()
def describe_planning_format() -> dict:
    """Describe the fixed JSON vocabulary for facts, action schemas, negation, and
    goals, plus a tiny worked example domain (a light switch) showing every piece.
    Call this before solve_planning_problem if you're writing a custom domain.
    """
    return planner.describe_planning_format()


@server.tool()
def solve_planning_problem(
    objects: list[str],
    initial_state: list[list[str]],
    goal: list[list[str]],
    actions: dict[str, dict],
    max_states: int = 200000,
    max_depth: int = 60,
) -> dict:
    """Find a shortest plan from initial_state to goal by breadth-first search over the
    grounded state space of the given domain. `objects` names everything that exists;
    `actions` maps action name -> {parameters, preconditions, add, delete} (see
    describe_planning_format for the exact literal/negation shape); `initial_state` and
    `goal` are lists of facts (goal facts may be negated). Returns solvable: true with
    the plan, its length, and optimal: true (BFS proves it's the fewest possible
    actions, not just *a* working plan) -- or solvable: false with a proof that the
    goal is unreachable (the entire reachable state space was exhausted, not just
    unsearched). Raises an error if the search budget (max_states/max_depth) runs out
    before either of those is established -- that's reported as inconclusive, distinct
    from a proven "no plan exists."
    """
    return planner.solve(objects, initial_state, goal, actions, max_states, max_depth)


@server.tool()
def verify_plan(
    objects: list[str],
    initial_state: list[list[str]],
    goal: list[list[str]],
    actions: dict[str, dict],
    plan: list[dict],
) -> dict:
    """Independently check a candidate plan (the solver's own, or a hand-written/
    model-proposed one) by replaying it against initial_state one action at a time --
    a separate, simpler code path than solve_planning_problem's search, so a bug in one
    isn't self-confirmed by the other. `plan` is a list of {"action": name, "args":
    [...]}. Returns a full step-by-step trace (each step's ok/error and resulting
    state) plus valid (every step applicable AND the final state satisfies goal) --
    and, on failure, exactly which step and which unmet precondition broke it.
    """
    return planner.verify_plan(objects, initial_state, goal, actions, plan)


@server.tool()
def generate_blocks_world_problem(num_blocks: int, seed: int | None = None) -> dict:
    """Generate a random instance of the classic Blocksworld benchmark domain (pick up/
    put down one block at a time, stack/unstack, hand holds at most one block) --
    objects, the 4-action domain, a random initial_state, and a random goal, ready to
    pass straight into solve_planning_problem. num_blocks must be 2..8. Uses a seeded
    stdlib RNG (not secure-random's CSPRNG -- this is reproducible puzzle-instance
    generation, not a security context): the same seed always returns the same
    instance, so a specific hard case can be regenerated on request.
    """
    return planner.generate_blocks_world_problem(num_blocks, seed)


if __name__ == "__main__":
    server.run(transport="stdio")
