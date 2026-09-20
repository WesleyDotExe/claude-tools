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
- `graph_coloring` solves via backtracking search (DSATUR variable ordering
  -- always branch on the uncolored node with the most differently-colored
  neighbors -- plus forward checking, pruning a branch the instant some
  uncolored node's remaining color domain empties out), capped by a
  `max_search_nodes` budget the same way `strips-planner`'s BFS is capped by
  `max_states`/`max_depth`: exhausting the whole search tree without a
  colorable branch is a *proof* the graph isn't colorable with that many
  colors, while running out of budget first is inconclusive and raises
  rather than silently reporting "not colorable." `verify_coloring`
  independently checks a claimed coloring against the direct definition
  (every node has one color, no edge joins two same-colored nodes) -- no
  search at all, a different code path from the solver's. `chromatic_number`
  finds the *minimum* number of colors needed: it proves a lower bound by
  exhibiting a clique (any `L` pairwise-adjacent nodes each need a distinct
  color, so fewer than `L` colors can never work -- no search needed for
  that half), then searches `graph_coloring`-style upward from that bound,
  so every color count it rules out along the way is *proven* uncolorable
  by a fully exhausted search, not merely unfound.

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
            "graph_coloring / chromatic_number / verify_coloring": "Always undirected; "
            "'weight'/'capacity'/'directed' are all ignored -- only which pairs of nodes are "
            "adjacent matters. graph_coloring and chromatic_number always return color labels "
            "as integers 0..k-1; a 'coloring' you pass to verify_coloring may label colors "
            "with integers or strings, as long as it's consistent.",
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


# ---------------------------------------------------------------------------
# Graph coloring: DSATUR + forward-checking backtracking (solve) + direct
# definition check (verify) + clique-lower-bound search (chromatic number)
# ---------------------------------------------------------------------------


def _build_adjacency(nodes: list[str], edges: list) -> dict[str, set]:
    """Coloring only cares about adjacency -- always undirected, weight/capacity/
    directed are all ignored, and parallel edges collapse into one adjacency."""
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=True)
    adj: dict[str, set] = {n: set() for n in nodes}
    for u, v, _w in parsed:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _search_coloring(nodes: list[str], adj: dict, k: int, node_budget: int):
    """Backtracking search for a proper coloring using colors 0..k-1: DSATUR variable
    ordering (branch on the uncolored node with the most distinctly-colored neighbors,
    tie-broken by smallest remaining domain then highest degree) plus forward checking
    (tentatively coloring a node removes that color from its uncolored neighbors'
    domains; a domain emptying out prunes the branch immediately, before recursing).
    Returns (colorable, coloring_or_None, nodes_expanded, budget_exceeded)."""
    domains = {v: set(range(k)) for v in nodes}
    color: dict[str, int] = {}
    expanded = 0
    exceeded = False

    def select_var() -> str:
        uncolored = [v for v in nodes if v not in color]
        return min(
            uncolored,
            key=lambda v: (
                -len({color[u] for u in adj[v] if u in color}),
                len(domains[v]),
                -len(adj[v]),
            ),
        )

    def backtrack() -> bool:
        nonlocal expanded, exceeded
        expanded += 1
        if expanded > node_budget:
            exceeded = True
            return False
        if len(color) == len(nodes):
            return True
        v = select_var()
        for c in sorted(domains[v]):
            color[v] = c
            removed = []
            dead = False
            for u in adj[v]:
                if u in color:
                    continue
                if c in domains[u]:
                    domains[u].discard(c)
                    removed.append(u)
                    if not domains[u]:
                        dead = True
            if not dead and backtrack():
                return True
            for u in removed:
                domains[u].add(c)
            del color[v]
            if exceeded:
                return False
        return False

    ok = backtrack()
    return ok, (dict(color) if ok else None), expanded, exceeded


def _greedy_clique(nodes: list[str], adj: dict) -> list[str]:
    """A clique found greedily (highest-degree node first, then keep any node adjacent
    to every clique member so far). Not necessarily a MAXIMUM clique -- but any clique
    it finds, of any size L, is still a mathematically valid proof that the chromatic
    number is >= L (L pairwise-adjacent nodes each need a distinct color), which is all
    chromatic_number needs from it."""
    order = sorted(nodes, key=lambda n: (-len(adj[n]), n))
    clique: list[str] = []
    for v in order:
        if all(v in adj[u] for u in clique):
            clique.append(v)
    return clique


def _greedy_coloring(nodes: list[str], adj: dict) -> dict[str, int]:
    """Welsh-Powell greedy coloring (highest-degree node first, each node takes the
    smallest color its already-colored neighbors don't use) -- always produces *some*
    valid coloring, giving chromatic_number a guaranteed-reachable upper bound to search
    up to."""
    order = sorted(nodes, key=lambda n: (-len(adj[n]), n))
    color: dict[str, int] = {}
    for v in order:
        used = {color[u] for u in adj[v] if u in color}
        c = 0
        while c in used:
            c += 1
        color[v] = c
    return color


def verify_coloring(nodes: list, edges: list, coloring: dict) -> dict:
    """Independently check a claimed coloring (the solver's own, or a hand-written/
    model-proposed one) against the direct definition: every declared node has exactly
    one assigned color, and no edge joins two same-colored nodes. No search at all --
    a structurally different, much simpler code path than the backtracking solver."""
    nodes = _validate_nodes(nodes)
    nodes_set = set(nodes)
    parsed = _parse_weighted_edges(edges, nodes, allow_negative=True)
    if not isinstance(coloring, dict):
        raise ValueError("coloring must be an object mapping each node to a color")

    missing = sorted(nodes_set - set(coloring.keys()))
    unexpected = sorted(set(coloring.keys()) - nodes_set)
    if missing or unexpected:
        return {
            "valid": False,
            "reason": "coloring must assign exactly one color to every declared node, no more, no less",
            "missing_nodes": missing,
            "unexpected_nodes": unexpected,
        }
    for n in nodes:
        c = coloring[n]
        if not isinstance(c, (int, str)) or isinstance(c, bool):
            raise ValueError(f"coloring[{n!r}] must be an int or string color label, got {c!r}")

    violations = [
        {"from": u, "to": v, "shared_color": coloring[u]} for u, v, _w in parsed if coloring[u] == coloring[v]
    ]
    colors_used = sorted({coloring[n] for n in nodes}, key=str)
    return {
        "valid": not violations,
        "violations": violations,
        "num_colors_used": len(colors_used),
        "colors_used": colors_used,
        "proof_method": "directly checks every node has exactly one assigned color and no edge "
        "connects two same-colored nodes -- the definition of a proper coloring.",
    }


def graph_coloring(nodes: list, edges: list, num_colors: int, max_search_nodes: int = 200_000) -> dict:
    """Find a proper coloring using at most num_colors colors (labeled 0..num_colors-1)
    via backtracking search (DSATUR ordering + forward checking), capped by
    max_search_nodes. Always undirected; weight/capacity/directed are ignored -- only
    adjacency matters. If no coloring exists, the *entire* search tree was exhausted --
    that's a proof num_colors is too few, not an inconclusive result (an inconclusive
    result -- the search budget ran out first -- raises instead, distinguishing "proven
    impossible" from "couldn't tell"), the same contract strips-planner's solve() uses
    for state-space search."""
    nodes = _validate_nodes(nodes)
    if not isinstance(num_colors, int) or isinstance(num_colors, bool) or num_colors < 1:
        raise ValueError("num_colors must be an int >= 1")
    if not isinstance(max_search_nodes, int) or isinstance(max_search_nodes, bool) or max_search_nodes < 1:
        raise ValueError("max_search_nodes must be an int >= 1")
    adj = _build_adjacency(nodes, edges)

    colorable, coloring, expanded, exceeded = _search_coloring(nodes, adj, num_colors, max_search_nodes)
    if colorable:
        verification = verify_coloring(nodes, edges, coloring)
        if not verification["valid"]:
            raise AssertionError(  # pragma: no cover -- would indicate a solver bug
                "internal error: solver's own coloring failed independent verification"
            )
        return {
            "colorable": True,
            "coloring": coloring,
            "colors_used": sorted(set(coloring.values())),
            "search_nodes_expanded": expanded,
            "verification": verification,
        }

    if exceeded:
        raise ValueError(
            f"search exceeded max_search_nodes={max_search_nodes} without determining whether "
            f"the graph is colorable with {num_colors} colors; colorability could not be "
            "determined either way -- try raising max_search_nodes"
        )
    return {
        "colorable": False,
        "reason": f"the entire search tree was explored without finding a proper coloring using "
        f"{num_colors} colors -- proven impossible with this many colors, not just unfound within "
        "a search budget",
        "search_nodes_expanded": expanded,
    }


def chromatic_number(nodes: list, edges: list, max_search_nodes: int = 200_000) -> dict:
    """Find the chromatic number: the minimum number of colors a proper coloring needs.
    Always undirected; weight/capacity/directed are ignored. Proceeds in two stages: (1)
    a greedy clique gives a lower bound L for free (L pairwise-adjacent nodes each need a
    distinct color -- no search required for that half of the proof), and a greedy
    (Welsh-Powell) coloring gives a guaranteed-reachable upper bound G; (2) backtracking
    search (the same DSATUR + forward-checking solver graph_coloring uses) tries k = L,
    L+1, ... up to G, so the chromatic number is the first colorable k, and every k it
    ruled out along the way was proven uncolorable by a fully exhausted search, not
    merely unfound. max_search_nodes is a single TOTAL budget shared across every k
    tried; running out before a k resolves raises (inconclusive), the same contract
    graph_coloring itself uses."""
    nodes = _validate_nodes(nodes)
    if not isinstance(max_search_nodes, int) or isinstance(max_search_nodes, bool) or max_search_nodes < 1:
        raise ValueError("max_search_nodes must be an int >= 1")
    adj = _build_adjacency(nodes, edges)

    clique = _greedy_clique(nodes, adj)
    lower_bound = len(clique)
    upper_bound = len(set(_greedy_coloring(nodes, adj).values()))

    proven_uncolorable = []
    remaining_budget = max_search_nodes
    total_expanded = 0
    chromatic = None
    result_coloring = None
    for k in range(lower_bound, upper_bound + 1):
        colorable, coloring, expanded, exceeded = _search_coloring(nodes, adj, k, remaining_budget)
        total_expanded += expanded
        remaining_budget -= expanded
        if colorable:
            chromatic = k
            result_coloring = coloring
            break
        if exceeded:
            raise ValueError(
                f"search exceeded max_search_nodes={max_search_nodes} (a single total budget "
                f"shared across every color count tried) while trying k={k} colors; the "
                "chromatic number could not be determined -- try raising max_search_nodes"
            )
        proven_uncolorable.append(k)

    if chromatic is None:  # pragma: no cover -- guaranteed unreachable: k == upper_bound is
        # always colorable by construction (it's exactly how many colors the greedy coloring
        # used), so the loop above always finds a colorable k at or before upper_bound.
        raise AssertionError("internal error: greedy upper bound was not itself colorable")

    verification = verify_coloring(nodes, edges, result_coloring)
    if not verification["valid"]:
        raise AssertionError(  # pragma: no cover -- would indicate a solver bug
            "internal error: solver's own coloring failed independent verification"
        )

    if proven_uncolorable:
        proof_method = (
            f"lower bound {lower_bound} is proven by lower_bound_clique ({lower_bound} pairwise-"
            f"adjacent nodes each need a distinct color); k={proven_uncolorable} were each then "
            "proven uncolorable by exhausting the entire backtracking search tree (not a budget "
            f"cutoff) before k={chromatic} was found colorable."
        )
    else:
        proof_method = (
            f"lower bound {lower_bound} is proven by lower_bound_clique ({lower_bound} pairwise-"
            f"adjacent nodes each need a distinct color), and a coloring using exactly that many "
            "colors was found immediately -- no exhaustive search was needed for any smaller k."
        )

    return {
        "chromatic_number": chromatic,
        "coloring": result_coloring,
        "colors_used": sorted(set(result_coloring.values())),
        "lower_bound": lower_bound,
        "lower_bound_clique": clique,
        "upper_bound_greedy": upper_bound,
        "k_values_proven_uncolorable": proven_uncolorable,
        "search_nodes_expanded_total": total_expanded,
        "proof_method": proof_method,
        "verification": verification,
    }
