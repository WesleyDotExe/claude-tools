# strips-planner

An MCP server that exactly solves STRIPS-style planning problems -- find a
sequence of actions that turns an initial state into a goal state -- instead
of asking a language model to hold the whole world-state in its head while
it reasons about what to do next.

## What it solves

Planning is a documented LLM failure mode with a different shape than the
ones already covered elsewhere in this collection. `secure-random` and
`discrete-probability` are about getting one calculation right;
`logic-grid-solver` is about holding many *simultaneous* constraints
consistent over a static assignment. Planning is neither: it's a *sequence*
of state-changing actions where every action's preconditions depend on the
cumulative effects of every action before it, and an early choice can make
a later goal unreachable in a way that isn't obvious until you get there.
That's a search-and-backtrack problem, not a language problem.

Kambhampati et al.'s PlanBench and Blocksworld benchmarks (and several
follow-ups) show standard LLMs -- including with chain-of-thought -- fail
reliably on this once instances grow past a handful of objects, precisely
because generating a plan token-by-token doesn't give the model a place to
maintain a consistent world-state or backtrack when a chosen action turns
out to be a mistake. One general planning MCP server was found in this
cycle's search (`byte4ever/gp`, a Go wrapper around the Graphplan
algorithm), but it requires the caller to already speak PDDL or full ADL
(disjunctive preconditions, conditional effects, quantifiers) to describe
the problem -- and a separate line of research ("LLM-as-formalizer
consistently underperforms LLM-as-solver") shows models are also unreliable
at *that* translation step, which just moves the failure earlier. No
keyless MCP server was found exposing planning through a small, fixed JSON
vocabulary with an independent plan verifier.

This tool takes the same approach `logic-grid-solver` already established
for its own puzzle shape:

1. **A small, fixed JSON vocabulary** (`describe_planning_format`) instead
   of PDDL/ADL -- facts are `[predicate, arg1, arg2, ...]`, actions are
   `{parameters, preconditions, add, delete}`, and a precondition is negated
   by prefixing it with `"not"`. Translating an English domain description
   into this shape is mechanical, not the hard part.
2. **Exact solving via real breadth-first search** over the grounded state
   space -- not asking the model to simulate the world. Because BFS explores
   states in non-decreasing order of actions taken, the first plan found is
   *proven* shortest, not just *a* working plan.
3. **Proof, not assertion**, in the same two ways this collection already
   applies to other problem shapes:
   - If the goal is unreachable, `solve_planning_problem` doesn't just give
     up -- it proves it, by exhausting the entire reachable state space, and
     says so explicitly (`solvable: false`) as distinct from "the search
     budget ran out and we don't actually know" (which raises an error
     instead of silently guessing).
   - `verify_plan` independently replays any candidate plan -- the solver's
     own, or a hand-written/model-proposed one -- one action at a time
     against the domain, via a deliberately separate, much simpler code path
     than the BFS search, and reports exactly which step and which unmet
     precondition breaks it if it's invalid.
4. **A ready-made benchmark generator**: `generate_blocks_world_problem`
   builds a random instance of the classic Blocksworld domain (the exact
   domain the LLM-planning-failure literature uses) with a seeded,
   reproducible RNG, so there's a domain to plan in without writing one.

## Tools exposed

| Tool | Purpose |
|---|---|
| `describe_planning_format` | The fixed JSON vocabulary for facts, action schemas, negation, and goals, plus a tiny worked example (a light switch). Call this first if writing a custom domain. |
| `solve_planning_problem` | Finds a shortest plan from `initial_state` to `goal` given `objects` and `actions`, via breadth-first search over the grounded state space. Returns the plan (proven optimal) or a proof of unsolvability. |
| `verify_plan` | Independently replays any candidate plan against a domain, one action at a time, and reports a full step-by-step trace plus exactly where it breaks (if it does). |
| `generate_blocks_world_problem` | Generates a random, reproducible (seeded) instance of the classic Blocksworld benchmark domain: objects, the 4-action domain, a random `initial_state`, and a random `goal`. |

### The format, briefly

A fact is `[predicate, arg1, ...]`, e.g. `["on", "a", "b"]` or
`["handempty"]` (zero-arity predicates are fine). A state is the set of
facts currently true; the closed-world assumption applies (anything not
listed is false). An action schema:

```json
{
  "parameters": ["x", "y"],
  "preconditions": [["holding", "x"], ["clear", "y"]],
  "add": [["on", "x", "y"], ["clear", "x"], ["handempty"]],
  "delete": [["holding", "x"], ["clear", "y"]]
}
```

Prefix a precondition with `"not"` to negate it: `["not", "clear", "x"]`
means "x is NOT clear". A goal is a list of (optionally negated) facts that
must all hold at once. Call `describe_planning_format` for the exact rules
and a runnable worked example.

## What it doesn't do

It's untyped, propositional STRIPS -- no object types/sorts, no
disjunctive preconditions, no conditional effects, no quantifiers, no
numeric fluents or action costs beyond "every action costs 1." Those are
ADL/PDDL2.1 features; if a domain genuinely needs them, that's what
general PDDL planners (including `byte4ever/gp`, at the cost of its own
formalization-input problem) are for. Search is breadth-first over the full
grounded action set, which is complete and optimal but exponential in the
worst case -- `max_states`/`max_depth` cap it so a genuinely too-large
problem fails predictably (as an inconclusive error) instead of hanging;
this is a sanity bound for exhaustive search, not a tuned performance
limit, the same stance `logic-grid-solver` takes on its own position cap.
`generate_blocks_world_problem` is capped at 2..8 blocks for the same
reason (comfortably inside the default search budget while still being a
genuinely nontrivial instance -- Blocksworld's state space grows fast).

## Files

- `planner.py` -- the actual logic: input validation, action grounding,
  the breadth-first search solver (`solve`), the independent step-by-step
  verifier (`verify_plan`), and the Blocksworld domain + instance generator.
  Stdlib only, no dependency beyond `mcp` for the server wrapper. Usable
  standalone.
- `server.py` -- a thin MCP server (stdio transport) wrapping `planner.py`.
- `tests/test_planner.py` -- 25 unit tests: a light-switch toy domain
  (including a negated-goal case) exercised end to end; the classic Sussman
  anomaly solved and checked against its known-optimal 6-action plan
  (`unstack, putdown, pickup, stack, pickup, stack`); the solver's plan
  independently re-verified via a separate call to `verify_plan`;
  `verify_plan` catching an unmet precondition, a wrong argument count, an
  unknown action, an unknown object, and a plan whose last step succeeds but
  doesn't actually reach the goal; a contradictory goal (`on(a,b)` and
  `on(b,a)` at once) proven unreachable by exhausting the state space, and a
  too-small search budget raising instead of claiming that same proof;
  input validation for every malformed-input path (duplicate objects,
  duplicate initial facts, an unknown predicate argument, a negated add
  effect, a parameter name colliding with an object name); and the
  Blocksworld generator's reproducibility (same seed -> identical instance),
  its generated instances being solvable and independently verifiable across
  ten different seeds, and its `num_blocks` range validation.
- `proof/run_2026-09-18.txt` -- the full test run plus a live MCP client
  session over stdio: `list_tools`, `describe_planning_format`, the Sussman
  anomaly solved in 18 expanded states with the plan independently
  re-verified, a deliberately broken plan (picking up a block still buried
  under another) caught by `verify_plan` with the exact unmet precondition
  named, a generated 5-block Blocksworld instance (seed 2026) solved and
  independently verified, a provably unsolvable goal correctly reported as
  such (state space exhausted, not just unsearched), and a too-small search
  budget correctly coming back as an MCP tool error (`is_error: true`)
  instead of a wrong or silent answer.

## Try it without MCP

```
python3 -c "
import json, planner
objects = ['a', 'b', 'c']
initial = [['on','c','a'], ['ontable','a'], ['ontable','b'], ['clear','b'], ['clear','c'], ['handempty']]
goal = [['on','a','b'], ['on','b','c']]
print(json.dumps(planner.solve(objects, initial, goal, planner.BLOCKS_WORLD_ACTIONS), indent=2))
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
    "strips-planner": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/strips-planner/server.py"]
    }
  }
}
```
