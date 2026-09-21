import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import spacedkit


class DescribeFormatTests(unittest.TestCase):
    def test_returns_usable_worked_example(self):
        desc = spacedkit.describe_arrangement_format()
        self.assertIn("example_items", desc)
        self.assertIn("example_min_distance", desc)
        result = spacedkit.arrange_with_spacing(desc["example_items"], desc["example_min_distance"])
        self.assertTrue(result["arrangable"])
        self.assertTrue(result["verification"]["valid"])


class FeasibleArrangementTests(unittest.TestCase):
    def test_simple_feasible_case_no_two_adjacent(self):
        # 3 A's, 1 B, 1 C, min_distance=2 -- max count 3 == ceil(5/2), tight but feasible.
        items = [{"id": f"a{i}", "category": "A"} for i in range(3)]
        items += [{"id": "b1", "category": "B"}, {"id": "c1", "category": "C"}]
        result = spacedkit.arrange_with_spacing(items, min_distance=2)
        self.assertTrue(result["arrangable"])
        self.assertEqual(sorted(result["arrangement"]), sorted(it["id"] for it in items))
        self.assertTrue(result["verification"]["valid"])
        self.assertEqual(result["verification"]["violations"], [])

    def test_min_distance_k3_tight_but_feasible_arithmetic_spread(self):
        # 3 categories, 3 each, min_distance=3, n=9 -- classic a,b,c,a,b,c,a,b,c layout exists.
        items = []
        for cat in ("A", "B", "C"):
            items += [{"id": f"{cat}{i}", "category": cat} for i in range(3)]
        result = spacedkit.arrange_with_spacing(items, min_distance=3)
        self.assertTrue(result["arrangable"])
        v = spacedkit.verify_arrangement(items, 3, result["arrangement"])
        self.assertTrue(v["valid"])

    def test_min_distance_1_is_always_trivially_feasible(self):
        items = [{"id": f"a{i}", "category": "A"} for i in range(10)]
        result = spacedkit.arrange_with_spacing(items, min_distance=1)
        self.assertTrue(result["arrangable"])
        self.assertTrue(result["verification"]["valid"])

    def test_random_tie_breaking_produces_varied_arrangements(self):
        items = []
        for cat in ("A", "B", "C"):
            items += [{"id": f"{cat}{i}", "category": cat} for i in range(4)]
        seen = set()
        for _ in range(12):
            result = spacedkit.arrange_with_spacing(items, min_distance=2)
            self.assertTrue(result["arrangable"])
            seen.add(tuple(result["arrangement"]))
        # True CSPRNG-backed shuffling should not produce the exact same order every time.
        self.assertGreater(len(seen), 1)


class InfeasibleArrangementTests(unittest.TestCase):
    def test_simple_infeasible_single_category_too_frequent(self):
        # 4 A's, 1 B, min_distance=2: max count 4 > ceil(5/2)=3 -- provably impossible.
        items = [{"id": f"a{i}", "category": "A"} for i in range(4)]
        items += [{"id": "b1", "category": "B"}]
        result = spacedkit.arrange_with_spacing(items, min_distance=2, max_search_nodes=10_000)
        self.assertFalse(result["arrangable"])
        self.assertIn("search tree was explored", result["reason"])
        self.assertEqual(result["most_frequent_category"], "A")
        self.assertEqual(result["most_frequent_count"], 4)

    def test_multi_category_infeasible_despite_per_category_count_passing(self):
        # A=3, B=3, C=1, min_distance=3, n=7. ceil(7/3)=3, so EVERY category individually
        # satisfies count <= ceil(n/min_distance) -- the naive necessary-only check would
        # wrongly call this feasible. It genuinely isn't: only one length-7 slot pattern
        # spaces 3 items >=3 apart (positions 0,3,6), and A and B can't both have it.
        items = [{"id": f"A{i}", "category": "A"} for i in range(3)]
        items += [{"id": f"B{i}", "category": "B"} for i in range(3)]
        items += [{"id": "C0", "category": "C"}]
        result = spacedkit.arrange_with_spacing(items, min_distance=3, max_search_nodes=50_000)
        self.assertFalse(result["arrangable"])
        # Confirm the naive per-category bound would have missed this.
        import math

        n = len(items)
        for cat, count in result["category_counts"].items():
            self.assertLessEqual(count, math.ceil(n / 3))

    def test_search_budget_exceeded_raises_instead_of_guessing(self):
        items = [{"id": f"A{i}", "category": "A"} for i in range(3)]
        items += [{"id": f"B{i}", "category": "B"} for i in range(3)]
        items += [{"id": "C0", "category": "C"}]
        with self.assertRaises(ValueError) as ctx:
            spacedkit.arrange_with_spacing(items, min_distance=3, max_search_nodes=1)
        self.assertIn("max_search_nodes", str(ctx.exception))


class VerifyArrangementTests(unittest.TestCase):
    def setUp(self):
        self.items = []
        for cat in ("A", "B", "C"):
            self.items += [{"id": f"{cat}{i}", "category": cat} for i in range(3)]

    def test_accepts_solvers_own_output(self):
        result = spacedkit.arrange_with_spacing(self.items, min_distance=2)
        v = spacedkit.verify_arrangement(self.items, 2, result["arrangement"])
        self.assertTrue(v["valid"])

    def test_catches_two_same_category_too_close(self):
        bad = ["A0", "A1", "A2", "B0", "B1", "B2", "C0", "C1", "C2"]
        v = spacedkit.verify_arrangement(self.items, 2, bad)
        self.assertFalse(v["valid"])
        self.assertTrue(any(vi["category"] == "A" for vi in v["violations"]))

    def test_catches_missing_and_unexpected_ids(self):
        bad = ["A0", "A1", "A2", "B0", "B1", "B2", "C0", "C1", "ZZZ"]
        v = spacedkit.verify_arrangement(self.items, 2, bad)
        self.assertFalse(v["valid"])
        self.assertIn("C2", v["missing_ids"])
        self.assertIn("ZZZ", v["unexpected_ids"])

    def test_valid_arrangement_at_exact_min_distance_boundary(self):
        # a,b,c,a,b,c,a,b,c satisfies min_distance=3 exactly at the boundary.
        arrangement = ["A0", "B0", "C0", "A1", "B1", "C1", "A2", "B2", "C2"]
        v = spacedkit.verify_arrangement(self.items, 3, arrangement)
        self.assertTrue(v["valid"])

    def test_invalid_arrangement_one_short_of_min_distance(self):
        arrangement = ["A0", "B0", "A1", "C0", "B1", "A2", "C1", "B2", "C2"]
        v = spacedkit.verify_arrangement(self.items, 3, arrangement)
        self.assertFalse(v["valid"])


class ValidationTests(unittest.TestCase):
    def test_rejects_too_few_items(self):
        with self.assertRaises(ValueError):
            spacedkit.arrange_with_spacing([{"id": "a", "category": "A"}], min_distance=2)

    def test_rejects_duplicate_ids(self):
        items = [{"id": "a", "category": "A"}, {"id": "a", "category": "B"}]
        with self.assertRaises(ValueError):
            spacedkit.arrange_with_spacing(items, min_distance=1)

    def test_rejects_missing_category_field(self):
        items = [{"id": "a"}, {"id": "b", "category": "B"}]
        with self.assertRaises(ValueError):
            spacedkit.arrange_with_spacing(items, min_distance=1)

    def test_rejects_bad_min_distance(self):
        items = [{"id": "a", "category": "A"}, {"id": "b", "category": "B"}]
        for bad in (0, -1, 1.5, True, "2"):
            with self.assertRaises(ValueError):
                spacedkit.arrange_with_spacing(items, min_distance=bad)

    def test_rejects_bad_max_search_nodes(self):
        items = [{"id": "a", "category": "A"}, {"id": "b", "category": "B"}]
        for bad in (0, -5, 1.5, False):
            with self.assertRaises(ValueError):
                spacedkit.arrange_with_spacing(items, min_distance=1, max_search_nodes=bad)

    def test_verify_rejects_non_list_arrangement(self):
        items = [{"id": "a", "category": "A"}, {"id": "b", "category": "B"}]
        with self.assertRaises(ValueError):
            spacedkit.verify_arrangement(items, 1, "ab")


class GenerateArrangementProblemTests(unittest.TestCase):
    def test_reproducible_with_same_seed(self):
        g1 = spacedkit.generate_arrangement_problem(20, 4, seed=7)
        g2 = spacedkit.generate_arrangement_problem(20, 4, seed=7)
        self.assertEqual(g1["items"], g2["items"])

    def test_different_seeds_typically_differ(self):
        g1 = spacedkit.generate_arrangement_problem(20, 4, seed=1)
        g2 = spacedkit.generate_arrangement_problem(20, 4, seed=2)
        self.assertNotEqual(g1["items"], g2["items"])

    def test_every_category_used_at_least_once(self):
        g = spacedkit.generate_arrangement_problem(15, 5, seed=3)
        used = {it["category"] for it in g["items"]}
        self.assertEqual(len(used), 5)

    def test_item_count_matches_request(self):
        g = spacedkit.generate_arrangement_problem(30, 6, seed=99)
        self.assertEqual(len(g["items"]), 30)
        self.assertEqual(sum(g["category_counts"].values()), 30)

    def test_generated_instance_is_usable_end_to_end(self):
        g = spacedkit.generate_arrangement_problem(24, 6, seed=11)
        result = spacedkit.arrange_with_spacing(g["items"], min_distance=2)
        self.assertTrue(result["arrangable"])
        self.assertTrue(
            spacedkit.verify_arrangement(g["items"], 2, result["arrangement"])["valid"]
        )

    def test_rejects_bad_num_items_and_num_categories(self):
        with self.assertRaises(ValueError):
            spacedkit.generate_arrangement_problem(1, 1)
        with self.assertRaises(ValueError):
            spacedkit.generate_arrangement_problem(5, 6)


if __name__ == "__main__":
    unittest.main()
