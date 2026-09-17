import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import puzzlekit  # noqa: E402


# --------------------------------------------------------------------------
# The classic Einstein "zebra puzzle" -- 5 houses, 5 categories, 15 clues,
# published answer: the German owns the zebra, the Norwegian drinks water.
# --------------------------------------------------------------------------
ZEBRA_CATEGORIES = {
    "color": ["Red", "Green", "White", "Yellow", "Blue"],
    "nationality": ["Brit", "Swede", "Dane", "Norwegian", "German"],
    "beverage": ["Tea", "Coffee", "Milk", "Beer", "Water"],
    "cigarette": ["PallMall", "Dunhill", "Blend", "BlueMaster", "Prince"],
    "pet": ["Dogs", "Birds", "Cats", "Horses", "Zebra"],
}

ZEBRA_CLUES = [
    {"type": "same_position", "a": ["color", "Red"], "b": ["nationality", "Brit"]},
    {"type": "same_position", "a": ["nationality", "Swede"], "b": ["pet", "Dogs"]},
    {"type": "same_position", "a": ["nationality", "Dane"], "b": ["beverage", "Tea"]},
    {"type": "immediately_left_of", "a": ["color", "Green"], "b": ["color", "White"]},
    {"type": "same_position", "a": ["color", "Green"], "b": ["beverage", "Coffee"]},
    {"type": "same_position", "a": ["cigarette", "PallMall"], "b": ["pet", "Birds"]},
    {"type": "same_position", "a": ["color", "Yellow"], "b": ["cigarette", "Dunhill"]},
    {"type": "position", "item": ["beverage", "Milk"], "position": 3},
    {"type": "position", "item": ["nationality", "Norwegian"], "position": 1},
    {"type": "next_to", "a": ["cigarette", "Blend"], "b": ["pet", "Cats"]},
    {"type": "next_to", "a": ["pet", "Horses"], "b": ["cigarette", "Dunhill"]},
    {"type": "same_position", "a": ["cigarette", "BlueMaster"], "b": ["beverage", "Beer"]},
    {"type": "same_position", "a": ["nationality", "German"], "b": ["cigarette", "Prince"]},
    {"type": "next_to", "a": ["nationality", "Norwegian"], "b": ["color", "Blue"]},
    {"type": "next_to", "a": ["cigarette", "Blend"], "b": ["beverage", "Water"]},
]


class ZebraPuzzleTests(unittest.TestCase):
    def test_solves_the_classic_puzzle(self):
        result = puzzlekit.solve(ZEBRA_CATEGORIES, ZEBRA_CLUES)
        by_cat = result["solution_by_category"]
        german_house = by_cat["nationality"]["German"]
        zebra_house = by_cat["pet"]["Zebra"]
        norwegian_house = by_cat["nationality"]["Norwegian"]
        water_house = by_cat["beverage"]["Water"]
        self.assertEqual(german_house, zebra_house, "the German should own the zebra")
        self.assertEqual(norwegian_house, water_house, "the Norwegian should drink water")

    def test_solution_is_proven_unique(self):
        result = puzzlekit.solve(ZEBRA_CATEGORIES, ZEBRA_CLUES, prove_unique=True)
        self.assertIs(result["unique"], True)
        self.assertNotIn("alternate_solution_by_position", result)

    def test_solvers_own_solution_passes_independent_verification(self):
        result = puzzlekit.solve(ZEBRA_CATEGORIES, ZEBRA_CLUES)
        v = result["verification"]
        self.assertTrue(v["all_satisfied"])
        self.assertTrue(v["well_formed"])
        self.assertTrue(all(r["satisfied"] is True for r in v["clue_results"]))
        self.assertEqual(len(v["clue_results"]), len(ZEBRA_CLUES))

    def test_prove_unique_false_is_faster_and_still_correct(self):
        result = puzzlekit.solve(ZEBRA_CATEGORIES, ZEBRA_CLUES, prove_unique=False)
        self.assertNotIn("unique", result)
        by_cat = result["solution_by_category"]
        self.assertEqual(by_cat["nationality"]["German"], by_cat["pet"]["Zebra"])


class SmallToyPuzzleTests(unittest.TestCase):
    """A tiny 2-category, 3-position puzzle, hand-verified, to exercise the
    solver on something small enough to reason about by hand."""

    CATEGORIES = {
        "color": ["Red", "Green", "Blue"],
        "animal": ["Cat", "Dog", "Fish"],
    }

    def test_left_of_and_distance_clues(self):
        clues = [
            {"type": "position", "item": ["color", "Red"], "position": 1},
            {"type": "left_of", "a": ["color", "Green"], "b": ["color", "Blue"]},
            {"type": "distance", "a": ["animal", "Cat"], "b": ["animal", "Dog"], "n": 2},
        ]
        result = puzzlekit.solve(self.CATEGORIES, clues)
        by_cat = result["solution_by_category"]
        self.assertEqual(by_cat["color"]["Red"], 1)
        self.assertEqual(by_cat["color"]["Green"], 2)
        self.assertEqual(by_cat["color"]["Blue"], 3)
        # distance 2 apart in a 3-slot line means positions 1 and 3
        self.assertEqual({by_cat["animal"]["Cat"], by_cat["animal"]["Dog"]}, {1, 3})

    def test_right_of_and_immediately_right_of(self):
        clues = [
            {"type": "position", "item": ["color", "Blue"], "position": 3},
            {"type": "right_of", "a": ["color", "Green"], "b": ["color", "Red"]},
            {"type": "immediately_right_of", "a": ["animal", "Dog"], "b": ["animal", "Cat"]},
        ]
        result = puzzlekit.solve(self.CATEGORIES, clues)
        by_cat = result["solution_by_category"]
        self.assertEqual(by_cat["color"]["Red"], 1)
        self.assertEqual(by_cat["color"]["Green"], 2)
        self.assertEqual(by_cat["color"]["Blue"], 3)
        self.assertEqual(by_cat["animal"]["Dog"], by_cat["animal"]["Cat"] + 1)

    def test_not_next_to_and_different_position(self):
        clues = [
            {"type": "position", "item": ["color", "Red"], "position": 1},
            {"type": "different_position", "a": ["color", "Green"], "b": ["color", "Blue"]},
            {"type": "not_next_to", "a": ["animal", "Cat"], "b": ["animal", "Dog"]},
        ]
        result = puzzlekit.solve(self.CATEGORIES, clues)
        by_cat = result["solution_by_category"]
        # only non-adjacent pair of distinct positions in a 3-line is (1, 3)
        self.assertEqual({by_cat["animal"]["Cat"], by_cat["animal"]["Dog"]}, {1, 3})

    def test_contradictory_clues_raise(self):
        clues = [
            {"type": "position", "item": ["color", "Red"], "position": 1},
            {"type": "position", "item": ["color", "Red"], "position": 2},
        ]
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, clues)

    def test_underconstrained_puzzle_is_not_unique(self):
        clues = [{"type": "position", "item": ["color", "Red"], "position": 1}]
        result = puzzlekit.solve(self.CATEGORIES, clues, prove_unique=True)
        self.assertIs(result["unique"], False)
        self.assertIn("alternate_solution_by_position", result)

    def test_max_nodes_cap_is_respected_without_crashing_or_hanging(self):
        # An absurdly small node budget on an underconstrained puzzle must fail
        # predictably (either "gave up before finding anything" or "found a
        # solution but couldn't finish proving uniqueness") -- never hang, and
        # never silently claim a wrong answer.
        clues = [{"type": "position", "item": ["color", "Red"], "position": 1}]
        try:
            result = puzzlekit.solve(self.CATEGORIES, clues, prove_unique=True, max_nodes=1)
        except ValueError as e:
            self.assertIn("max_nodes", str(e))
        else:
            self.assertIsNone(result["unique"])
            self.assertTrue(result["search_incomplete"])


class ValidationTests(unittest.TestCase):
    CATEGORIES = SmallToyPuzzleTests.CATEGORIES

    def test_empty_categories_raises(self):
        with self.assertRaises(ValueError):
            puzzlekit.solve({}, [{"type": "position", "item": ["a", "b"], "position": 1}])

    def test_mismatched_category_lengths_raise(self):
        cats = {"color": ["Red", "Green"], "animal": ["Cat", "Dog", "Fish"]}
        with self.assertRaises(ValueError):
            puzzlekit.solve(cats, [{"type": "position", "item": ["color", "Red"], "position": 1}])

    def test_duplicate_items_in_category_raise(self):
        cats = {"color": ["Red", "Red", "Blue"]}
        with self.assertRaises(ValueError):
            puzzlekit.solve(cats, [{"type": "position", "item": ["color", "Red"], "position": 1}])

    def test_unknown_clue_type_raises(self):
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, [{"type": "teleports_to", "a": ["color", "Red"], "b": ["color", "Blue"]}])

    def test_unknown_category_reference_raises(self):
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, [{"type": "position", "item": ["nope", "Red"], "position": 1}])

    def test_unknown_item_reference_raises(self):
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, [{"type": "position", "item": ["color", "Purple"], "position": 1}])

    def test_out_of_range_position_raises(self):
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, [{"type": "position", "item": ["color", "Red"], "position": 99}])

    def test_distance_out_of_range_raises(self):
        clues = [{"type": "distance", "a": ["color", "Red"], "b": ["color", "Blue"], "n": 99}]
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, clues)

    def test_self_referencing_clue_raises(self):
        clues = [{"type": "next_to", "a": ["color", "Red"], "b": ["color", "Red"]}]
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, clues)

    def test_no_clues_raises(self):
        with self.assertRaises(ValueError):
            puzzlekit.solve(self.CATEGORIES, [])

    def test_too_many_positions_raises(self):
        cats = {"x": [str(i) for i in range(13)]}
        with self.assertRaises(ValueError):
            puzzlekit.solve(cats, [{"type": "position", "item": ["x", "0"], "position": 1}])


class VerifySolutionTests(unittest.TestCase):
    CATEGORIES = SmallToyPuzzleTests.CATEGORIES
    CLUES = [
        {"type": "position", "item": ["color", "Red"], "position": 1},
        {"type": "left_of", "a": ["color", "Green"], "b": ["color", "Blue"]},
    ]
    CORRECT_GRID = {
        "1": {"color": "Red", "animal": "Cat"},
        "2": {"color": "Green", "animal": "Dog"},
        "3": {"color": "Blue", "animal": "Fish"},
    }

    def test_correct_guess_verifies_clean(self):
        v = puzzlekit.verify_solution(self.CATEGORIES, self.CLUES, self.CORRECT_GRID)
        self.assertTrue(v["all_satisfied"])
        self.assertTrue(v["well_formed"])
        self.assertEqual(v["structural_errors"], [])

    def test_wrong_guess_is_caught_not_rubber_stamped(self):
        bad_grid = {
            "1": {"color": "Green", "animal": "Cat"},  # violates position(Red)==1
            "2": {"color": "Red", "animal": "Dog"},
            "3": {"color": "Blue", "animal": "Fish"},
        }
        v = puzzlekit.verify_solution(self.CATEGORIES, self.CLUES, bad_grid)
        self.assertFalse(v["all_satisfied"])
        self.assertFalse(v["clue_results"][0]["satisfied"])

    def test_missing_item_is_a_structural_error_not_a_crash(self):
        incomplete_grid = {
            "1": {"color": "Red", "animal": "Cat"},
            "2": {"color": "Green", "animal": "Dog"},
            "3": {"animal": "Fish"},  # color missing at position 3
        }
        v = puzzlekit.verify_solution(self.CATEGORIES, self.CLUES, incomplete_grid)
        self.assertFalse(v["well_formed"])
        self.assertFalse(v["all_satisfied"])
        self.assertTrue(any("missing category" in e for e in v["structural_errors"]))

    def test_duplicate_item_is_a_structural_error(self):
        dup_grid = {
            "1": {"color": "Red", "animal": "Cat"},
            "2": {"color": "Red", "animal": "Dog"},  # Red used twice
            "3": {"color": "Blue", "animal": "Fish"},
        }
        v = puzzlekit.verify_solution(self.CATEGORIES, self.CLUES, dup_grid)
        self.assertFalse(v["well_formed"])
        self.assertTrue(any("appears at both position" in e for e in v["structural_errors"]))

    def test_wrong_position_key_raises(self):
        # An out-of-range position key isn't a "this solution is wrong" finding --
        # it means the input isn't a valid grid for this puzzle shape at all, same
        # as an unknown category/item, so it's rejected up front rather than folded
        # into structural_errors.
        bad_grid = dict(self.CORRECT_GRID)
        bad_grid["7"] = bad_grid.pop("3")
        with self.assertRaises(ValueError):
            puzzlekit.verify_solution(self.CATEGORIES, self.CLUES, bad_grid)


class DescribeClueTypesTests(unittest.TestCase):
    def test_every_clue_type_used_in_the_zebra_puzzle_is_documented(self):
        described = puzzlekit.describe_clue_types()["clue_types"]
        used_types = {c["type"] for c in ZEBRA_CLUES}
        self.assertTrue(used_types.issubset(described.keys()))

    def test_every_documented_example_is_actually_valid(self):
        described = puzzlekit.describe_clue_types()["clue_types"]
        categories = {
            "color": ["Red", "Green", "White", "Yellow", "Blue"],
            "nationality": ["Brit", "Swede", "Dane", "Norwegian", "German"],
            "pet": ["Dogs", "Birds", "Cats", "Horses", "Zebra"],
        }
        for name, spec in described.items():
            example = spec["example"]
            # Each example should validate on its own against a puzzle containing
            # every category/item it references (doesn't need to be solvable).
            clue_categories = {ref[0] for ref in (example.get("a"), example.get("b"), example.get("item")) if ref}
            self.assertTrue(clue_categories.issubset(categories.keys()), f"{name} example uses an undeclared category")


if __name__ == "__main__":
    unittest.main()
