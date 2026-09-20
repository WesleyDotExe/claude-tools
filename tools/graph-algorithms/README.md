# graph-algorithms

An MCP server that exactly solves the classic graph algorithm problems --
shortest path, topological order, minimum spanning tree, maximum flow,
graph coloring -- instead of asking a language model to track running
distances, in-degrees, tree membership, residual capacities, or color
assignments across many nodes by itself.

## What it solves

"Exact algorithmic reasoning over an explicit graph" is a documented LLM
failure mode with a different shape than anything else in this collection.
`strips-planner` is sequential action search over cumulative world-state;
`logic-grid-solver` is constraint satisfaction over a static assignment;
`secure-random`/`discrete-probability`/`time-arithmetic` are each a single
deterministic calculation. Graph algorithms are a fourth shape: structural
traversal/optimization over an explicit set of nodes and edges, where the
correct next step depends on state (a running distance, an in-degree
count, which tree component a node belongs to, a residual capacity) that
has to stay exactly consistent across the whole computation.

This isn't a hunch -- it's actively benchmarked. GraphArena, GraphOmni,
GrAlgoBench, GTA (Graph Theory Agent), and the paper "Can Language Models
Solve Graph Problems in Natural Language?" all document LLM accuracy
dropping sharply on exactly these classic algorithm families (shortest
path, topological sort, spanning trees, max flow, graph coloring) once
graphs grow past a handful of nodes. This cycle's search found one general
constraint-solving MCP server that can express some of this (`mcp-solver`,
which requires the caller to formalize into SMT-LIB or ASP first -- the
same "LLM-as-formalizer is also unreliable" problem `logic-grid-solver`
and `strips-planner` already sidestep for their own shapes), and one
research prototype (GDS Agent) that requires a running Neo4j Graph Data
Science instance, not a keyless/credential-free fit. No MCP server was
found exposing plain classic graph algorithms through a small, fixed
JSON node/edge vocabulary with an independent verifier.

This tool applies the same discipline the rest of this collection already
established for its own shapes -- **every algorithm is implemented twice,
independently**, so a bug in one isn't self-confirmed by the other:

| Algorithm | Solves via | Independently verified via |
|---|---|---|
| Shortest path | Dijkstra's algorithm (priority-queue greedy search) | Bellman-Ford relaxation (DP, structurally different) checked against the formal shortest-path optimality conditions |
| Topological sort | Kahn's algorithm (repeated zero-in-degree removal) | The direct definition (every edge points forward); a cycle isn't just reported, a concrete one is extracted via DFS as a witness |
| Minimum spanning tree | Kruskal's algorithm (union-find) | The cycle-property exchange argument -- the standard mathematical proof of MST optimality, not a second run of Kruskal's |
| Max flow | Edmonds-Karp (BFS augmenting paths) | Flow conservation + capacity constraints, plus the max-flow min-cut theorem itself: a returned cut of equal capacity proves optimality, independent of how the flow was computed |
| Graph coloring | Backtracking search (DSATUR variable ordering + forward checking, budgeted by `max_search_nodes`) | The direct definition -- every node has one color, no edge joins two same-colored nodes |

`chromatic_number` goes one step further than a solve/verify pair: it finds
the *minimum* number of colors a graph needs, and proves that number is
minimal rather than just reporting a search result. A lower bound comes
for free by exhibiting a clique (`L` pairwise-adjacent nodes each need a
distinct color, so fewer than `L` colors can never work -- no search
required for that half of the proof); a greedy (Welsh-Powell) coloring
gives a guaranteed-reachable upper bound. The backtracking solver then
tries color counts upward from the lower bound, so every count it rules
out along the way was *proven* uncolorable by exhausting the entire search
tree, not merely unfound within a budget -- this cycle's answer to the
"real backtracking-search-with-a-budget story" `graph coloring` needed
before it could be built fully (see `progress/quality-debt.md`'s prior
entry, now resolved).

`generate_random_graph` gives a seeded, reproducible random graph to
experiment with -- the same role `strips-planner`'s Blocksworld generator
plays for planning.

## Tools exposed

| Tool | Purpose |
|---|---|
| `describe_graph_format` | The fixed JSON vocabulary for nodes/edges (directedness, weight vs. capacity, defaults per algorithm), plus a worked example. Call this first. |
| `shortest_path` | Shortest path from `source` to `target` via Dijkstra's algorithm (weight >= 0; defaults to 1, so unweighted graphs work). Returns the path, distance, and an embedded independent (Bellman-Ford) verification. |
| `verify_shortest_path` | Independently checks any claimed path + distance: it's a real walk, and the distance is truly minimal. |
| `topological_sort` | A valid order via Kahn's algorithm, or `is_dag: false` with a concrete cycle if none exists. |
| `verify_topological_order` | Independently checks any claimed order against the direct definition. |
| `minimum_spanning_tree` | A minimum spanning tree (or forest, if disconnected) via Kruskal's algorithm, with an embedded independent (cycle-property) verification. |
| `verify_minimum_spanning_tree` | Independently checks any claimed tree/forest: real edges, acyclic, fully spanning, and minimal. |
| `max_flow` | Maximum flow from `source` to `sink` via Edmonds-Karp, always returned with a minimum cut whose capacity IS the optimality proof. |
| `verify_max_flow` | Independently checks any claimed flow assignment (conservation + capacity), and, given a cut, whether it proves optimality. |
| `graph_coloring` | A proper coloring using at most `num_colors` colors via backtracking search (DSATUR + forward checking), or `colorable: false` proven by exhausting the whole search tree. |
| `verify_coloring` | Independently checks any claimed coloring against the direct definition (no search). |
| `chromatic_number` | The minimum colors needed: a clique lower bound (no search) plus backtracking search upward, proving every smaller count impossible along the way. |
| `generate_random_graph` | A seeded, reproducible random graph to experiment with. |

### The format, briefly

```json
{
  "nodes": ["A", "B", "C", "D"],
  "edges": [
    {"from": "A", "to": "B", "weight": 1},
    {"from": "B", "to": "C", "weight": 2},
    {"from": "A", "to": "C", "weight": 5},
    {"from": "C", "to": "D", "weight": 1}
  ]
}
```

`weight` is optional (defaults to 1). Self-loops are always rejected. Most
tools take a `directed` boolean read against the same edge list.
`max_flow`/`verify_max_flow` use `capacity` instead of `weight` (required,
no default, no duplicate `(from, to)` pairs). `minimum_spanning_tree` and
the graph-coloring tools (`graph_coloring`, `verify_coloring`,
`chromatic_number`) are always undirected, ignoring `weight`/`directed`
entirely; `topological_sort` is always directed. Call
`describe_graph_format` for the exact rules.

## What it doesn't do

No maximum matching or general LP-style network optimization -- real,
also-documented LLM failure shapes (this collection's research found them
too), but out of scope for this cycle. Graph coloring itself -- the one gap
explicitly left open in the previous cycle's README and
`progress/quality-debt.md` -- is now built (`graph_coloring`,
`verify_coloring`, `chromatic_number`), with its own backtracking-search
budget (`max_search_nodes`, same contract as `strips-planner`'s
`max_states`/`max_depth`: exhausting the search tree is a proof, running
out of budget first raises rather than guessing). `chromatic_number`'s
search is exponential in the worst case like any exact graph-coloring
algorithm; the clique lower bound and greedy upper bound keep the typical
case fast, but a dense, adversarially hard instance can still exhaust
`max_search_nodes` -- raise it, or accept an inconclusive result staying
inconclusive rather than silently wrong. `shortest_path` requires non-negative
weights (Dijkstra's own requirement); negative-weight shortest paths need
a different algorithm family (Bellman-Ford as the primary solver, plus
negative-cycle handling) and aren't supported as the main entry point here
-- though `verify_shortest_path`'s own Bellman-Ford recomputation would
already detect a negative cycle if one existed. `max_flow` doesn't allow
parallel edges between the same ordered pair (combine them into one
edge with the summed capacity first) or edge costs (this is max flow, not
min-cost flow). Graphs are capped implicitly by Python's plain
(non-vectorized) implementations -- fine for the sizes these tools are
meant for (tens to low hundreds of nodes), not tuned for very large graphs,
the same "correctness over raw throughput" tradeoff `secure-random`'s
`verify_uniformity` already documents for itself.

## Files

- `graphkit.py` -- the actual logic: input validation, the five
  algorithm/verifier pairs (shortest path, topological sort, minimum
  spanning tree, max flow, graph coloring -- plus `chromatic_number`'s
  clique-lower-bound-and-search minimality proof), and the random graph
  generator. Stdlib only, no dependency beyond `mcp` for the server
  wrapper. Usable standalone.
- `server.py` -- a thin MCP server (stdio transport) wrapping `graphkit.py`.
- `tests/test_graphkit.py` -- 61 unit tests: a known-by-hand shortest path
  on a small directed weighted graph (cross-checked against a manual
  calculation), directed-vs-undirected edge traversal, unreachable targets
  proven rather than guessed, negative weights rejected; a diamond DAG's
  topological order, a 3-cycle's concrete witness extracted and checked
  against the real edge set, a partial cycle correctly leaving the acyclic
  part ordered; a known-minimum spanning tree cross-checked by hand,
  disconnected graphs correctly returning a forest, a deliberately
  suboptimal tree caught by the cycle-property check with the exact
  violating edge named; a known max-flow value on a small textbook flow
  network, flow conservation and capacity checked directly, a capacity
  violation and a conservation violation each caught, a flow's optimality
  correctly reported as unproven without a matching cut and correctly
  rejected when given a mismatched one; a triangle correctly colorable with
  3 colors but proven uncolorable with 2, a bipartite 4-cycle colored with
  2, weight/directedness confirmed ignored, a too-small search budget
  raising instead of guessing; `verify_coloring` catching a shared color on
  adjacent nodes, a missing node, an unexpected node, and a bad color
  type, while accepting both integer and string color labels; a triangle's
  chromatic number (3) proven by the clique bound alone with zero search,
  a 4-cycle's (2) the same way, and a 5-cycle's (3) requiring real
  exhaustive search at k=2 first since it's triangle-free (clique bound
  only 2) -- the case that actually exercises the search, not just the
  bound; a generated random graph's chromatic number cross-checked by
  confirming one fewer color is genuinely uncolorable; the random
  generator's reproducibility and composability with the other tools; and
  input validation for every malformed-input path shared across all
  algorithms (duplicate nodes, self-loops, unknown node references,
  non-numeric weights).
- `proof/run_2026-09-20.txt` -- the full test run plus a live MCP client
  session over stdio: `list_tools`, the known shortest path solved and
  independently verified, a diamond DAG ordered and a 3-cycle's concrete
  witness returned, the known MST found and a deliberately suboptimal one
  caught via the cycle-property check, the known max flow found with its
  matching min cut, a triangle colored with 3 colors and proven
  uncolorable with 2, `verify_coloring` catching two adjacent nodes
  sharing a color, a 5-cycle's chromatic number (3) found with real search
  at k=2 first, a too-small `max_search_nodes` budget correctly coming
  back as an MCP tool error instead of a wrong "not colorable" answer, a
  generated random graph fed straight into `chromatic_number`, and
  `shortest_path` confirmed still working unchanged alongside the new
  tools.

## Try it without MCP

```
python3 -c "
import json, graphkit
nodes = ['A', 'B', 'C', 'D', 'E']
edges = [
    {'from': 'A', 'to': 'B', 'weight': 6}, {'from': 'A', 'to': 'C', 'weight': 3},
    {'from': 'C', 'to': 'B', 'weight': 2}, {'from': 'B', 'to': 'D', 'weight': 1},
    {'from': 'C', 'to': 'D', 'weight': 5}, {'from': 'D', 'to': 'E', 'weight': 2},
    {'from': 'B', 'to': 'E', 'weight': 6},
]
print(json.dumps(graphkit.shortest_path(nodes, edges, 'A', 'E'), indent=2))
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
    "graph-algorithms": {
      "command": "python3",
      "args": ["/absolute/path/to/tools/graph-algorithms/server.py"]
    }
  }
}
```
