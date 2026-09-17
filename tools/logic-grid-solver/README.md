# logic-grid-solver

An MCP server that exactly solves logic grid puzzles ("zebra puzzles" /
Einstein's Riddle) — the "5 houses, 5 categories, 15 clues, who owns the
zebra?" shape — instead of asking a language model to hold the whole
deduction chain in its head.

## What it solves

Language models are specifically bad at this puzzle shape, not just at
arithmetic or probability. Research on logic grid puzzles finds models can
break individual clues down but fail the *iterative cross-checking* needed
to keep every deduction consistent with every other clue at once — a
documented failure mode distinct from "can't do math," with reported
success rates as low as 8% on this exact puzzle format.

The standard fix in the literature is to hand the puzzle to a real
constraint/SAT/SMT solver — and MCP servers for that already exist
(`z3-solver-mcp-server`, `mcp-solver`, both found in this cycle's search).
But those require the calling model to first translate the puzzle into
SMT-LIB or ASP syntax, and a separate line of research ("LLM-as-formalizer
consistently underperforms LLM-as-solver") shows models are *also*
unreliable at that translation step — the failure just moves earlier and
gets harder to spot. No MCP server exposing a logic-grid-puzzle-specific
solver with a simple structured clue vocabulary was found in the existing
MCP ecosystem (the JSON `same_house`/`next_to`/`left_of` clue shape itself
already exists in a few non-MCP web solvers, e.g. the CacheSleuth logic
solver and `zebra4j`, which is a strong signal it's a natural fit, just not
one anyone had exposed as an MCP tool yet).

This tool closes both gaps at once:

1. **A small, fixed clue vocabulary** (`describe_clue_types`) that maps
   almost mechanically from an English clue ("the green house is
   immediately left of the white house" → `immediately_left_of`) — the only
   job left for the calling model is transcription, not formalization.
2. **Exact solving via constraint propagation** (arc consistency between
   every clue and the "each category is a bijection to positions"
   constraint, iterated to a fixpoint, with backtracking on the
   most-constrained remaining item whenever propagation alone doesn't
   finish) — the standard technique real zebra-puzzle solvers use.
3. **Proof, not assertion**, in two ways, extending the same discipline
   already established in this collection by `secure-random` and
   `discrete-probability`:
   - `solve_logic_grid` doesn't stop at the first solution it finds — by
     default it keeps searching for a *second*, distinct one, so it can
     state the puzzle is actually well-posed (`unique: true`) instead of
     just returning an answer and hoping the clues pinned it down. If a
     second solution exists, it's returned too (`alternate_solution_by_position`).
   - Every solution is independently re-verified: `verify_logic_grid_solution`
     re-derives each clue's truth value by scanning the grid fresh, a
     different code path and data representation than the solver's own
     internal search state, and it's exposed standalone — so a model (or a
     person) can check *any* proposed grid, including its own manual guess,
     against the clues instead of trusting an answer on say-so.

## Tools exposed

| Tool | Purpose |
|---|---|
| `describe_clue_types` | Lists the supported clue vocabulary (fields, meaning, worked example for each type). Call this first. |
| `solve_logic_grid` | Solves a puzzle given `categories` (name → list of N items) and `clues`. Returns the exact solution, an independent re-verification of every clue, and (by default) a proof of uniqueness. |
| `verify_logic_grid_solution` | Independently checks any candidate grid (the solver's own answer, or a hand-written/model-proposed guess) against the clues and against basic well-formedness. |

### Clue vocabulary

Every item reference is `[category, item]`. Ten clue types cover essentially
every phrasing that appears in classic logic grid puzzles:

`position`, `same_position`, `different_position`, `immediately_left_of`,
`immediately_right_of`, `left_of`, `right_of`, `next_to`, `not_next_to`,
`distance` (generalizes `next_to` to an arbitrary gap). See
`puzzlekit.CLUE_TYPES` or call `describe_clue_types` for the exact fields
and an example of each.

## What it doesn't do

It does not parse English clues into this JSON vocabulary — like the rest
of this collection, it computes once the input is already unambiguous, not
from prose. It does not support "between three items" clues (e.g. "there is
one house between the red house and the blue house, in either direction" —
partially expressible via `distance`, but not the fully general three-way
case) or quantified clues ("at least one of X or Y is true") — the ten
clue types cover ordinary logic grid puzzles, not arbitrary first-order
constraints (that's what `z3-solver-mcp-server`/`mcp-solver` are for, at the
cost of needing SMT-LIB/ASP formalization instead of this tool's simpler
vocabulary). Puzzles are capped at 12 positions per category, a sanity
bound for exhaustive search, not a tuned performance limit.

## Files

- `puzzlekit.py` — the actual logic: clue validation, the constraint-
  propagation solver (`solve`), and the independent verifier
  (`verify_solution`). Stdlib only, no dependency beyond `mcp` for the
  server wrapper. Usable standalone.
- `server.py` — a thin MCP server (stdio transport) wrapping `puzzlekit.py`.
- `tests/test_puzzlekit.py` — 28 unit tests: the classic 5-house Einstein
  zebra puzzle solved end-to-end and checked against its published answer
  (the German owns the zebra, the Norwegian drinks water), its uniqueness
  proven, every one of its 15 clues independently re-verified; every clue
  type exercised on a small hand-checkable puzzle; contradictory clues
  raising instead of returning a wrong answer; an under-constrained puzzle
  correctly reported as *not* unique with a concrete alternate solution; the
  verifier catching a deliberately wrong guess and structurally malformed
  grids (duplicate/missing items) instead of rubber-stamping them; and
  input validation for every malformed-input path.
- `proof/run_2026-09-17.txt` — the full test run plus a live MCP client
  session over stdio: `list_tools`, `describe_clue_types`, the classic zebra
  puzzle solved and proven unique, its own solution independently
  re-verified, a deliberately wrong guess caught by the verifier, an
  under-constrained puzzle correctly reported as not unique (with the
  alternate solution), and contradictory clues coming back as an MCP tool
  error instead of a silently wrong answer.

## Try it without MCP

```
python3 -c "
import puzzlekit
categories = {'color': ['Red', 'Green', 'Blue'], 'animal': ['Cat', 'Dog', 'Fish']}
clues = [
    {'type': 'position', 'item': ['color', 'Red'], 'position': 1},
    {'type': 'left_of', 'a': ['color', 'Green'], 'b': ['color', 'Blue']},
]
import json
print(json.dumps(puzzlekit.solve(categories, clues), indent=2))
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
    "logic-grid-solver": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/logic-grid-solver/server.py"]
    }
  }
}
```
