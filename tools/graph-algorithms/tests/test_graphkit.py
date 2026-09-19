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


if __name__ == "__main__":
    unittest.main()
