import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import planner  # noqa: E402


LIGHT_ACTIONS = {
    "turn_on": {
        "parameters": ["x"],
        "preconditions": [["not", "on", "x"]],
        "add": [["on", "x"]],
        "delete": [],
    },
    "turn_off": {
        "parameters": ["x"],
        "preconditions": [["on", "x"]],
        "add": [],
        "delete": [["on", "x"]],
    },
}


class DescribeFormatTests(unittest.TestCase):
    def test_returns_worked_example(self):
        d = planner.describe_planning_format()
        self.assertIn("example_domain", d)
        self.assertIn("negation", d)


class LightSwitchTests(unittest.TestCase):
    def test_already_at_goal_returns_empty_plan(self):
        r = planner.solve(["lamp"], [["on", "lamp"]], [["on", "lamp"]], LIGHT_ACTIONS)
        self.assertTrue(r["solvable"])
        self.assertEqual(r["plan"], [])
        self.assertEqual(r["plan_length"], 0)

    def test_one_step_plan(self):
        r = planner.solve(["lamp"], [], [["on", "lamp"]], LIGHT_ACTIONS)
        self.assertTrue(r["solvable"])
        self.assertEqual(r["plan"], [{"action": "turn_on", "args": ["lamp"]}])
        self.assertTrue(r["optimal"])

    def test_negated_goal(self):
        r = planner.solve(["lamp"], [["on", "lamp"]], [["not", "on", "lamp"]], LIGHT_ACTIONS)
        self.assertEqual(r["plan"], [{"action": "turn_off", "args": ["lamp"]}])


# --------------------------------------------------------------------------
# Sussman anomaly -- the canonical example showing naive "achieve goals one
# at a time" planning fails (achieving on(A,B) first, greedily, undoes
# progress toward on(B,C)). Known optimal solution under pickup/putdown/
# stack/unstack decomposition is 6 actions: unstack C, putdown C, pickup B,
# stack B C, pickup A, stack A B.
# --------------------------------------------------------------------------
SUSSMAN_OBJECTS = ["a", "b", "c"]
SUSSMAN_INITIAL = [
    ["on", "c", "a"],
    ["ontable", "a"],
    ["ontable", "b"],
    ["clear", "b"],
    ["clear", "c"],
    ["handempty"],
]
SUSSMAN_GOAL = [["on", "a", "b"], ["on", "b", "c"]]


class SussmanAnomalyTests(unittest.TestCase):
    def test_finds_known_optimal_plan_length(self):
        r = planner.solve(SUSSMAN_OBJECTS, SUSSMAN_INITIAL, SUSSMAN_GOAL, planner.BLOCKS_WORLD_ACTIONS)
        self.assertTrue(r["solvable"])
        self.assertTrue(r["optimal"])
        self.assertEqual(r["plan_length"], 6)

    def test_plan_passes_independent_verification(self):
        r = planner.solve(SUSSMAN_OBJECTS, SUSSMAN_INITIAL, SUSSMAN_GOAL, planner.BLOCKS_WORLD_ACTIONS)
        self.assertTrue(r["verification"]["valid"])
        self.assertTrue(r["verification"]["goal_reached"])

    def test_verify_plan_standalone_matches_solver(self):
        r = planner.solve(SUSSMAN_OBJECTS, SUSSMAN_INITIAL, SUSSMAN_GOAL, planner.BLOCKS_WORLD_ACTIONS)
        v = planner.verify_plan(SUSSMAN_OBJECTS, SUSSMAN_INITIAL, SUSSMAN_GOAL, planner.BLOCKS_WORLD_ACTIONS, r["plan"])
        self.assertTrue(v["valid"])
        self.assertEqual(v["steps_applied"], 6)


class VerifyPlanCatchesBadPlansTests(unittest.TestCase):
    INIT = [["ontable", "a"], ["clear", "a"], ["handempty"]]

    def test_catches_unmet_precondition(self):
        bad_plan = [{"action": "pickup", "args": ["a"]}, {"action": "pickup", "args": ["a"]}]
        v = planner.verify_plan(["a"], self.INIT, [["holding", "a"]], planner.BLOCKS_WORLD_ACTIONS, bad_plan)
        self.assertFalse(v["valid"])
        self.assertFalse(v["steps"][1]["ok"])
        self.assertIn(["handempty"], v["steps"][1]["unmet_preconditions"])

    def test_catches_wrong_arg_count(self):
        v = planner.verify_plan(["a"], self.INIT, [["holding", "a"]], planner.BLOCKS_WORLD_ACTIONS, [{"action": "pickup", "args": []}])
        self.assertFalse(v["valid"])
        self.assertIn("argument", v["steps"][0]["error"])

    def test_catches_unknown_action(self):
        v = planner.verify_plan(["a"], self.INIT, [["holding", "a"]], planner.BLOCKS_WORLD_ACTIONS, [{"action": "fly", "args": ["a"]}])
        self.assertFalse(v["valid"])
        self.assertIn("unknown action", v["steps"][0]["error"])

    def test_catches_unknown_object(self):
        v = planner.verify_plan(["a"], self.INIT, [["holding", "a"]], planner.BLOCKS_WORLD_ACTIONS, [{"action": "pickup", "args": ["zzz"]}])
        self.assertFalse(v["valid"])
        self.assertIn("unknown object", v["steps"][0]["error"])

    def test_valid_plan_but_goal_not_actually_reached(self):
        v = planner.verify_plan(["a"], self.INIT, [["on", "a", "a"]], planner.BLOCKS_WORLD_ACTIONS, [{"action": "pickup", "args": ["a"]}])
        self.assertTrue(v["steps"][0]["ok"])
        self.assertFalse(v["goal_reached"])
        self.assertFalse(v["valid"])


class UnsolvableProofTests(unittest.TestCase):
    def test_contradictory_goal_is_proven_unreachable(self):
        init = [["ontable", "a"], ["ontable", "b"], ["clear", "a"], ["clear", "b"], ["handempty"]]
        goal = [["on", "a", "b"], ["on", "b", "a"]]
        r = planner.solve(["a", "b"], init, goal, planner.BLOCKS_WORLD_ACTIONS)
        self.assertFalse(r["solvable"])
        self.assertIn("provably unreachable", r["reason"])

    def test_budget_exceeded_raises_instead_of_claiming_unsolvable(self):
        init = [["ontable", "a"], ["ontable", "b"], ["clear", "a"], ["clear", "b"], ["handempty"]]
        goal = [["on", "a", "b"], ["on", "b", "a"]]
        with self.assertRaises(ValueError):
            planner.solve(["a", "b"], init, goal, planner.BLOCKS_WORLD_ACTIONS, max_states=1)


class ValidationTests(unittest.TestCase):
    def test_duplicate_objects_rejected(self):
        with self.assertRaises(ValueError):
            planner.solve(["a", "a"], [], [["on", "lamp"]], LIGHT_ACTIONS)

    def test_unknown_predicate_arg_rejected(self):
        bad_actions = {
            "turn_on": {"parameters": ["x"], "preconditions": [], "add": [["on", "y"]], "delete": []},
        }
        with self.assertRaises(ValueError):
            planner.solve(["lamp"], [], [["on", "lamp"]], bad_actions)

    def test_negated_add_effect_rejected(self):
        bad_actions = {
            "turn_on": {"parameters": ["x"], "preconditions": [], "add": [["not", "on", "x"]], "delete": []},
        }
        with self.assertRaises(ValueError):
            planner.solve(["lamp"], [], [["on", "lamp"]], bad_actions)

    def test_duplicate_initial_facts_rejected(self):
        with self.assertRaises(ValueError):
            planner.solve(["lamp"], [["on", "lamp"], ["on", "lamp"]], [["on", "lamp"]], LIGHT_ACTIONS)

    def test_empty_objects_rejected(self):
        with self.assertRaises(ValueError):
            planner.solve([], [], [["on", "lamp"]], LIGHT_ACTIONS)

    def test_parameter_colliding_with_object_name_rejected(self):
        bad_actions = {
            "turn_on": {"parameters": ["lamp"], "preconditions": [], "add": [["on", "lamp"]], "delete": []},
        }
        with self.assertRaises(ValueError):
            planner.solve(["lamp"], [], [["on", "lamp"]], bad_actions)


class GenerateBlocksWorldProblemTests(unittest.TestCase):
    def test_reproducible_with_same_seed(self):
        p1 = planner.generate_blocks_world_problem(5, seed=7)
        p2 = planner.generate_blocks_world_problem(5, seed=7)
        self.assertEqual(p1, p2)

    def test_different_seed_usually_differs(self):
        p1 = planner.generate_blocks_world_problem(5, seed=1)
        p2 = planner.generate_blocks_world_problem(5, seed=2)
        self.assertNotEqual((p1["initial_state"], p1["goal"]), (p2["initial_state"], p2["goal"]))

    def test_generated_problem_is_solvable_and_verifiable(self):
        for seed in range(10):
            prob = planner.generate_blocks_world_problem(4, seed=seed)
            r = planner.solve(prob["objects"], prob["initial_state"], prob["goal"], prob["actions"])
            self.assertTrue(r["solvable"], f"seed {seed} produced an unsolvable instance")
            v = planner.verify_plan(
                prob["objects"], prob["initial_state"], prob["goal"], prob["actions"], r["plan"]
            )
            self.assertTrue(v["valid"], f"seed {seed}'s plan failed independent verification")

    def test_num_blocks_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            planner.generate_blocks_world_problem(1)
        with self.assertRaises(ValueError):
            planner.generate_blocks_world_problem(9)

    def test_goal_always_differs_from_initial_state(self):
        for seed in range(10):
            prob = planner.generate_blocks_world_problem(3, seed=seed)
            init_arrangement = sorted(f for f in prob["initial_state"] if f[0] in ("on", "ontable"))
            self.assertNotEqual(sorted(prob["goal"]), init_arrangement)


if __name__ == "__main__":
    unittest.main()
