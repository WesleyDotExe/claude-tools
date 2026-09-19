# graph-algorithms

An MCP server that exactly solves the classic graph algorithm problems --
shortest path, topological order, minimum spanning tree, maximum flow --
instead of asking a language model to track running distances, in-degrees,
tree membership, or residual capacities across many nodes by itself.

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
no default, no duplicate `(from, to)` pairs). `minimum_spanning_tree` is
always undirected; `topological_sort` is always directed. Call
`describe_graph_format` for the exact rules.

## What it doesn't do

No graph coloring, maximum matching, or general LP-style network
optimization -- those are real, also-documented LLM failure shapes (this
cycle's research found them too), but graph coloring in particular is
NP-hard in a way that needs real backtracking-search infrastructure with
its own budget/pruning story to build *fully*, and folding it in alongside
four other algorithm families in one cycle would have meant doing it
half-attentively. Left for a future cycle if a concrete need surfaces (see
`progress/notes-for-owner.md`). `shortest_path` requires non-negative
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

- `graphkit.py` -- the actual logic: input validation, the four
  algorithm/verifier pairs, and the random graph generator. Stdlib only,
  no dependency beyond `mcp` for the server wrapper. Usable standalone.
- `server.py` -- a thin MCP server (stdio transport) wrapping `graphkit.py`.
- `tests/test_graphkit.py` -- 44 unit tests: a known-by-hand shortest path
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
  rejected when given a mismatched one; the random generator's
  reproducibility and composability with the other tools; and input
  validation for every malformed-input path shared across all four
  algorithms (duplicate nodes, self-loops, unknown node references,
  non-numeric weights).
- `proof/run_2026-09-19.txt` -- the full test run plus a live MCP client
  session over stdio: `list_tools`, `describe_graph_format`, the known
  shortest path solved and independently verified, a deliberately wrong
  distance claim caught, a diamond DAG ordered and a 3-cycle's concrete
  witness returned, the known MST found and a deliberately suboptimal one
  caught via the cycle-property check, the known max flow found with its
  matching min cut (both proving each other optimal) and a deliberately
  invalid flow assignment caught, a generated random graph fed straight
  into `minimum_spanning_tree`, and a negative edge weight correctly
  coming back as an MCP tool error (`is_error: true`) instead of a wrong
  or silent answer.

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
