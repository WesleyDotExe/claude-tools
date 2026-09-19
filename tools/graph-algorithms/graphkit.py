"""Exact graph algorithms + independent verifiers.

This exists because "exact algorithmic reasoning over an explicit graph" is
a documented LLM failure mode with a different shape than anything else in
this collection. `strips-planner` is sequential action search over
cumulative world-state; `logic-grid-solver` is constraint satisfaction over
a static assignment; `secure-random`/`discrete-probability`/`time-arithmetic`
are each a single deterministic calculation. Graph algorithms are a fourth
shape: structural traversal/optimization over an explicit set of nodes and
edges (shortest paths, ordering under dependencies, minimum connection cost,
maximum throughput) -- classic, well-defined problems models get wrong not
because the concept is unclear but because tracking exact distances,
degrees, or residual capacities across many nodes at once, updated as the
computation proceeds, isn't something autoregressive generation does
reliably. 2025/2026 benchmarks built specifically to test this (GraphArena,
GraphOmni, GrAlgoBench, GTA, and "Can Language Models Solve Graph Problems
in Natural Language?") document accuracy dropping sharply as graphs grow
past a handful of nodes, on exactly these classic algorithm families.

Every algorithm here is implemented twice, independently, the same
proof-not-assertion discipline the rest of this collection already applies
to its own problem shapes:

- `shortest_path` solves via Dijkstra's algorithm; `verify_shortest_path`
  independently recomputes via Bellman-Ford (a structurally different
  algorithm -- DP relaxation instead of a greedy priority queue) and checks
  the formal shortest-path optimality conditions (dist[source] = 0, and
  dist[v] <= dist[u] + weight(u, v) for every edge), not just "do the
  numbers match."
- `topological_sort` solves via Kahn's algorithm (repeatedly removing
  zero-in-degree nodes); `verify_topological_order` independently checks
  the direct definition (every edge points forward in the order) rather
  than re-running Kahn's. When the graph isn't a DAG, a concrete cycle is
  extracted via DFS as a witness, instead of just reporting "cyclic."
- `minimum_spanning_tree` solves via Kruskal's algorithm (union-find);
  `verify_minimum_spanning_tree` independently proves minimality via the
  cycle-property exchange argument (for every edge outside the tree,
  confirm it isn't lighter than the heaviest edge on the tree path it would
  close into a cycle) -- the standard mathematical proof of MST optimality,
  not a second run of Kruskal's.
- `max_flow` solves via Edmonds-Karp (BFS augmenting paths) and always
  returns a minimum cut alongside the flow; `verify_max_flow` independently
  checks flow conservation and capacity constraints, and (given a cut) uses
  the max-flow min-cut theorem itself as the optimality proof: any flow's
  value is <= any cut's capacity, so a cut with capacity equal to the flow
  proves both are optimal, regardless of how the flow was computed.

`generate_random_graph` gives a seeded, reproducible random graph to
experiment with, the same role `strips-planner`'s Blocksworld generator
plays for planning.

Stdlib only. No network, no account, no dependency beyond `mcp` for the
server wrapper.
"""
from __future__ import annotations

import heapq
import math
import random
from collections import defaultdict, deque

# ---------------------------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------------------------


def _validate_nodes(nodes) -> list[str]:
    if not isinstance(nodes, list) or not nodes or not all(isinstance(n, str) for n in nodes):
        raise ValueError("nodes must be a non-empty list of strings")
    if len(set(nodes)) != len(nodes):
        raise ValueError(f"nodes has duplicates: {nodes}")
    return nodes


def _validate_node_ref(node, nodes_set: set, where: str) -> None:
    if not isinstance(node, str) or node not in nodes_set:
        raise ValueError(f"{where} must be one of the declared nodes, got {node!r}")


def _parse_weighted_edges(edges, nodes: list[str], *, allow_negative: bool = True) -> list[tuple]:
    """Parse a list of {"from", "to", "weight"} edges. `weight` defaults to 1.
    Returns a list of (u, v, weight) tuples. Self-loops are rejected."""
    nodes_set = set(nodes)
    if not isinstance(edges, list):
        raise ValueError("edges must be a list")
    parsed = []
    for i, e in enumerate(edges):
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            raise ValueError(f"edges[{i}] must be an object with 'from' and 'to'")
        u, v = e["from"], e["to"]
        _validate_node_ref(u, nodes_set, f"edges[{i}].from")
        _validate_node_ref(v, nodes_set, f"edges[{i}].to")
        if u == v:
            raise ValueError(f"edges[{i}] is a self-loop ({u} -> {u}); not supported")
        w = e.get("weight", 1)
        if not isinstance(w, (int, float)) or isinstance(w, bool):
            raise ValueError(f"edges[{i}].weight must be a number, got {w!r}")
        if not allow_negative and w < 0:
            raise ValueError(f"edges[{i}].weight must be >= 0, got {w}")
        parsed.append((u, v, float(w)))
    return parsed


def _parse_flow_edges(edges, nodes: list[str]) -> list[tuple]:
    """Parse a list of {"from", "to", "capacity"} edges for max_flow. `capacity` is
    required (no default -- an unweighted flow network isn't a meaningful concept).
    Rejects self-loops and duplicate (from, to) pairs."""
    nodes_set = set(nodes)
    if not isinstance(edges, list):
        raise ValueError("edges must be a list")
    parsed = []
    seen = set()
    for i, e in enumerate(edges):
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            raise ValueError(f"edges[{i}] must be an object with 'from' and 'to'")
        u, v = e["from"], e["to"]
        _validate_node_ref(u, nodes_set, f"edges[{i}].from")
        _validate_node_ref(v, nodes_set, f"edges[{i}].to")
        if u == v:
            raise ValueError(f"edges[{i}] is a self-loop ({u} -> {u}); not supported")
        if "capacity" not in e:
            raise ValueError(f"edges[{i}] must include 'capacity' (no default for a flow network)")
        cap = e["capacity"]
        if not isinstance(cap, (int, float)) or isinstance(cap, bool) or cap < 0:
            raise ValueError(f"edges[{i}].capacity must be a number >= 0, got {cap!r}")
        if (u, v) in seen:
            raise ValueError(
                f"edges[{i}]: duplicate edge {u} -> {v}; combine parallel edges into one "
                "with the summed capacity first"
            )
        seen.add((u, v))
        parsed.append((u, v, float(cap)))
    return parsed


class _UnionFind:
    """Disjoint-set forest with path compression + union by rank."""

    def __init__(self, items):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


# ---------------------------------------------------------------------------
# Format description
# ---------------------------------------------------------------------------


def describe_graph_format() -> dict:
    """Return the fixed JSON vocabulary for nodes/edges, plus a tiny worked example."""
    example_nodes = ["A", "B", "C", "D"]
    example_edges = [
        {"from": "A", "to": "B", "weight": 1},
        {"from": "B", "to": "C", "weight": 2},
        {"from": "A", "to": "C", "weight": 5},
        {"from": "C", "to": "D", "weight": 1},
    ]
    return {
        "nodes": "A non-empty list of unique node-name strings.",
        "edge": "An object {\"from\": node, \"to\": node, \"weight\": number}. 'weight' is "
        "optional and defaults to 1 (an unweighted graph is just edges without it). "
        "Self-loops (from == to) are rejected everywhere.",
        "directed": "Most tools take a separate 'directed' boolean: the same edge list is "
        "read as one-way (from -> to only) or two-way (both directions) depending on it.",
        "per_tool_notes": {
            "shortest_path": "Requires weight >= 0 -- Dijkstra's algorithm (used to solve) "
            "requires non-negative weights; negative-weight shortest paths need a different "
            "algorithm family and aren't supported here.",
            "minimum_spanning_tree": "Always undirected (no 'directed' parameter); weight may "
            "be any real number, including negative or zero -- Kruskal's algorithm doesn't "
            "care about sign.",
            "topological_sort": "Always directed; 'weight', if present, is ignored.",
            "max_flow": "Directed, with a 'capacity' field instead of 'weight' (required, "
            "must be >= 0, no default). Parallel edges between the same ordered pair are "
            "rejected -- combine them into one edge with the summed capacity first.",
        },
        "example_graph": {"nodes": example_nodes, "edges": example_edges},
    }


# ---------------------------------------------------------------------------
# Shortest path: Dijkstra (solve) + Bellman-Ford (independent verify)
# ---------------------------------------------------------------------------


def shortest_path(nodes: list, edges: list, source: str, target: str, directed: bool = True) -> dict:
    """Find the shortest path from source to target via Dijkstra's algorithm. Requires
    weight >= 0 on every edge. Returns reachable: false with a proof (Dijkstra's whole
    frontier from source was exhausted without reaching target) if there's no path, or
    the path, its total distance, and an independent Bellman-Ford-based verification
    proving the distance is truly minimal -- not just *a* path."""
    nodes = _validate_nodes(nodes)
    nodes_set = set(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=False)
    _validate_node_ref(source, nodes_set, "source")
    _validate_node_ref(target, nodes_set, "target")

    adj: dict[str, list[tuple[str, float]]] = {n: [] for n in nodes}
    for u, v, w in parsed:
        adj[u].append((v, w))
        if not directed:
            adj[v].append((u, w))

    dist = {n: math.inf for n in nodes}
    prev: dict[str, str | None] = {n: None for n in nodes}
    dist[source] = 0.0
    visited = set()
    heap = [(0.0, source)]
    nodes_expanded = 0
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        nodes_expanded += 1
        if u == target:
            break
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    if dist[target] == math.inf:
        return {
            "reachable": False,
            "reason": f"no path exists from '{source}' to '{target}' -- Dijkstra's algorithm "
            "explored every node reachable from source (its frontier emptied) without ever "
            "reaching target",
            "nodes_expanded": nodes_expanded,
        }

    path = []
    cur: str | None = target
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    verification = verify_shortest_path(nodes, edges, source, target, path, dist[target], directed=directed)
    if not verification["valid"]:
        raise AssertionError(  # pragma: no cover -- would indicate a solver bug
            "internal error: solver's own path failed independent verification"
        )
    return {
        "reachable": True,
        "path": path,
        "distance": dist[target],
        "nodes_expanded": nodes_expanded,
        "verification": verification,
    }


def verify_shortest_path(
    nodes: list, edges: list, source: str, target: str, path: list, distance: float, directed: bool = True
) -> dict:
    """Independently check a claimed shortest path (the solver's own, or a hand-written/
    model-proposed one): (1) it's a genuine walk from source to target using real edges,
    with weights summing to `distance`, and (2) `distance` really is minimal, proven by
    recomputing it via Bellman-Ford -- a structurally different algorithm (DP relaxation,
    not a priority-queue greedy search) than Dijkstra's algorithm `shortest_path` uses --
    and confirming the formal optimality conditions (dist[source] = 0, and
    dist[v] <= dist[u] + weight(u, v) for every edge)."""
    nodes = _validate_nodes(nodes)
    nodes_set = set(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=False)
    _validate_node_ref(source, nodes_set, "source")
    _validate_node_ref(target, nodes_set, "target")
    if not isinstance(path, list) or not all(isinstance(p, str) for p in path):
        raise ValueError("path must be a list of node-name strings")
    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        raise ValueError("distance must be a number")

    directed_edges = list(parsed)
    if not directed:
        directed_edges += [(v, u, w) for u, v, w in parsed]
    edge_weight: dict[tuple, float] = {}
    for u, v, w in directed_edges:
        if (u, v) not in edge_weight or w < edge_weight[(u, v)]:
            edge_weight[(u, v)] = w

    path_errors = []
    path_ok = bool(path) and path[0] == source and path[-1] == target
    if not path_ok:
        path_errors.append(f"path must be non-empty, start at '{source}', and end at '{target}'")
    path_weight = 0.0
    if path_ok:
        for a, b in zip(path, path[1:]):
            if (a, b) not in edge_weight:
                path_ok = False
                path_errors.append(f"no edge from '{a}' to '{b}'")
                break
            path_weight += edge_weight[(a, b)]

    distance_matches_path = path_ok and abs(path_weight - distance) < 1e-6

    # Independent recomputation via Bellman-Ford.
    dist = {n: math.inf for n in nodes}
    dist[source] = 0.0
    for _ in range(len(nodes) - 1):
        changed = False
        for u, v, w in directed_edges:
            if dist[u] + w < dist[v] - 1e-12:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
    negative_cycle = any(dist[u] + w < dist[v] - 1e-9 for u, v, w in directed_edges)
    optimality_conditions_hold = not negative_cycle and all(
        dist[v] <= dist[u] + w + 1e-9 for u, v, w in directed_edges
    )
    independently_computed = dist[target]
    optimal = (
        not negative_cycle
        and independently_computed != math.inf
        and abs(independently_computed - distance) < 1e-6
    )

    valid = distance_matches_path and optimal and not path_errors
    return {
        "valid": valid,
        "path_is_real_walk": path_ok,
        "path_errors": path_errors,
        "path_weight": path_weight if path_ok else None,
        "claimed_distance": distance,
        "independently_computed_shortest_distance": (
            independently_computed if independently_computed != math.inf else None
        ),
        "optimality_conditions_hold": optimality_conditions_hold,
        "proof_method": "Bellman-Ford relaxation (a different algorithm than the Dijkstra's "
        "algorithm shortest_path uses), independently confirming the shortest-path optimality "
        "conditions rather than re-running the same code.",
    }


# ---------------------------------------------------------------------------
# Topological sort: Kahn's algorithm (solve) + direct-definition check (verify)
# ---------------------------------------------------------------------------


def _find_cycle(remaining: list, adj: dict) -> list | None:
    """DFS cycle extraction over the subgraph induced by `remaining` (nodes Kahn's
    algorithm never emitted, i.e. every node in or downstream of some cycle)."""
    remaining_set = set(remaining)
    color = {n: 0 for n in remaining}  # 0=unvisited, 1=in progress, 2=done
    path: list = []

    def dfs(u):
        color[u] = 1
        path.append(u)
        for v in adj[u]:
            if v not in remaining_set:
                continue
            if color[v] == 1:
                idx = path.index(v)
                return path[idx:] + [v]
            if color[v] == 0:
                found = dfs(v)
                if found:
                    return found
        path.pop()
        color[u] = 2
        return None

    for n in sorted(remaining):
        if color[n] == 0:
            found = dfs(n)
            if found:
                return found
    return None  # pragma: no cover -- unreachable if `remaining` truly contains a cycle


def topological_sort(nodes: list, edges: list) -> dict:
    """Find a topological order (every edge points forward) via Kahn's algorithm --
    repeatedly removing zero-in-degree nodes, breaking ties by node name for a
    deterministic result. If the graph isn't a DAG, returns is_dag: false with a
    concrete cycle (found via DFS over the leftover nodes) as proof, rather than just
    reporting 'cyclic'. Edges are always directed; 'weight' is ignored if present."""
    nodes = _validate_nodes(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=True)

    adj: dict[str, list[str]] = {n: [] for n in nodes}
    indegree = {n: 0 for n in nodes}
    for u, v, _w in parsed:
        adj[u].append(v)
        indegree[v] += 1

    heap = sorted(n for n in nodes if indegree[n] == 0)
    heapq.heapify(heap)
    indegree_work = dict(indegree)
    order = []
    while heap:
        u = heapq.heappop(heap)
        order.append(u)
        for v in adj[u]:
            indegree_work[v] -= 1
            if indegree_work[v] == 0:
                heapq.heappush(heap, v)

    if len(order) == len(nodes):
        verification = verify_topological_order(nodes, edges, order)
        if not verification["valid"]:
            raise AssertionError("internal error: solver's own order failed verification")  # pragma: no cover
        return {"is_dag": True, "order": order, "verification": verification}

    remaining = [n for n in nodes if n not in order]
    cycle = _find_cycle(remaining, adj)
    return {
        "is_dag": False,
        "reason": "a cycle exists, so no order can satisfy every edge -- proof: a concrete "
        "cycle is given below (found by exploring the nodes Kahn's algorithm could never "
        "reach zero in-degree for)",
        "nodes_not_orderable": sorted(remaining),
        "cycle": cycle,
    }


def verify_topological_order(nodes: list, edges: list, order: list) -> dict:
    """Independently check a claimed topological order against the direct definition:
    it's a permutation of nodes, and every edge (u, v) has position(u) < position(v).
    This never re-runs Kahn's algorithm -- it's the same "independent recheck via a
    different, simpler code path" this collection's other verifiers use."""
    nodes = _validate_nodes(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=True)
    if not isinstance(order, list) or not all(isinstance(o, str) for o in order):
        raise ValueError("order must be a list of node-name strings")

    if sorted(order) != sorted(nodes):
        return {
            "valid": False,
            "reason": "order is not a permutation of nodes",
            "missing": sorted(set(nodes) - set(order)),
            "unexpected": sorted(set(order) - set(nodes)),
        }

    position = {n: i for i, n in enumerate(order)}
    violations = [{"from": u, "to": v} for u, v, _w in parsed if position[u] >= position[v]]
    return {
        "valid": not violations,
        "violations": violations,
        "proof_method": "directly checks every edge (u, v) has position(u) < position(v) in "
        "the given order -- the definition of a valid topological order.",
    }


# ---------------------------------------------------------------------------
# Minimum spanning tree: Kruskal (solve) + cycle-property exchange argument (verify)
# ---------------------------------------------------------------------------


def minimum_spanning_tree(nodes: list, edges: list) -> dict:
    """Find a minimum spanning tree (or forest, if the graph is disconnected) via
    Kruskal's algorithm: sort all edges ascending by weight, add each one that connects
    two different components (union-find), skip it otherwise. Always undirected. Weight
    may be any real number (Kruskal doesn't require non-negative weights)."""
    nodes = _validate_nodes(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=True)
    sorted_edges = sorted(parsed, key=lambda e: (e[2], e[0], e[1]))

    uf = _UnionFind(nodes)
    tree_edges = []
    for u, v, w in sorted_edges:
        if uf.union(u, v):
            tree_edges.append({"from": u, "to": v, "weight": w})

    num_components = len({uf.find(n) for n in nodes})
    total_weight = sum(e["weight"] for e in tree_edges)
    result = {
        "tree_edges": tree_edges,
        "total_weight": total_weight,
        "num_components": num_components,
        "is_spanning_tree": num_components == 1,
    }
    if num_components > 1:
        result["reason"] = (
            f"the graph has {num_components} connected components -- this is a minimum "
            "spanning FOREST (one tree per component), not a single spanning tree, because "
            "no edge connects across components"
        )

    verification = verify_minimum_spanning_tree(nodes, edges, tree_edges)
    if not verification["valid"]:
        raise AssertionError("internal error: solver's own tree failed verification")  # pragma: no cover
    result["verification"] = verification
    return result


def verify_minimum_spanning_tree(nodes: list, edges: list, tree_edges: list) -> dict:
    """Independently check a claimed minimum spanning tree/forest: (1) every edge in it
    is real (present in the graph, with a matching weight), (2) it's acyclic, (3) it
    spans exactly the same connected components as the full graph, and (4, minimality)
    the cycle-property exchange argument: for every edge NOT in the tree that connects
    two nodes already in the same tree component, it isn't lighter than the heaviest
    edge on the tree path between them -- if it were, swapping it in would produce a
    lighter spanning forest, proving the given one isn't minimum. This is the standard
    mathematical proof of MST optimality, a different code path from Kruskal's own
    union-find search."""
    nodes = _validate_nodes(nodes)
    nodes_set = set(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=True)
    if not isinstance(tree_edges, list):
        raise ValueError("tree_edges must be a list of {from, to, weight} edges")

    tree_parsed = []
    for i, e in enumerate(tree_edges):
        if not isinstance(e, dict) or "from" not in e or "to" not in e or "weight" not in e:
            raise ValueError(f"tree_edges[{i}] must be an object with 'from', 'to', and 'weight'")
        u, v = e["from"], e["to"]
        _validate_node_ref(u, nodes_set, f"tree_edges[{i}].from")
        _validate_node_ref(v, nodes_set, f"tree_edges[{i}].to")
        if u == v:
            raise ValueError(f"tree_edges[{i}] is a self-loop ({u} -> {u}); not supported")
        tree_parsed.append((u, v, float(e["weight"])))

    available: dict[frozenset, list[float]] = defaultdict(list)
    for u, v, w in parsed:
        available[frozenset((u, v))].append(w)
    bad_edges = [
        {"from": u, "to": v, "weight": w}
        for u, v, w in tree_parsed
        if not any(abs(w - aw) < 1e-9 for aw in available.get(frozenset((u, v)), []))
    ]
    if bad_edges:
        return {
            "valid": False,
            "reason": "tree_edges references edges not present in the graph (or with a "
            "mismatched weight)",
            "bad_edges": bad_edges,
        }

    uf_tree = _UnionFind(nodes)
    for u, v, _w in tree_parsed:
        if not uf_tree.union(u, v):
            return {
                "valid": False,
                "reason": f"tree_edges contains a cycle through edge ('{u}', '{v}') -- not a forest",
            }

    uf_full = _UnionFind(nodes)
    for u, v, _w in parsed:
        uf_full.union(u, v)
    by_full_component: dict = defaultdict(set)
    for n in nodes:
        by_full_component[uf_full.find(n)].add(uf_tree.find(n))
    if any(len(group) > 1 for group in by_full_component.values()):
        return {
            "valid": False,
            "reason": "tree_edges does not span every connected component of the graph -- "
            "some component got split across more than one tree component",
        }

    tree_adj: dict[str, list[tuple[str, float]]] = {n: [] for n in nodes}
    tree_edge_set = set()
    for u, v, w in tree_parsed:
        tree_adj[u].append((v, w))
        tree_adj[v].append((u, w))
        tree_edge_set.add(frozenset((u, v)))

    def path_max_weight(u: str, v: str) -> float | None:
        parent: dict[str, str | None] = {u: None}
        parent_weight: dict[str, float] = {}
        queue = deque([u])
        while queue:
            cur = queue.popleft()
            if cur == v:
                break
            for nxt, w in tree_adj[cur]:
                if nxt not in parent:
                    parent[nxt] = cur
                    parent_weight[nxt] = w
                    queue.append(nxt)
        if v not in parent:
            return None
        max_w = float("-inf")
        cur = v
        while parent[cur] is not None:
            max_w = max(max_w, parent_weight[cur])
            cur = parent[cur]
        return max_w

    tree_component = {n: uf_tree.find(n) for n in nodes}
    violations = []
    for u, v, w in parsed:
        if frozenset((u, v)) in tree_edge_set or tree_component[u] != tree_component[v]:
            continue
        max_on_path = path_max_weight(u, v)
        if max_on_path is not None and w < max_on_path - 1e-9:
            violations.append(
                {
                    "non_tree_edge": {"from": u, "to": v, "weight": w},
                    "heaviest_edge_on_tree_path": max_on_path,
                    "explanation": "this non-tree edge is lighter than the heaviest edge on "
                    "the tree path it would close into a cycle -- swapping it in would "
                    "produce a lighter spanning forest, so tree_edges is NOT minimum",
                }
            )

    return {
        "valid": not violations,
        "violations": violations,
        "proof_method": "cycle-property exchange argument: for every edge outside the tree, "
        "checks it is not lighter than the heaviest edge on the tree path it would close "
        "into a cycle -- the standard mathematical proof of MST optimality.",
    }


# ---------------------------------------------------------------------------
# Max flow: Edmonds-Karp (solve) + conservation + min-cut theorem (verify)
# ---------------------------------------------------------------------------


def max_flow(nodes: list, edges: list, source: str, sink: str) -> dict:
    """Find the maximum flow from source to sink via Edmonds-Karp (repeated BFS
    shortest augmenting paths in the residual graph). Always returns a minimum cut
    alongside the flow: the set of nodes reachable from source in the final residual
    graph, and the original edges crossing out of it -- their total capacity equals the
    max flow value, which IS the proof of optimality (max-flow min-cut theorem), not a
    separate check. Directed; edges need 'capacity' (no default); duplicate (from, to)
    pairs are rejected."""
    nodes = _validate_nodes(nodes)
    nodes_set = set(nodes)
    parsed = _parse_flow_edges(edges, nodes)
    _validate_node_ref(source, nodes_set, "source")
    _validate_node_ref(sink, nodes_set, "sink")
    if source == sink:
        raise ValueError("source and sink must be different nodes")

    capacity: dict[tuple, float] = {}
    original_edges = set()
    for u, v, cap in parsed:
        capacity[(u, v)] = cap
        original_edges.add((u, v))

    adj: dict[str, set] = {n: set() for n in nodes}
    for u, v in list(capacity.keys()):
        adj[u].add(v)
        adj[v].add(u)
        capacity.setdefault((v, u), 0.0)

    residual = dict(capacity)
    flow_value = 0.0
    augmenting_paths = 0

    while True:
        parent: dict[str, str | None] = {source: None}
        queue = deque([source])
        while queue:
            u = queue.popleft()
            if u == sink:
                break
            for v in adj[u]:
                if v not in parent and residual.get((u, v), 0.0) > 1e-9:
                    parent[v] = u
                    queue.append(v)
        if sink not in parent:
            break
        path = []
        cur: str | None = sink
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()
        bottleneck = min(residual[(a, b)] for a, b in zip(path, path[1:]))
        for a, b in zip(path, path[1:]):
            residual[(a, b)] -= bottleneck
            residual[(b, a)] = residual.get((b, a), 0.0) + bottleneck
        flow_value += bottleneck
        augmenting_paths += 1

    reachable = {source}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if v not in reachable and residual.get((u, v), 0.0) > 1e-9:
                reachable.add(v)
                queue.append(v)

    cut_edges = [
        {"from": u, "to": v, "capacity": capacity[(u, v)]}
        for (u, v) in original_edges
        if u in reachable and v not in reachable
    ]
    cut_capacity = sum(e["capacity"] for e in cut_edges)

    flow_edges = []
    for u, v in original_edges:
        f = capacity[(u, v)] - residual[(u, v)]
        f = max(0.0, min(capacity[(u, v)], f))
        flow_edges.append({"from": u, "to": v, "flow": f, "capacity": capacity[(u, v)]})

    min_cut = {
        "reachable_from_source": sorted(reachable),
        "cut_edges": cut_edges,
        "cut_capacity": cut_capacity,
    }
    verification = verify_max_flow(nodes, edges, source, sink, flow_edges, cut=min_cut)
    if not verification["valid"] or not verification.get("optimality_proven"):
        raise AssertionError(  # pragma: no cover -- would indicate a solver bug
            "internal error: solver's own flow failed independent verification"
        )
    return {
        "max_flow": flow_value,
        "flow_edges": flow_edges,
        "augmenting_paths_found": augmenting_paths,
        "min_cut": min_cut,
        "verification": verification,
    }


def verify_max_flow(nodes: list, edges: list, source: str, sink: str, flow_edges: list, cut: dict | None = None) -> dict:
    """Independently check a claimed flow assignment: every edge's flow respects
    0 <= flow <= capacity, and flow is conserved at every node except source/sink
    (inflow == outflow). This alone only proves the flow is *feasible*, not maximum --
    pass `cut` (max_flow's own min_cut, or any cut you believe is tight) to additionally
    prove optimality via the max-flow min-cut theorem: any flow's value is always <= any
    cut's capacity, so a cut whose capacity equals this flow's value proves both are
    optimal, independently of how the flow was computed."""
    nodes = _validate_nodes(nodes)
    nodes_set = set(nodes)
    parsed = _parse_flow_edges(edges, nodes)
    _validate_node_ref(source, nodes_set, "source")
    _validate_node_ref(sink, nodes_set, "sink")
    capacity = {(u, v): cap for u, v, cap in parsed}

    if not isinstance(flow_edges, list):
        raise ValueError("flow_edges must be a list of {from, to, flow} entries")

    errors = []
    flow: dict[tuple, float] = {}
    for i, e in enumerate(flow_edges):
        if not isinstance(e, dict) or "from" not in e or "to" not in e or "flow" not in e:
            raise ValueError(f"flow_edges[{i}] must be an object with 'from', 'to', 'flow'")
        u, v, f = e["from"], e["to"], e["flow"]
        if (u, v) not in capacity:
            errors.append(f"flow_edges[{i}]: no such edge {u} -> {v} in the graph")
            continue
        if not isinstance(f, (int, float)) or isinstance(f, bool):
            errors.append(f"flow_edges[{i}]: flow must be a number")
            continue
        if f < -1e-9 or f > capacity[(u, v)] + 1e-9:
            errors.append(
                f"flow_edges[{i}]: flow {f} violates 0 <= flow <= capacity "
                f"({capacity[(u, v)]}) on edge {u} -> {v}"
            )
        flow[(u, v)] = f

    missing = [f"{u}->{v}" for (u, v) in capacity if (u, v) not in flow]
    if missing:
        errors.append(f"flow_edges is missing edge(s): {missing}")

    if errors:
        return {"valid": False, "errors": errors, "optimality_proven": False}

    net = {n: 0.0 for n in nodes}
    for (u, v), f in flow.items():
        net[u] -= f
        net[v] += f
    conservation_violations = [n for n in nodes if n not in (source, sink) and abs(net[n]) > 1e-6]

    flow_out_of_source = -net[source]
    flow_into_sink = net[sink]
    value_consistent = abs(flow_out_of_source - flow_into_sink) < 1e-6
    valid = not conservation_violations and value_consistent

    result = {
        "valid": valid,
        "conservation_violations": conservation_violations,
        "flow_value": flow_out_of_source if value_consistent else None,
        "source_outflow": flow_out_of_source,
        "sink_inflow": flow_into_sink,
        "optimality_proven": False,
    }

    if valid and cut is not None:
        if not isinstance(cut, dict) or "cut_edges" not in cut:
            raise ValueError("cut must be an object with 'cut_edges' to prove optimality")
        cut_capacity = 0.0
        for i, ce in enumerate(cut["cut_edges"]):
            u, v = ce.get("from"), ce.get("to")
            if (u, v) not in capacity:
                raise ValueError(f"cut['cut_edges'][{i}]: no such edge {u} -> {v} in the graph")
            cut_capacity += capacity[(u, v)]
        result["cut_capacity"] = cut_capacity
        result["optimality_proven"] = abs(cut_capacity - flow_out_of_source) < 1e-6
        result["proof_method"] = (
            "max-flow min-cut theorem: any flow's value is always <= any cut's capacity, so "
            "finding a cut whose capacity equals this flow's value proves BOTH the flow is "
            "maximum AND the cut is minimum, independently of how the flow was computed."
        )

    return result


# ---------------------------------------------------------------------------
# Random graph generator (seeded, reproducible)
# ---------------------------------------------------------------------------


def generate_random_graph(
    num_nodes: int,
    num_edges: int,
    seed: int | None = None,
    weighted: bool = True,
    directed: bool = False,
    min_weight: int = 1,
    max_weight: int = 10,
) -> dict:
    """Generate a random graph instance -- nodes named n1..nN and a random selection of
    `num_edges` distinct pairs -- ready to pass into any tool above. Uses a seeded
    stdlib random.Random (not secure-random's CSPRNG: this is reproducible instance
    generation, not a security context), so the same seed always returns the same
    graph. num_nodes must be 2..40; num_edges must fit within the number of distinct
    pairs available for that many nodes (directed or not)."""
    if not isinstance(num_nodes, int) or not (2 <= num_nodes <= 40):
        raise ValueError("num_nodes must be an int between 2 and 40")
    max_possible = num_nodes * (num_nodes - 1) if directed else num_nodes * (num_nodes - 1) // 2
    if not isinstance(num_edges, int) or not (0 <= num_edges <= max_possible):
        raise ValueError(
            f"num_edges must be an int between 0 and {max_possible} for {num_nodes} nodes "
            f"({'directed' if directed else 'undirected'})"
        )
    if min_weight > max_weight:
        raise ValueError("min_weight must be <= max_weight")

    rng = random.Random(seed)
    nodes = [f"n{i + 1}" for i in range(num_nodes)]
    possible_pairs = []
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i == j:
                continue
            if not directed and j < i:
                continue
            possible_pairs.append((nodes[i], nodes[j]))
    rng.shuffle(possible_pairs)
    chosen = possible_pairs[:num_edges]

    edges = []
    for u, v in chosen:
        edge = {"from": u, "to": v}
        if weighted:
            edge["weight"] = rng.randint(min_weight, max_weight)
        edges.append(edge)
    edges.sort(key=lambda e: (e["from"], e["to"]))

    return {"nodes": nodes, "edges": edges, "seed": seed, "directed": directed, "weighted": weighted}
