"""Exact STRIPS-style planner + independent plan verifier.

This exists because "planning" is a documented LLM failure mode with a
different shape than the ones already covered elsewhere in this collection.
secure-random and discrete-probability are about getting one formula right;
logic-grid-solver is about holding many *simultaneous* constraints
consistent (constraint satisfaction over a static assignment). Planning is
neither: it's finding a *sequence of state-changing actions* that reaches a
goal, where every action's preconditions depend on the effects of every
action before it. Kambhampati et al.'s Blocksworld benchmarks (and PlanBench)
show standard LLMs -- including with chain-of-thought -- fail reliably on
this once instances grow past a handful of objects, because a valid plan
requires maintaining a consistent world-state across many interdependent
steps and backtracking when a chosen action turns out to make a later goal
unreachable. That's a search problem, not a language problem, so it's
solved here by actual breadth-first search over the grounded state space,
not by asking a model to simulate the world.

Domains are given in a small, fixed JSON-friendly vocabulary instead of PDDL
or ADL -- the same "mechanical transcription instead of formalization" move
logic-grid-solver already makes for its own puzzle shape (and for the same
reason: research on "LLM-as-formalizer" shows models are also unreliable at
translating problems into formal planning languages, so requiring PDDL/ADL
input would just move the failure earlier).

A *fact* (a.k.a. ground literal) is a flat list: [predicate, arg1, arg2, ...],
e.g. ["on", "a", "b"] or ["handempty"] (zero-arity predicates are fine). A
*state* is a set of facts assumed true; anything not listed is assumed false
(the standard STRIPS closed-world assumption).

An *action schema* has a list of parameter names, and preconditions/add/
delete lists of literals written in terms of those parameter names (or of
object constants, if a literal's argument isn't one of the action's own
parameters). A precondition can be negated by prefixing it with "not":
["not", "clear", "x"] means "x is NOT clear" must hold. Add/delete effects
are never negated -- "delete" already says what stops being true.

`solve` grounds every action schema over the supplied objects (all
parameter bindings with distinct objects) and runs breadth-first search from
`initial_state` to any state satisfying `goal`. BFS explores states in
non-decreasing order of the number of actions taken, so the first goal state
found is reached by a *shortest possible* plan -- the search doesn't just
return a plan, it proves that plan is optimal in action count. If the
search exhausts the entire reachable state space without finding the goal,
that's equally a proof: the problem is provably unsolvable under the given
domain, not just "not found within the budget" (which is reported
separately, and distinctly, as an inconclusive result).

`verify_plan` is a deliberately separate, much simpler code path: it just
replays a candidate plan (the solver's own, or a hand-written/model-proposed
one) against the initial state one action at a time, checking every
precondition before applying an action's effects, and reports exactly which
step fails if the plan is invalid -- the same "independent re-check via a
different code path" discipline logic-grid-solver applies to candidate
solutions.

Stdlib only. No network, no account, no dependency beyond `mcp` for the
server wrapper.
"""
from __future__ import annotations

from collections import deque
from itertools import permutations
import random

Literal = tuple  # (predicate, *args)


def describe_planning_format() -> dict:
    """Return the fixed JSON vocabulary for facts, actions, and goals, plus a tiny
    worked example domain (a light switch) showing every piece end to end."""
    example_domain = {
        "objects": ["lamp"],
        "actions": {
            "turn_on": {
                "parameters": ["x"],
                "preconditions": [["not", "on", "x"]],
                "add": [["on", "x"]],
                "delete": [],
            },
            "turn_off": {
                "parameters": ["x"],
                "preconditions": [["on", "x"]],
                "add": [],
                "delete": [["on", "x"]],
            },
        },
        "initial_state": [],
        "goal": [["on", "lamp"]],
    }
    return {
        "fact": "A flat list [predicate, arg1, arg2, ...]. Zero-arity predicates "
        "(no args) are fine, e.g. [\"handempty\"]. A state is the set of facts "
        "currently true; anything not listed is false (closed-world assumption).",
        "action_schema": "An object with 'parameters' (list of parameter names used "
        "in this action's own literals), 'preconditions' (list of literals that must "
        "hold before the action can run), 'add' (facts that become true), and "
        "'delete' (facts that become false). A literal's arguments are substituted "
        "from the action's parameter bindings when the action is grounded over "
        "actual objects; an argument that isn't one of the action's own parameter "
        "names is treated as a literal object constant instead.",
        "negation": "Prefix a precondition literal with \"not\" to require the fact "
        "be absent: [\"not\", \"clear\", \"x\"] means x is NOT clear. Add/delete "
        "effects are never negated -- delete already says what becomes false.",
        "goal": "A list of literals (optionally negated the same way as "
        "preconditions) that must ALL hold simultaneously in the final state.",
        "grounding": "Actions are grounded over the 'objects' list you supply: every "
        "way of binding the action's parameters to distinct objects becomes one "
        "concrete (ground) action the search can take.",
        "example_domain": example_domain,
    }


def _parse_literal(raw, where: str) -> tuple[bool, tuple]:
    """Parse a raw JSON literal into (negated, (predicate, *args))."""
    if not isinstance(raw, list) or not raw or not all(isinstance(x, str) for x in raw):
        raise ValueError(f"{where} must be a non-empty list of strings, got {raw!r}")
    if raw[0] == "not":
        if len(raw) < 2:
            raise ValueError(f"{where}: 'not' requires a predicate to negate")
        return True, tuple(raw[1:])
    return False, tuple(raw)


def _validate_objects(objects) -> list[str]:
    if not isinstance(objects, list) or not objects or not all(isinstance(o, str) for o in objects):
        raise ValueError("objects must be a non-empty list of strings")
    if len(set(objects)) != len(objects):
        raise ValueError(f"objects has duplicates: {objects}")
    return objects


def _validate_actions(actions, objects: list[str]) -> dict:
    if not isinstance(actions, dict) or not actions:
        raise ValueError("actions must be a non-empty object mapping action name -> schema")
    parsed = {}
    for name, schema in actions.items():
        if not isinstance(schema, dict):
            raise ValueError(f"actions['{name}'] must be an object")
        params = schema.get("parameters", [])
        if not isinstance(params, list) or not all(isinstance(p, str) for p in params):
            raise ValueError(f"actions['{name}'].parameters must be a list of strings")
        if len(set(params)) != len(params):
            raise ValueError(f"actions['{name}'].parameters has duplicate names: {params}")
        for p in params:
            if p in objects:
                raise ValueError(
                    f"actions['{name}'] parameter '{p}' collides with an object name; "
                    "parameter names and object names must be disjoint"
                )

        def parse_list(key):
            out = []
            for i, raw in enumerate(schema.get(key, [])):
                out.append(_parse_literal(raw, f"actions['{name}'].{key}[{i}]"))
            return out

        preconditions = parse_list("preconditions")
        add = [lit for neg, lit in parse_list("add") if not neg]
        if len(add) != len(schema.get("add", [])):
            raise ValueError(f"actions['{name}'].add entries cannot be negated")
        delete = [lit for neg, lit in parse_list("delete") if not neg]
        if len(delete) != len(schema.get("delete", [])):
            raise ValueError(f"actions['{name}'].delete entries cannot be negated")

        for neg, lit in preconditions + [(False, l) for l in add] + [(False, l) for l in delete]:
            for arg in lit[1:]:
                if arg not in params and arg not in objects:
                    raise ValueError(
                        f"actions['{name}'] references '{arg}', which is neither a "
                        "declared parameter nor a known object"
                    )
        parsed[name] = {"parameters": params, "preconditions": preconditions, "add": add, "delete": delete}
    return parsed


def _ground_literal(lit: tuple, binding: dict) -> tuple:
    return (lit[0],) + tuple(binding.get(a, a) for a in lit[1:])


def _ground_actions(actions: dict, objects: list[str]) -> list[dict]:
    """Every action schema x every way of binding its parameters to distinct objects."""
    ground = []
    for name, schema in actions.items():
        params = schema["parameters"]
        if not params:
            bindings = [{}]
        else:
            bindings = [dict(zip(params, combo)) for combo in permutations(objects, len(params))]
        for binding in bindings:
            pre_pos = frozenset(_ground_literal(l, binding) for neg, l in schema["preconditions"] if not neg)
            pre_neg = frozenset(_ground_literal(l, binding) for neg, l in schema["preconditions"] if neg)
            add = frozenset(_ground_literal(l, binding) for l in schema["add"])
            delete = frozenset(_ground_literal(l, binding) for l in schema["delete"])
            ground.append(
                {
                    "name": name,
                    "args": [binding[p] for p in params],
                    "pre_pos": pre_pos,
                    "pre_neg": pre_neg,
                    "add": add,
                    "delete": delete,
                }
            )
    return ground


def _applicable(ga: dict, state: frozenset) -> bool:
    return ga["pre_pos"] <= state and not (ga["pre_neg"] & state)


def _apply(ga: dict, state: frozenset) -> frozenset:
    return (state - ga["delete"]) | ga["add"]


def _parse_state(raw, where: str) -> frozenset:
    if not isinstance(raw, list):
        raise ValueError(f"{where} must be a list of facts")
    facts = []
    for i, item in enumerate(raw):
        neg, lit = _parse_literal(item, f"{where}[{i}]")
        if neg:
            raise ValueError(f"{where}[{i}] cannot be negated (a state lists what IS true)")
        facts.append(lit)
    if len(set(facts)) != len(facts):
        raise ValueError(f"{where} has duplicate facts")
    return frozenset(facts)


def _parse_goal(raw, where: str) -> tuple[frozenset, frozenset]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{where} must be a non-empty list of (optionally negated) facts")
    pos, neg = [], []
    for i, item in enumerate(raw):
        is_neg, lit = _parse_literal(item, f"{where}[{i}]")
        (neg if is_neg else pos).append(lit)
    return frozenset(pos), frozenset(neg)


def _goal_satisfied(state: frozenset, goal_pos: frozenset, goal_neg: frozenset) -> bool:
    return goal_pos <= state and not (goal_neg & state)


def _action_to_dict(ga: dict) -> dict:
    return {"action": ga["name"], "args": ga["args"]}


def _state_to_facts(state: frozenset) -> list[list[str]]:
    return sorted([list(f) for f in state])


def solve(
    objects: list,
    initial_state: list,
    goal: list,
    actions: dict,
    max_states: int = 200_000,
    max_depth: int = 60,
) -> dict:
    """Find a shortest plan from initial_state to goal via breadth-first search over
    the grounded state space. Raises ValueError on malformed input. Returns a dict
    with `solvable`; when True, `plan` (list of {action, args}), `plan_length`,
    `optimal` (always True when solvable -- BFS explores shorter plans first, so the
    first goal state found is reached by the fewest possible actions), and
    `states_expanded`. When False, the *entire* reachable state space was exhausted
    without finding the goal -- that's a proof of unsolvability under this domain, not
    an inconclusive result (an inconclusive result -- the search budget ran out first
    -- raises instead, distinguishing "proven impossible" from "couldn't tell").
    """
    objs = _validate_objects(objects)
    parsed_actions = _validate_actions(actions, objs)
    start = _parse_state(initial_state, "initial_state")
    goal_pos, goal_neg = _parse_goal(goal, "goal")
    if max_states < 1:
        raise ValueError("max_states must be >= 1")
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")

    ground_actions = _ground_actions(parsed_actions, objs)

    if _goal_satisfied(start, goal_pos, goal_neg):
        return {
            "solvable": True,
            "plan": [],
            "plan_length": 0,
            "optimal": True,
            "states_expanded": 0,
            "distinct_states_reached": 1,
            "verification": verify_plan(objects, initial_state, goal, actions, []),
        }

    visited = {start: 0}
    parent: dict = {start: None}
    frontier = deque([start])
    states_expanded = 0
    budget_exceeded = False
    depth_capped = False
    goal_state = None

    while frontier:
        state = frontier.popleft()
        states_expanded += 1
        if states_expanded > max_states:
            budget_exceeded = True
            break
        depth = visited[state]
        if depth >= max_depth:
            depth_capped = True
            continue
        for ga in ground_actions:
            if not _applicable(ga, state):
                continue
            new_state = _apply(ga, state)
            if new_state in visited:
                continue
            visited[new_state] = depth + 1
            parent[new_state] = (state, ga)
            if _goal_satisfied(new_state, goal_pos, goal_neg):
                goal_state = new_state
                break
            frontier.append(new_state)
        if goal_state is not None:
            break

    if goal_state is not None:
        plan = []
        s = goal_state
        while parent[s] is not None:
            prev, ga = parent[s]
            plan.append(_action_to_dict(ga))
            s = prev
        plan.reverse()
        verification = verify_plan(objects, initial_state, goal, actions, plan)
        if not verification["valid"]:
            raise AssertionError(  # pragma: no cover -- would indicate a solver bug
                "internal error: solver's own plan failed independent verification"
            )
        return {
            "solvable": True,
            "plan": plan,
            "plan_length": len(plan),
            "optimal": True,
            "states_expanded": states_expanded,
            "distinct_states_reached": len(visited),
            "verification": verification,
        }

    if budget_exceeded or depth_capped:
        raise ValueError(
            f"search exceeded max_states={max_states} (or max_depth={max_depth}) without "
            "reaching the goal or exhausting the reachable state space; solvability could "
            "not be determined either way -- try raising max_states/max_depth"
        )

    return {
        "solvable": False,
        "reason": "the entire reachable state space was explored without ever satisfying "
        "the goal -- the goal is provably unreachable from initial_state under this domain, "
        "not just unfound within a search budget",
        "states_expanded": states_expanded,
        "distinct_states_reached": len(visited),
    }


def verify_plan(objects: list, initial_state: list, goal: list, actions: dict, plan: list) -> dict:
    """Independently replay a candidate plan against initial_state, one ground action at
    a time, checking every precondition before applying its effects. A deliberately
    simpler, separate code path from `solve`'s search (plain forward simulation, no
    grounding-and-search machinery) so a bug in one isn't self-confirmed by the other.
    Returns a full step-by-step trace plus `valid` (every step applicable AND the final
    state satisfies goal) -- use this to check the solver's own plan, or any
    hand-written/model-proposed plan, on its own.

    `plan` is a list of {"action": name, "args": [...]} (the same shape `solve` returns
    in its `plan` field).
    """
    objs = _validate_objects(objects)
    parsed_actions = _validate_actions(actions, objs)
    state = _parse_state(initial_state, "initial_state")
    goal_pos, goal_neg = _parse_goal(goal, "goal")

    if not isinstance(plan, list):
        raise ValueError("plan must be a list of {action, args} steps")

    steps = []
    valid = True
    state_now = state
    for i, step in enumerate(plan):
        if not isinstance(step, dict) or "action" not in step:
            raise ValueError(f"plan[{i}] must be an object with an 'action' field")
        name = step["action"]
        args = step.get("args", [])
        if name not in parsed_actions:
            steps.append({"index": i, "action": name, "args": args, "ok": False, "error": f"unknown action '{name}'"})
            valid = False
            break
        schema = parsed_actions[name]
        if len(args) != len(schema["parameters"]):
            steps.append(
                {
                    "index": i,
                    "action": name,
                    "args": args,
                    "ok": False,
                    "error": f"expects {len(schema['parameters'])} argument(s), got {len(args)}",
                }
            )
            valid = False
            break
        bad_objects = [a for a in args if a not in objs]
        if bad_objects:
            steps.append(
                {
                    "index": i,
                    "action": name,
                    "args": args,
                    "ok": False,
                    "error": f"unknown object(s) {bad_objects}",
                }
            )
            valid = False
            break

        binding = dict(zip(schema["parameters"], args))
        pre_pos = [_ground_literal(l, binding) for neg, l in schema["preconditions"] if not neg]
        pre_neg = [_ground_literal(l, binding) for neg, l in schema["preconditions"] if neg]
        unmet = [list(l) for l in pre_pos if l not in state_now] + [
            ["not"] + list(l) for l in pre_neg if l in state_now
        ]
        if unmet:
            steps.append(
                {
                    "index": i,
                    "action": name,
                    "args": args,
                    "ok": False,
                    "error": "precondition(s) not satisfied",
                    "unmet_preconditions": unmet,
                    "state_before": _state_to_facts(state_now),
                }
            )
            valid = False
            break

        add = {_ground_literal(l, binding) for l in schema["add"]}
        delete = {_ground_literal(l, binding) for l in schema["delete"]}
        state_now = (state_now - delete) | add
        steps.append({"index": i, "action": name, "args": args, "ok": True, "state_after": _state_to_facts(state_now)})

    goal_reached = valid and _goal_satisfied(state_now, goal_pos, goal_neg)
    return {
        "valid": bool(valid and goal_reached),
        "steps_applied": len(steps),
        "steps": steps,
        "final_state": _state_to_facts(state_now),
        "goal_reached": goal_reached,
    }


BLOCKS_WORLD_ACTIONS = {
    "pickup": {
        "parameters": ["x"],
        "preconditions": [["clear", "x"], ["ontable", "x"], ["handempty"]],
        "add": [["holding", "x"]],
        "delete": [["clear", "x"], ["ontable", "x"], ["handempty"]],
    },
    "putdown": {
        "parameters": ["x"],
        "preconditions": [["holding", "x"]],
        "add": [["ontable", "x"], ["clear", "x"], ["handempty"]],
        "delete": [["holding", "x"]],
    },
    "stack": {
        "parameters": ["x", "y"],
        "preconditions": [["holding", "x"], ["clear", "y"]],
        "add": [["on", "x", "y"], ["clear", "x"], ["handempty"]],
        "delete": [["holding", "x"], ["clear", "y"]],
    },
    "unstack": {
        "parameters": ["x", "y"],
        "preconditions": [["on", "x", "y"], ["clear", "x"], ["handempty"]],
        "add": [["holding", "x"], ["clear", "y"]],
        "delete": [["on", "x", "y"], ["clear", "x"], ["handempty"]],
    },
}


def _random_stack_state(objects: list[str], rng: random.Random) -> frozenset:
    """One random arrangement of every block into some number of stacks on the table."""
    order = list(objects)
    rng.shuffle(order)
    facts = {("handempty",)}
    prev_in_stack: dict[str, str | None] = {}
    on_table = set()
    remaining = list(order)
    while remaining:
        stack_len = rng.randint(1, len(remaining))
        stack = remaining[:stack_len]
        remaining = remaining[stack_len:]
        on_table.add(stack[0])
        for below, above in zip(stack, stack[1:]):
            prev_in_stack[above] = below
    for obj in objects:
        if obj in on_table:
            facts.add(("ontable", obj))
        else:
            facts.add(("on", obj, prev_in_stack[obj]))
        if obj not in prev_in_stack.values():
            facts.add(("clear", obj))
    return frozenset(facts)


def generate_blocks_world_problem(num_blocks: int, seed: int | None = None) -> dict:
    """Generate a random Blocksworld problem instance: the classic benchmark domain
    Kambhampati et al. use to show LLMs fail at planning (pick up/put down one block
    at a time, stack/unstack, hand can hold at most one block, a block can only be
    moved if nothing is on top of it). Returns objects, the 4-action domain, a random
    initial_state, and a random goal state -- ready to pass straight into
    solve_planning_problem (and to independently check with verify_plan). Uses a
    seeded stdlib `random.Random`, not secure-random's CSPRNG: this is puzzle-instance
    generation, not a security context, and a seed makes a specific hard instance
    reproducible on request instead of needing this tool's own state to remember it.

    Raises ValueError if num_blocks is out of a sane range (2..8 -- large enough to be
    a genuinely nontrivial planning problem, small enough that solve_planning_problem's
    default search budget comfortably proves optimality).
    """
    if not isinstance(num_blocks, int) or not (2 <= num_blocks <= 8):
        raise ValueError("num_blocks must be an int between 2 and 8")
    rng = random.Random(seed)
    objects = [f"b{i + 1}" for i in range(num_blocks)]
    initial = _random_stack_state(objects, rng)
    goal_state = _random_stack_state(objects, rng)
    while goal_state == initial:
        goal_state = _random_stack_state(objects, rng)
    goal = [list(f) for f in goal_state if f[0] in ("on", "ontable")]
    return {
        "objects": objects,
        "actions": BLOCKS_WORLD_ACTIONS,
        "initial_state": _state_to_facts(initial),
        "goal": goal,
        "seed": seed,
    }
