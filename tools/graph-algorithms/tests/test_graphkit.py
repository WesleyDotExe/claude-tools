import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import graphkit


class DescribeFormatTests(unittest.TestCase):
    def test_returns_worked_example(self):
        desc = graphkit.describe_graph_format()
        self.assertIn("example_graph", desc)
        ex = desc["example_graph"]
        # The example should be internally consistent: usable as a real graph.
        result = graphkit.shortest_path(ex["nodes"], ex["edges"], "A", "D", directed=True)
        self.assertTrue(result["reachable"])


# A small directed weighted graph with a known-by-hand shortest path.
#   A --6--> B          A --3--> C --2--> B --1--> D --2--> E
#            B --1--> D                        B --6--> E
DIRECTED_NODES = ["A", "B", "C", "D", "E"]
DIRECTED_EDGES = [
    {"from": "A", "to": "B", "weight": 6},
    {"from": "A", "to": "C", "weight": 3},
    {"from": "C", "to": "B", "weight": 2},
    {"from": "B", "to": "D", "weight": 1},
    {"from": "C", "to": "D", "weight": 5},
    {"from": "D", "to": "E", "weight": 2},
    {"from": "B", "to": "E", "weight": 6},
]


class ShortestPathTests(unittest.TestCase):
    def test_known_shortest_path(self):
        result = graphkit.shortest_path(DIRECTED_NODES, DIRECTED_EDGES, "A", "E", directed=True)
        self.assertTrue(result["reachable"])
        self.assertEqual(result["path"], ["A", "C", "B", "D", "E"])
        self.assertAlmostEqual(result["distance"], 8.0)
        self.assertTrue(result["verification"]["valid"])
        self.assertTrue(result["verification"]["optimality_conditions_hold"])

    def test_unweighted_defaults_to_bfs_shortest_hop_count(self):
        nodes = ["X", "Y", "Z"]
        edges = [{"from": "X", "to": "Y"}, {"from": "Y", "to": "Z"}, {"from": "X", "to": "Z"}]
        result = graphkit.shortest_path(nodes, edges, "X", "Z", directed=False)
        self.assertEqual(result["path"], ["X", "Z"])
        self.assertAlmostEqual(result["distance"], 1.0)

    def test_directed_edge_cannot_be_used_backwards(self):
        nodes = ["A", "B"]
        edges = [{"from": "A", "to": "B", "weight": 1}]
        result = graphkit.shortest_path(nodes, edges, "B", "A", directed=True)
        self.assertFalse(result["reachable"])
        self.assertIn("reason", result)

    def test_undirected_allows_backwards_traversal(self):
        nodes = ["A", "B"]
        edges = [{"from": "A", "to": "B", "weight": 1}]
        result = graphkit.shortest_path(nodes, edges, "B", "A", directed=False)
        self.assertTrue(result["reachable"])
        self.assertAlmostEqual(result["distance"], 1.0)

    def test_unreachable_target_gives_proof_not_guess(self):
        nodes = ["A", "B", "C"]
        edges = [{"from": "A", "to": "B", "weight": 1}]
        result = graphkit.shortest_path(nodes, edges, "A", "C", directed=True)
        self.assertFalse(result["reachable"])
        self.assertEqual(result["nodes_expanded"], 2)  # A, then B; C never reached

    def test_negative_weight_rejected(self):
        nodes = ["A", "B"]
        edges = [{"from": "A", "to": "B", "weight": -1}]
        with self.assertRaises(ValueError):
            graphkit.shortest_path(nodes, edges, "A", "B")

    def test_verify_catches_wrong_distance_claim(self):
        v = graphkit.verify_shortest_path(
            DIRECTED_NODES, DIRECTED_EDGES, "A", "E", ["A", "C", "B", "D", "E"], 7.0, directed=True
        )
        self.assertFalse(v["valid"])
        self.assertEqual(v["independently_computed_shortest_distance"], 8.0)

    def test_verify_catches_nonexistent_edge_in_path(self):
        v = graphkit.verify_shortest_path(DIRECTED_NODES, DIRECTED_EDGES, "A", "E", ["A", "D", "E"], 4.0, directed=True)
        self.assertFalse(v["valid"])
        self.assertFalse(v["path_is_real_walk"])

    def test_verify_catches_path_not_ending_at_target(self):
        v = graphkit.verify_shortest_path(DIRECTED_NODES, DIRECTED_EDGES, "A", "E", ["A", "C"], 3.0, directed=True)
        self.assertFalse(v["valid"])

    def test_verify_accepts_correct_standalone_claim(self):
        v = graphkit.verify_shortest_path(DIRECTED_NODES, DIRECTED_EDGES, "A", "E", ["A", "C", "B", "D", "E"], 8.0)
        self.assertTrue(v["valid"])

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.shortest_path(DIRECTED_NODES, DIRECTED_EDGES, "Z", "A")


DAG_NODES = ["A", "B", "C", "D"]
DAG_EDGES = [
    {"from": "A", "to": "B"},
    {"from": "A", "to": "C"},
    {"from": "B", "to": "D"},
    {"from": "C", "to": "D"},
]

CYCLE_NODES = ["A", "B", "C"]
CYCLE_EDGES = [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}, {"from": "C", "to": "A"}]


class TopologicalSortTests(unittest.TestCase):
    def test_known_order_on_diamond_dag(self):
        result = graphkit.topological_sort(DAG_NODES, DAG_EDGES)
        self.assertTrue(result["is_dag"])
        self.assertEqual(result["order"], ["A", "B", "C", "D"])
        self.assertTrue(result["verification"]["valid"])

    def test_cycle_detected_with_concrete_witness(self):
        result = graphkit.topological_sort(CYCLE_NODES, CYCLE_EDGES)
        self.assertFalse(result["is_dag"])
        self.assertEqual(sorted(result["nodes_not_orderable"]), ["A", "B", "C"])
        cycle = result["cycle"]
        self.assertEqual(cycle[0], cycle[-1])
        edge_set = {(e["from"], e["to"]) for e in CYCLE_EDGES}
        for a, b in zip(cycle, cycle[1:]):
            self.assertIn((a, b), edge_set)

    def test_partial_cycle_still_orders_the_acyclic_part(self):
        # A -> B -> C -> B is a cycle among B, C; A is not part of it and has no
        # incoming edges, so Kahn's algorithm should still order A but never B or C.
        nodes = ["A", "B", "C"]
        edges = [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}, {"from": "C", "to": "B"}]
        result = graphkit.topological_sort(nodes, edges)
        self.assertFalse(result["is_dag"])
        self.assertEqual(sorted(result["nodes_not_orderable"]), ["B", "C"])

    def test_verify_catches_backwards_edge(self):
        v = graphkit.verify_topological_order(DAG_NODES, DAG_EDGES, ["B", "A", "C", "D"])
        self.assertFalse(v["valid"])
        self.assertIn({"from": "A", "to": "B"}, v["violations"])

    def test_verify_catches_non_permutation(self):
        v = graphkit.verify_topological_order(DAG_NODES, DAG_EDGES, ["A", "B", "C"])
        self.assertFalse(v["valid"])
        self.assertEqual(v["missing"], ["D"])

    def test_verify_accepts_valid_order(self):
        v = graphkit.verify_topological_order(DAG_NODES, DAG_EDGES, ["A", "C", "B", "D"])
        self.assertTrue(v["valid"])


# Classic small MST example: sorted edges by weight are AB(1), BC(2), CD(3), AC(4), AD(10);
# Kruskal takes AB, BC, CD (total 6) and skips AC, AD (both would close a cycle).
MST_NODES = ["A", "B", "C", "D"]
MST_EDGES = [
    {"from": "A", "to": "B", "weight": 1},
    {"from": "B", "to": "C", "weight": 2},
    {"from": "C", "to": "D", "weight": 3},
    {"from": "A", "to": "D", "weight": 10},
    {"from": "A", "to": "C", "weight": 4},
]


class MinimumSpanningTreeTests(unittest.TestCase):
    def test_known_minimum_weight(self):
        result = graphkit.minimum_spanning_tree(MST_NODES, MST_EDGES)
        self.assertTrue(result["is_spanning_tree"])
        self.assertAlmostEqual(result["total_weight"], 6.0)
        self.assertEqual(len(result["tree_edges"]), 3)
        self.assertTrue(result["verification"]["valid"])

    def test_disconnected_graph_returns_forest(self):
        nodes = ["A", "B", "C", "D"]
        edges = [{"from": "A", "to": "B", "weight": 1}, {"from": "C", "to": "D", "weight": 2}]
        result = graphkit.minimum_spanning_tree(nodes, edges)
        self.assertFalse(result["is_spanning_tree"])
        self.assertEqual(result["num_components"], 2)
        self.assertAlmostEqual(result["total_weight"], 3.0)

    def test_verify_catches_suboptimal_tree_via_cycle_property(self):
        # Swap the true MST's C-D(3) edge for the far heavier A-D(10) edge -- still
        # spans every node, but is provably not minimum.
        bad_tree = [
            {"from": "A", "to": "B", "weight": 1},
            {"from": "B", "to": "C", "weight": 2},
            {"from": "A", "to": "D", "weight": 10},
        ]
        v = graphkit.verify_minimum_spanning_tree(MST_NODES, MST_EDGES, bad_tree)
        self.assertFalse(v["valid"])
        self.assertTrue(v["violations"])
        self.assertEqual(v["violations"][0]["non_tree_edge"], {"from": "C", "to": "D", "weight": 3.0})

    def test_verify_catches_edge_not_in_graph(self):
        bad_tree = [{"from": "A", "to": "B", "weight": 999}]
        v = graphkit.verify_minimum_spanning_tree(MST_NODES, MST_EDGES, bad_tree)
        self.assertFalse(v["valid"])
        self.assertIn("bad_edges", v)

    def test_verify_catches_cycle_in_claimed_tree(self):
        bad_tree = [
            {"from": "A", "to": "B", "weight": 1},
            {"from": "B", "to": "C", "weight": 2},
            {"from": "A", "to": "C", "weight": 4},
        ]
        v = graphkit.verify_minimum_spanning_tree(MST_NODES, MST_EDGES, bad_tree)
        self.assertFalse(v["valid"])

    def test_verify_catches_incomplete_spanning(self):
        bad_tree = [{"from": "A", "to": "B", "weight": 1}]
        v = graphkit.verify_minimum_spanning_tree(MST_NODES, MST_EDGES, bad_tree)
        self.assertFalse(v["valid"])

    def test_negative_weight_allowed(self):
        nodes = ["A", "B", "C"]
        edges = [{"from": "A", "to": "B", "weight": -5}, {"from": "B", "to": "C", "weight": 1}]
        result = graphkit.minimum_spanning_tree(nodes, edges)
        self.assertAlmostEqual(result["total_weight"], -4.0)


# Classic textbook flow network, max flow S->T is 5.
FLOW_NODES = ["S", "A", "B", "T"]
FLOW_EDGES = [
    {"from": "S", "to": "A", "capacity": 3},
    {"from": "S", "to": "B", "capacity": 2},
    {"from": "A", "to": "B", "capacity": 1},
    {"from": "A", "to": "T", "capacity": 2},
    {"from": "B", "to": "T", "capacity": 4},
]


class MaxFlowTests(unittest.TestCase):
    def test_known_max_flow_value(self):
        result = graphkit.max_flow(FLOW_NODES, FLOW_EDGES, "S", "T")
        self.assertAlmostEqual(result["max_flow"], 5.0)
        self.assertAlmostEqual(result["min_cut"]["cut_capacity"], 5.0)
        self.assertTrue(result["verification"]["valid"])
        self.assertTrue(result["verification"]["optimality_proven"])

    def test_flow_respects_conservation_and_capacity(self):
        result = graphkit.max_flow(FLOW_NODES, FLOW_EDGES, "S", "T")
        by_edge = {(e["from"], e["to"]): e for e in result["flow_edges"]}
        for e in FLOW_EDGES:
            key = (e["from"], e["to"])
            self.assertGreaterEqual(by_edge[key]["flow"], -1e-9)
            self.assertLessEqual(by_edge[key]["flow"], e["capacity"] + 1e-9)
        net = {n: 0.0 for n in FLOW_NODES}
        for (u, v), e in by_edge.items():
            net[u] -= e["flow"]
            net[v] += e["flow"]
        for n in ("A", "B"):
            self.assertAlmostEqual(net[n], 0.0)

    def test_verify_catches_capacity_violation(self):
        flow_edges = [
            {"from": "S", "to": "A", "flow": 999},
            {"from": "S", "to": "B", "flow": 2},
            {"from": "A", "to": "B", "flow": 0},
            {"from": "A", "to": "T", "flow": 2},
            {"from": "B", "to": "T", "flow": 2},
        ]
        v = graphkit.verify_max_flow(FLOW_NODES, FLOW_EDGES, "S", "T", flow_edges)
        self.assertFalse(v["valid"])
        self.assertTrue(v["errors"])

    def test_verify_catches_conservation_violation(self):
        flow_edges = [
            {"from": "S", "to": "A", "flow": 3},
            {"from": "S", "to": "B", "flow": 2},
            {"from": "A", "to": "B", "flow": 0},
            {"from": "A", "to": "T", "flow": 1},  # should be 3 to conserve at A
            {"from": "B", "to": "T", "flow": 2},
        ]
        v = graphkit.verify_max_flow(FLOW_NODES, FLOW_EDGES, "S", "T", flow_edges)
        self.assertFalse(v["valid"])
        self.assertIn("A", v["conservation_violations"])

    def test_verify_without_cut_only_proves_feasibility(self):
        # A feasible but non-maximum flow (send only 3 total) -- valid as a flow, but
        # optimality is never claimed without a matching cut.
        flow_edges = [
            {"from": "S", "to": "A", "flow": 1},
            {"from": "S", "to": "B", "flow": 2},
            {"from": "A", "to": "B", "flow": 0},
            {"from": "A", "to": "T", "flow": 1},
            {"from": "B", "to": "T", "flow": 2},
        ]
        v = graphkit.verify_max_flow(FLOW_NODES, FLOW_EDGES, "S", "T", flow_edges)
        self.assertTrue(v["valid"])
        self.assertFalse(v["optimality_proven"])

    def test_verify_rejects_mismatched_cut_as_non_optimal(self):
        result = graphkit.max_flow(FLOW_NODES, FLOW_EDGES, "S", "T")
        # A cut whose capacity (2+4=6) doesn't equal the flow value (5) must not be
        # accepted as an optimality proof, even though the flow itself is feasible.
        mismatched_cut = {"cut_edges": [{"from": "A", "to": "T", "capacity": 2}, {"from": "B", "to": "T", "capacity": 4}]}
        v = graphkit.verify_max_flow(FLOW_NODES, FLOW_EDGES, "S", "T", result["flow_edges"], cut=mismatched_cut)
        self.assertTrue(v["valid"])
        self.assertFalse(v["optimality_proven"])
        self.assertAlmostEqual(v["cut_capacity"], 6.0)

    def test_duplicate_edge_rejected(self):
        edges = FLOW_EDGES + [{"from": "S", "to": "A", "capacity": 1}]
        with self.assertRaises(ValueError):
            graphkit.max_flow(FLOW_NODES, edges, "S", "T")

    def test_missing_capacity_rejected(self):
        edges = [{"from": "S", "to": "T"}]
        with self.assertRaises(ValueError):
            graphkit.max_flow(["S", "T"], edges, "S", "T")

    def test_source_equals_sink_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.max_flow(FLOW_NODES, FLOW_EDGES, "S", "S")


class GenerateRandomGraphTests(unittest.TestCase):
    def test_reproducible_with_same_seed(self):
        g1 = graphkit.generate_random_graph(6, 8, seed=42)
        g2 = graphkit.generate_random_graph(6, 8, seed=42)
        self.assertEqual(g1, g2)

    def test_different_seed_usually_differs(self):
        g1 = graphkit.generate_random_graph(8, 10, seed=1)
        g2 = graphkit.generate_random_graph(8, 10, seed=2)
        self.assertNotEqual(g1["edges"], g2["edges"])

    def test_generated_graph_feeds_mst_and_shortest_path(self):
        g = graphkit.generate_random_graph(6, 10, seed=7, directed=False)
        mst = graphkit.minimum_spanning_tree(g["nodes"], g["edges"])
        self.assertTrue(mst["verification"]["valid"])
        sp = graphkit.shortest_path(g["nodes"], g["edges"], g["nodes"][0], g["nodes"][-1], directed=False)
        self.assertIn("reachable", sp)

    def test_num_nodes_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.generate_random_graph(1, 0)

    def test_num_edges_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.generate_random_graph(3, 100)


class GraphColoringTests(unittest.TestCase):
    # A triangle (K3): every pair of nodes is adjacent, so it needs exactly 3 colors.
    TRIANGLE_NODES = ["A", "B", "C"]
    TRIANGLE_EDGES = [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}, {"from": "A", "to": "C"}]

    # An even cycle (bipartite): 2 colors suffice.
    SQUARE_NODES = ["A", "B", "C", "D"]
    SQUARE_EDGES = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
    ]

    # An odd cycle (C5): triangle-free (max clique = 2) but needs 3 colors -- the
    # standard example where the clique lower bound alone doesn't already prove the
    # chromatic number, so an exhaustive search is genuinely needed at k=2.
    PENTAGON_NODES = ["A", "B", "C", "D", "E"]
    PENTAGON_EDGES = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "E"},
        {"from": "E", "to": "A"},
    ]

    def test_triangle_colorable_with_three_not_two(self):
        ok = graphkit.graph_coloring(self.TRIANGLE_NODES, self.TRIANGLE_EDGES, num_colors=3)
        self.assertTrue(ok["colorable"])
        self.assertEqual(len(ok["colors_used"]), 3)
        self.assertTrue(ok["verification"]["valid"])

        bad = graphkit.graph_coloring(self.TRIANGLE_NODES, self.TRIANGLE_EDGES, num_colors=2)
        self.assertFalse(bad["colorable"])
        self.assertIn("reason", bad)

    def test_square_colorable_with_two(self):
        result = graphkit.graph_coloring(self.SQUARE_NODES, self.SQUARE_EDGES, num_colors=2)
        self.assertTrue(result["colorable"])
        self.assertEqual(set(result["coloring"].keys()), set(self.SQUARE_NODES))
        self.assertLessEqual(len(result["colors_used"]), 2)

    def test_num_colors_directed_and_weight_ignored(self):
        # Same square, but with 'directed'-shaped weighted edges -- coloring only cares
        # about adjacency, so this must behave identically to the unweighted version.
        weighted = [dict(e, weight=7) for e in self.SQUARE_EDGES]
        result = graphkit.graph_coloring(self.SQUARE_NODES, weighted, num_colors=2)
        self.assertTrue(result["colorable"])

    def test_budget_exceeded_raises_instead_of_guessing(self):
        with self.assertRaises(ValueError):
            graphkit.graph_coloring(self.TRIANGLE_NODES, self.TRIANGLE_EDGES, num_colors=2, max_search_nodes=1)

    def test_num_colors_validation(self):
        with self.assertRaises(ValueError):
            graphkit.graph_coloring(self.SQUARE_NODES, self.SQUARE_EDGES, num_colors=0)
        with self.assertRaises(ValueError):
            graphkit.graph_coloring(self.SQUARE_NODES, self.SQUARE_EDGES, num_colors=True)  # bool, not int
        with self.assertRaises(ValueError):
            graphkit.graph_coloring(self.SQUARE_NODES, self.SQUARE_EDGES, num_colors=2, max_search_nodes=0)


class VerifyColoringTests(unittest.TestCase):
    def test_valid_coloring_accepted(self):
        v = graphkit.verify_coloring(
            GraphColoringTests.TRIANGLE_NODES, GraphColoringTests.TRIANGLE_EDGES, {"A": 0, "B": 1, "C": 2}
        )
        self.assertTrue(v["valid"])
        self.assertEqual(v["num_colors_used"], 3)

    def test_catches_shared_color_on_adjacent_nodes(self):
        v = graphkit.verify_coloring(
            GraphColoringTests.TRIANGLE_NODES, GraphColoringTests.TRIANGLE_EDGES, {"A": 0, "B": 1, "C": 1}
        )
        self.assertFalse(v["valid"])
        self.assertEqual(len(v["violations"]), 1)
        self.assertEqual(v["violations"][0]["shared_color"], 1)

    def test_catches_missing_node(self):
        v = graphkit.verify_coloring(GraphColoringTests.TRIANGLE_NODES, GraphColoringTests.TRIANGLE_EDGES, {"A": 0, "B": 1})
        self.assertFalse(v["valid"])
        self.assertEqual(v["missing_nodes"], ["C"])

    def test_catches_unexpected_node(self):
        v = graphkit.verify_coloring(
            GraphColoringTests.TRIANGLE_NODES, GraphColoringTests.TRIANGLE_EDGES, {"A": 0, "B": 1, "C": 2, "Z": 0}
        )
        self.assertFalse(v["valid"])
        self.assertEqual(v["unexpected_nodes"], ["Z"])

    def test_string_color_labels_allowed(self):
        v = graphkit.verify_coloring(
            GraphColoringTests.SQUARE_NODES, GraphColoringTests.SQUARE_EDGES, {"A": "red", "B": "blue", "C": "red", "D": "blue"}
        )
        self.assertTrue(v["valid"])

    def test_bad_color_type_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.verify_coloring(
                GraphColoringTests.TRIANGLE_NODES, GraphColoringTests.TRIANGLE_EDGES, {"A": 0, "B": 1, "C": [1, 2]}
            )


class ChromaticNumberTests(unittest.TestCase):
    def test_triangle_chromatic_number_three_proven_by_clique_alone(self):
        result = graphkit.chromatic_number(GraphColoringTests.TRIANGLE_NODES, GraphColoringTests.TRIANGLE_EDGES)
        self.assertEqual(result["chromatic_number"], 3)
        self.assertEqual(result["lower_bound"], 3)
        self.assertEqual(len(result["lower_bound_clique"]), 3)
        # The clique lower bound already equals the answer -- no exhaustive search needed.
        self.assertEqual(result["k_values_proven_uncolorable"], [])
        self.assertTrue(result["verification"]["valid"])

    def test_square_chromatic_number_two(self):
        result = graphkit.chromatic_number(GraphColoringTests.SQUARE_NODES, GraphColoringTests.SQUARE_EDGES)
        self.assertEqual(result["chromatic_number"], 2)
        self.assertEqual(result["k_values_proven_uncolorable"], [])

    def test_pentagon_chromatic_number_three_needs_real_search(self):
        result = graphkit.chromatic_number(GraphColoringTests.PENTAGON_NODES, GraphColoringTests.PENTAGON_EDGES)
        self.assertEqual(result["chromatic_number"], 3)
        # Triangle-free, so the clique lower bound is only 2 -- k=2 must be exhaustively
        # ruled out by real search before k=3 is found colorable.
        self.assertEqual(result["lower_bound"], 2)
        self.assertEqual(result["k_values_proven_uncolorable"], [2])
        self.assertTrue(result["verification"]["valid"])
        self.assertGreater(result["search_nodes_expanded_total"], 0)

    def test_single_node_no_edges_chromatic_number_one(self):
        result = graphkit.chromatic_number(["A"], [])
        self.assertEqual(result["chromatic_number"], 1)

    def test_budget_exceeded_raises(self):
        with self.assertRaises(ValueError):
            graphkit.chromatic_number(GraphColoringTests.PENTAGON_NODES, GraphColoringTests.PENTAGON_EDGES, max_search_nodes=1)

    def test_generated_graph_coloring_is_self_consistent(self):
        g = graphkit.generate_random_graph(8, 12, seed=3, directed=False)
        result = graphkit.chromatic_number(g["nodes"], g["edges"], max_search_nodes=500_000)
        self.assertTrue(result["verification"]["valid"])
        # A coloring with fewer colors than the proven chromatic number cannot exist.
        too_few = graphkit.graph_coloring(g["nodes"], g["edges"], num_colors=result["chromatic_number"] - 1)
        self.assertFalse(too_few["colorable"])


class ValidationTests(unittest.TestCase):
    def test_duplicate_nodes_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.shortest_path(["A", "A"], [], "A", "A")

    def test_empty_nodes_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.shortest_path([], [], "A", "A")

    def test_self_loop_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.shortest_path(["A"], [{"from": "A", "to": "A", "weight": 1}], "A", "A")

    def test_unknown_edge_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.shortest_path(["A", "B"], [{"from": "A", "to": "Z", "weight": 1}], "A", "B")

    def test_non_number_weight_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.shortest_path(["A", "B"], [{"from": "A", "to": "B", "weight": "far"}], "A", "B")


# ---------------------------------------------------------------------------
# Maximum bipartite matching
# ---------------------------------------------------------------------------


class BipartiteFormatTests(unittest.TestCase):
    def test_bipartite_example_is_usable(self):
        desc = graphkit.describe_graph_format()
        bip = desc["bipartite_format"]
        ex = bip["example_bipartite_graph"]
        result = graphkit.maximum_bipartite_matching(ex["left_nodes"], ex["right_nodes"], ex["edges"])
        self.assertTrue(result["verification"]["is_maximum"])

    def test_describe_bipartite_format_standalone(self):
        bip = graphkit.describe_bipartite_format()
        self.assertIn("example_bipartite_graph", bip)


class MaximumBipartiteMatchingTests(unittest.TestCase):
    def test_known_maximum_matching_is_not_perfect(self):
        # a-x, b-x, b-y, c-y: max matching size is 2 (e.g. a-x, b-y, or a-x, c-y), not 3
        # (only two right nodes exist), and 'c' or 'a' is necessarily left unmatched.
        left = ["a", "b", "c"]
        right = ["x", "y"]
        edges = [
            {"from": "a", "to": "x"},
            {"from": "b", "to": "x"},
            {"from": "b", "to": "y"},
            {"from": "c", "to": "y"},
        ]
        result = graphkit.maximum_bipartite_matching(left, right, edges)
        self.assertEqual(result["matching_size"], 2)
        self.assertTrue(result["verification"]["is_maximum"])
        self.assertEqual(len(result["unmatched_left"]), 1)
        self.assertEqual(result["unmatched_right"], [])

    def test_perfect_matching_found_when_one_exists(self):
        left = ["w1", "w2", "w3"]
        right = ["t1", "t2", "t3"]
        edges = [
            {"from": "w1", "to": "t1"},
            {"from": "w1", "to": "t2"},
            {"from": "w2", "to": "t2"},
            {"from": "w2", "to": "t3"},
            {"from": "w3", "to": "t3"},
            {"from": "w3", "to": "t1"},
        ]
        result = graphkit.maximum_bipartite_matching(left, right, edges)
        self.assertEqual(result["matching_size"], 3)
        self.assertEqual(result["unmatched_left"], [])
        self.assertEqual(result["unmatched_right"], [])

    def test_no_edges_gives_empty_matching(self):
        result = graphkit.maximum_bipartite_matching(["a"], ["x"], [])
        self.assertEqual(result["matching_size"], 0)
        self.assertTrue(result["verification"]["is_maximum"])

    def test_weight_field_is_ignored(self):
        left, right = ["a"], ["x"]
        edges = [{"from": "a", "to": "x", "weight": -999}]
        result = graphkit.maximum_bipartite_matching(left, right, edges)
        self.assertEqual(result["matching_size"], 1)


class VerifyBipartiteMatchingTests(unittest.TestCase):
    LEFT = ["a", "b", "c"]
    RIGHT = ["x", "y"]
    EDGES = [
        {"from": "a", "to": "x"},
        {"from": "b", "to": "x"},
        {"from": "b", "to": "y"},
        {"from": "c", "to": "y"},
    ]

    def test_accepts_solvers_own_matching(self):
        solved = graphkit.maximum_bipartite_matching(self.LEFT, self.RIGHT, self.EDGES)
        v = graphkit.verify_bipartite_matching(self.LEFT, self.RIGHT, self.EDGES, solved["matching"])
        self.assertTrue(v["valid"])
        self.assertTrue(v["is_maximum"])

    def test_catches_non_maximum_matching_with_augmenting_path(self):
        # only 'a-x' matched: 'a' and 'x' are used, but b-y (or c-y) is still available,
        # and in fact b is free, y is free via c -- an augmenting path exists.
        v = graphkit.verify_bipartite_matching(self.LEFT, self.RIGHT, self.EDGES, [{"left": "a", "right": "x"}])
        self.assertTrue(v["valid"])
        self.assertFalse(v["is_maximum"])
        self.assertIn("augmenting_path", v)
        # the witness path must alternate real edges and end on a free right node.
        path = v["augmenting_path"]
        self.assertEqual(path[0], "b")  # only free left node
        self.assertIn(path[-1], {"x", "y"})

    def test_catches_left_node_reused(self):
        v = graphkit.verify_bipartite_matching(
            self.LEFT, self.RIGHT, self.EDGES, [{"left": "b", "right": "x"}, {"left": "b", "right": "y"}]
        )
        self.assertFalse(v["valid"])
        self.assertTrue(any("matched more than once" in e for e in v["errors"]))

    def test_catches_edge_not_in_graph(self):
        v = graphkit.verify_bipartite_matching(self.LEFT, self.RIGHT, self.EDGES, [{"left": "a", "right": "y"}])
        self.assertFalse(v["valid"])

    def test_empty_matching_on_empty_graph_is_trivially_maximum(self):
        v = graphkit.verify_bipartite_matching(["a"], ["x"], [], [])
        self.assertTrue(v["valid"])
        self.assertTrue(v["is_maximum"])
        self.assertEqual(v["minimum_vertex_cover"], {"left": [], "right": []})


class BipartiteValidationTests(unittest.TestCase):
    def test_left_right_overlap_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.maximum_bipartite_matching(["a", "b"], ["b", "c"], [])

    def test_edge_from_must_be_a_left_node(self):
        with self.assertRaises(ValueError):
            graphkit.maximum_bipartite_matching(["a"], ["x"], [{"from": "x", "to": "a"}])

    def test_edge_to_must_be_a_right_node(self):
        with self.assertRaises(ValueError):
            graphkit.maximum_bipartite_matching(["a"], ["x"], [{"from": "a", "to": "a"}])

    def test_duplicate_bipartite_edge_rejected(self):
        edges = [{"from": "a", "to": "x"}, {"from": "a", "to": "x"}]
        with self.assertRaises(ValueError):
            graphkit.maximum_bipartite_matching(["a"], ["x"], edges)


# ---------------------------------------------------------------------------
# Assignment problem
# ---------------------------------------------------------------------------


def _cost_matrix_edges(left, right, matrix):
    return [
        {"from": left[i], "to": right[j], "weight": matrix[i][j]}
        for i in range(len(left))
        for j in range(len(right))
    ]


class AssignmentProblemTests(unittest.TestCase):
    # Textbook 3x3 cost matrix (brute-forced by hand over all 6 permutations):
    # min total = 9 (r0->c1, r1->c0, r2->c2); max total = 21 (r0->c2, r1->c1, r2->c0).
    LEFT = ["r0", "r1", "r2"]
    RIGHT = ["c0", "c1", "c2"]
    COSTS = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]

    def test_known_minimum_assignment(self):
        edges = _cost_matrix_edges(self.LEFT, self.RIGHT, self.COSTS)
        result = graphkit.assignment_problem(self.LEFT, self.RIGHT, edges, maximize=False)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["total_weight"], 9.0)
        self.assertTrue(result["verification"]["optimality_proven"])
        self.assertEqual({(a["left"], a["right"]) for a in result["assignment"]}, {("r0", "c1"), ("r1", "c0"), ("r2", "c2")})

    def test_known_maximum_assignment(self):
        edges = _cost_matrix_edges(self.LEFT, self.RIGHT, self.COSTS)
        result = graphkit.assignment_problem(self.LEFT, self.RIGHT, edges, maximize=True)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["total_weight"], 21.0)
        self.assertTrue(result["verification"]["optimality_proven"])

    def test_infeasible_when_no_perfect_assignment_possible(self):
        # both left nodes can only reach the same single right node -- no bijection exists.
        left, right = ["a", "b"], ["x", "y"]
        edges = [{"from": "a", "to": "x", "weight": 1}, {"from": "b", "to": "x", "weight": 2}]
        result = graphkit.assignment_problem(left, right, edges)
        self.assertFalse(result["feasible"])
        self.assertEqual(result["max_real_matching_size"], 1)
        self.assertEqual(result["required_size"], 2)

    def test_unequal_sizes_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.assignment_problem(["a", "b"], ["x"], [{"from": "a", "to": "x", "weight": 1}])

    def test_weight_magnitude_cap_enforced(self):
        edges = [{"from": "a", "to": "x", "weight": 1_000_001}]
        with self.assertRaises(ValueError):
            graphkit.assignment_problem(["a"], ["x"], edges)

    def test_missing_weight_rejected(self):
        with self.assertRaises(ValueError):
            graphkit.assignment_problem(["a"], ["x"], [{"from": "a", "to": "x"}])

    def test_single_pair_trivial_assignment(self):
        result = graphkit.assignment_problem(["a"], ["x"], [{"from": "a", "to": "x", "weight": 42}])
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["total_weight"], 42.0)

    def test_greedy_smallest_edge_first_is_provably_suboptimal(self):
        # Concrete counterexample (the same shape documented in real assignment-problem
        # write-ups): greedily taking the globally cheapest edge first, then being forced
        # into whatever's left, gives a WORSE total than the true optimum.
        left, right = ["alice", "george"], ["task1", "task2"]
        # alice-task1=1 (the global minimum -- greedy grabs this first), forcing
        # george-task2=8 -> greedy total 9. The other pairing (alice-task2=4,
        # george-task1=3) totals 7 -- strictly better, and what assignment_problem finds.
        edges = [
            {"from": "alice", "to": "task1", "weight": 1},
            {"from": "alice", "to": "task2", "weight": 4},
            {"from": "george", "to": "task1", "weight": 3},
            {"from": "george", "to": "task2", "weight": 8},
        ]
        # Reproduce the naive greedy heuristic directly to show it really is worse.
        by_weight = sorted(edges, key=lambda e: e["weight"])
        greedy_total = 0
        used_left, used_right = set(), set()
        for e in by_weight:
            if e["from"] in used_left or e["to"] in used_right:
                continue
            greedy_total += e["weight"]
            used_left.add(e["from"])
            used_right.add(e["to"])
        self.assertEqual(greedy_total, 9)

        result = graphkit.assignment_problem(left, right, edges, maximize=False)
        self.assertAlmostEqual(result["total_weight"], 7.0)
        self.assertLess(result["total_weight"], greedy_total)
        self.assertTrue(result["verification"]["optimality_proven"])


class VerifyAssignmentTests(unittest.TestCase):
    LEFT = ["r0", "r1", "r2"]
    RIGHT = ["c0", "c1", "c2"]
    COSTS = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]

    def test_accepts_solvers_own_certificate(self):
        edges = _cost_matrix_edges(self.LEFT, self.RIGHT, self.COSTS)
        solved = graphkit.assignment_problem(self.LEFT, self.RIGHT, edges, maximize=False)
        v = graphkit.verify_assignment(self.LEFT, self.RIGHT, edges, solved["assignment"], maximize=False)
        # (re-check without potentials: still structurally valid, optimality just unproven)
        self.assertTrue(v["valid"])
        self.assertFalse(v["optimality_proven"])

    def test_bad_potentials_fail_optimality_proof(self):
        edges = _cost_matrix_edges(self.LEFT, self.RIGHT, self.COSTS)
        solved = graphkit.assignment_problem(self.LEFT, self.RIGHT, edges, maximize=False)
        zero_potentials = {"left": {n: 0 for n in self.LEFT}, "right": {n: 0 for n in self.RIGHT}}
        v = graphkit.verify_assignment(
            self.LEFT, self.RIGHT, edges, solved["assignment"], maximize=False, potentials=zero_potentials
        )
        self.assertFalse(v["optimality_proven"])

    def test_suboptimal_assignment_cannot_be_proven_optimal_by_any_valid_certificate(self):
        # A deliberately suboptimal (but structurally valid) assignment: r0-c0, r1-c1,
        # r2-c2 costs 9+4+1=14, worse than the true optimum of 9. Even feeding it the
        # solver's own genuine dual potentials (correct FOR THE OPTIMAL assignment, not
        # this one) must fail the check, since the equality (complementary slackness)
        # condition can't hold for a non-optimal matching's pairs.
        edges = _cost_matrix_edges(self.LEFT, self.RIGHT, self.COSTS)
        solved = graphkit.assignment_problem(self.LEFT, self.RIGHT, edges, maximize=False)
        suboptimal = [{"left": "r0", "right": "c0"}, {"left": "r1", "right": "c1"}, {"left": "r2", "right": "c2"}]
        v = graphkit.verify_assignment(
            self.LEFT, self.RIGHT, edges, suboptimal, maximize=False, potentials=solved["potentials"]
        )
        self.assertFalse(v["optimality_proven"])

    def test_catches_non_bijection(self):
        edges = _cost_matrix_edges(self.LEFT, self.RIGHT, self.COSTS)
        v = graphkit.verify_assignment(self.LEFT, self.RIGHT, edges, [{"left": "r0", "right": "c0"}])
        self.assertFalse(v["valid"])

    def test_catches_edge_not_in_graph(self):
        left, right = ["r0", "r1"], ["c0", "c1"]
        edges = [
            {"from": "r0", "to": "c0", "weight": 1},
            {"from": "r0", "to": "c1", "weight": 2},
            {"from": "r1", "to": "c0", "weight": 3},
            # r1-c1 deliberately missing
        ]
        v = graphkit.verify_assignment(left, right, edges, [{"left": "r0", "right": "c1"}, {"left": "r1", "right": "c1"}])
        self.assertFalse(v["valid"])


if __name__ == "__main__":
    unittest.main()
