"""MCP server exposing graphkit's exact graph algorithms and their verifiers.

Run: python3 server.py
Wire into an MCP client (e.g. Claude Desktop/Code) with a stdio server
entry pointing at this file. See README.md for a config snippet.
"""
from mcp.server.mcpserver import MCPServer

import graphkit

server = MCPServer(
    name="graph-algorithms",
    instructions=(
        "Exact classic graph algorithms (shortest path, topological sort, minimum "
        "spanning tree, max flow) plus an independent verifier for each -- a fourth "
        "documented LLM failure shape distinct from the rest of this collection: "
        "structural traversal/optimization over an explicit graph, not sequential "
        "action search (strips-planner), constraint satisfaction over a static "
        "assignment (logic-grid-solver), or a single calculation. 2025/2026 graph-"
        "reasoning benchmarks (GraphArena, GraphOmni, GrAlgoBench, GTA) document "
        "accuracy dropping sharply on exactly these algorithm families as graphs grow "
        "past a handful of nodes -- tracking exact running distances, in-degrees, tree "
        "membership, or residual capacities across many nodes at once isn't something "
        "autoregressive generation does reliably. Call describe_graph_format first to "
        "see the small fixed JSON vocabulary for nodes/edges (a mechanical transcription "
        "step, not the hard part). Every solver is implemented via one algorithm and "
        "independently checked via a second, structurally different one: shortest_path "
        "uses Dijkstra and is checked via Bellman-Ford's formal optimality conditions; "
        "topological_sort uses Kahn's algorithm and is checked against the direct "
        "definition (every edge points forward), with a concrete cycle returned as proof "
        "when the graph isn't a DAG; minimum_spanning_tree uses Kruskal's algorithm and "
        "is checked via the cycle-property exchange argument; max_flow uses Edmonds-Karp "
        "and always returns a minimum cut whose capacity equals the flow value, which IS "
        "the optimality proof (max-flow min-cut theorem). generate_random_graph gives a "
        "seeded, reproducible graph to experiment with."
    ),
)


@server.tool()
def describe_graph_format() -> dict:
    """Describe the fixed JSON vocabulary for nodes/edges (and per-tool notes on directed-
    ness, weight vs. capacity, and defaults), plus a tiny worked example graph. Call this
    before the other tools if you're building a graph from scratch."""
    return graphkit.describe_graph_format()


@server.tool()
def shortest_path(nodes: list[str], edges: list[dict], source: str, target: str, directed: bool = True) -> dict:
    """Find the shortest path from source to target via Dijkstra's algorithm (edges need
    weight >= 0; 'weight' defaults to 1 if omitted, so an unweighted graph works too).
    Returns reachable: false with a proof if no path exists, or the path, its total
    distance, and an embedded independent verification (Bellman-Ford-based) proving the
    distance is truly minimal.
    """
    return graphkit.shortest_path(nodes, edges, source, target, directed)


@server.tool()
def verify_shortest_path(
    nodes: list[str], edges: list[dict], source: str, target: str, path: list[str], distance: float, directed: bool = True
) -> dict:
    """Independently check a claimed shortest path (the solver's own, a hand-written one,
    or a model's guess): that it's a genuine walk with weights summing to `distance`, and
    that `distance` is truly minimal, via an independent Bellman-Ford recomputation and
    the formal shortest-path optimality conditions -- a structurally different code path
    than the Dijkstra-based solver.
    """
    return graphkit.verify_shortest_path(nodes, edges, source, target, path, distance, directed)


@server.tool()
def topological_sort(nodes: list[str], edges: list[dict]) -> dict:
    """Find a topological order (every directed edge points forward) via Kahn's algorithm.
    If the graph isn't a DAG, returns is_dag: false with a concrete cycle (found via DFS)
    as proof, instead of just reporting 'cyclic'. Edges are always directed; 'weight', if
    present, is ignored.
    """
    return graphkit.topological_sort(nodes, edges)


@server.tool()
def verify_topological_order(nodes: list[str], edges: list[dict], order: list[str]) -> dict:
    """Independently check a claimed topological order against the direct definition (a
    permutation of nodes where every edge points forward) -- never re-runs Kahn's
    algorithm, so a bug in one isn't self-confirmed by the other.
    """
    return graphkit.verify_topological_order(nodes, edges, order)


@server.tool()
def minimum_spanning_tree(nodes: list[str], edges: list[dict]) -> dict:
    """Find a minimum spanning tree (or forest, if disconnected) via Kruskal's algorithm.
    Always undirected; weight may be any real number. Returns the tree edges, total
    weight, and an embedded independent verification proving minimality.
    """
    return graphkit.minimum_spanning_tree(nodes, edges)


@server.tool()
def verify_minimum_spanning_tree(nodes: list[str], edges: list[dict], tree_edges: list[dict]) -> dict:
    """Independently check a claimed minimum spanning tree/forest: every edge is real,
    it's acyclic, it spans the same components as the full graph, and -- via the
    cycle-property exchange argument -- that no edge outside the tree is lighter than the
    heaviest edge on the tree path it would close into a cycle (the standard mathematical
    proof of MST optimality, a different code path than Kruskal's own search).
    """
    return graphkit.verify_minimum_spanning_tree(nodes, edges, tree_edges)


@server.tool()
def max_flow(nodes: list[str], edges: list[dict], source: str, sink: str) -> dict:
    """Find the maximum flow from source to sink via Edmonds-Karp (directed graph, edges
    need 'capacity' >= 0, no duplicate (from, to) pairs). Always returns a minimum cut
    alongside the flow -- its capacity equals the flow value, which IS the optimality
    proof (max-flow min-cut theorem).
    """
    return graphkit.max_flow(nodes, edges, source, sink)


@server.tool()
def verify_max_flow(
    nodes: list[str], edges: list[dict], source: str, sink: str, flow_edges: list[dict], cut: dict | None = None
) -> dict:
    """Independently check a claimed flow assignment: capacity limits and flow
    conservation at every node except source/sink. Pass `cut` (max_flow's own min_cut, or
    any cut you believe is tight) to additionally prove optimality via the max-flow
    min-cut theorem.
    """
    return graphkit.verify_max_flow(nodes, edges, source, sink, flow_edges, cut)


@server.tool()
def generate_random_graph(
    num_nodes: int,
    num_edges: int,
    seed: int | None = None,
    weighted: bool = True,
    directed: bool = False,
    min_weight: int = 1,
    max_weight: int = 10,
) -> dict:
    """Generate a random, reproducible (seeded) graph -- nodes n1..nN and num_edges
    randomly chosen distinct pairs -- ready to feed into any tool above. Uses a seeded
    stdlib RNG, not secure-random's CSPRNG: this is reproducible instance generation, not
    a security context.
    """
    return graphkit.generate_random_graph(num_nodes, num_edges, seed, weighted, directed, min_weight, max_weight)


if __name__ == "__main__":
    server.run(transport="stdio")
