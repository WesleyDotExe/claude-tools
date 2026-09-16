"""Tests aimed at: exact answers checked against known textbook values (birthday
paradox, Monty Hall, dice sums, card-hand hypergeometric odds, binomial trials),
input validation, the Bayes-theorem path cross-checked against monty_hall's own
independently-derived formula, and that the simulation machinery actually flags a
wrong claim rather than only ever passing a correct one. Run:
python3 -m unittest discover -s tests -v
"""
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from probkit import (  # noqa: E402
    _simulation_report,
    _wilson_interval,
    bayes_update,
    binomial_probability,
    birthday_collision,
    dice_sum_distribution,
    hypergeometric_probability,
    monty_hall,
)


def assert_matches_simulation(test, successes, trials, exact_probability, sigma=6):
    """Assert an observed frequency is within `sigma` standard errors of the exact
    probability -- generous on purpose (a real CSPRNG run, not a fixed seed) so
    this doesn't flake, while still catching a genuinely wrong formula.
    """
    p = exact_probability
    se = math.sqrt(p * (1 - p) / trials) if 0 < p < 1 else 1 / trials
    observed = successes / trials
    test.assertLessEqual(abs(observed - p), sigma * se + 1e-6, f"observed={observed} exact={p} se={se}")


class BirthdayCollisionTests(unittest.TestCase):
    def test_classic_23_people_365_days(self):
        result = birthday_collision(23, 365)
        self.assertAlmostEqual(result["probability_of_collision"]["decimal"], 0.5073, places=4)

    def test_zero_or_one_item_has_no_collision(self):
        self.assertEqual(birthday_collision(0, 365)["probability_of_collision"]["fraction"], "0/1")
        self.assertEqual(birthday_collision(1, 365)["probability_of_collision"]["fraction"], "0/1")

    def test_more_items_than_categories_is_certain(self):
        result = birthday_collision(5, 4)
        self.assertEqual(result["probability_of_collision"]["fraction"], "1/1")

    def test_negative_n_raises(self):
        with self.assertRaises(ValueError):
            birthday_collision(-1, 365)

    def test_zero_categories_raises(self):
        with self.assertRaises(ValueError):
            birthday_collision(5, 0)

    def test_verify_matches_exact_answer(self):
        result = birthday_collision(23, 365, verify=True, verify_trials=30000)
        exact = result["probability_of_collision"]["decimal"]
        sim = result["simulation"]
        assert_matches_simulation(self, sim["successes"], sim["trials"], exact)

    def test_verify_trials_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            birthday_collision(23, 365, verify=True, verify_trials=10)


class DiceSumDistributionTests(unittest.TestCase):
    def test_two_d6_sum_seven_is_one_sixth(self):
        result = dice_sum_distribution(2, 6, target=7)
        self.assertEqual(result["event_probability"]["fraction"], "1/6")

    def test_full_distribution_sums_to_one(self):
        result = dice_sum_distribution(3, 6)
        total = sum(Fraction(v["fraction"]) for v in result["distribution"].values())
        self.assertEqual(total, 1)

    def test_distribution_bounds(self):
        result = dice_sum_distribution(2, 6)
        self.assertEqual(result["min_sum"], 2)
        self.assertEqual(result["max_sum"], 12)
        self.assertEqual(set(result["distribution"].keys()), {str(s) for s in range(2, 13)})

    def test_at_least_and_at_most_combine(self):
        result = dice_sum_distribution(1, 6, at_least=3, at_most=5)
        self.assertEqual(result["event_probability"]["fraction"], "1/2")  # {3,4,5} of 6

    def test_invalid_num_dice_raises(self):
        with self.assertRaises(ValueError):
            dice_sum_distribution(0, 6)

    def test_invalid_sides_raises(self):
        with self.assertRaises(ValueError):
            dice_sum_distribution(2, 1)

    def test_oversized_space_raises(self):
        with self.assertRaises(ValueError):
            dice_sum_distribution(20, 100)

    def test_verify_matches_exact_answer(self):
        result = dice_sum_distribution(2, 6, target=7, verify=True, verify_trials=30000)
        exact = result["event_probability"]["decimal"]
        sim = result["simulation"]
        assert_matches_simulation(self, sim["successes"], sim["trials"], exact)


class HypergeometricProbabilityTests(unittest.TestCase):
    def test_at_least_two_aces_in_five_card_hand(self):
        result = hypergeometric_probability(52, 4, 5, at_least=2)
        # 1 - P(0 aces) - P(1 ace), textbook value.
        self.assertAlmostEqual(result["event_probability"]["decimal"], 0.04168, places=5)

    def test_probabilities_over_full_range_sum_to_one(self):
        total = Fraction(0)
        for k in range(0, 5):
            total += Fraction(
                hypergeometric_probability(52, 4, 5, exactly=k)["event_probability"]["fraction"]
            )
        self.assertEqual(total, 1)

    def test_no_event_specified_raises(self):
        with self.assertRaises(ValueError):
            hypergeometric_probability(52, 4, 5)

    def test_sample_size_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            hypergeometric_probability(52, 4, 53, exactly=0)

    def test_success_states_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            hypergeometric_probability(52, 53, 5, exactly=0)

    def test_verify_matches_exact_answer(self):
        result = hypergeometric_probability(52, 4, 5, at_least=2, verify=True, verify_trials=30000)
        exact = result["event_probability"]["decimal"]
        sim = result["simulation"]
        assert_matches_simulation(self, sim["successes"], sim["trials"], exact)


class BinomialProbabilityTests(unittest.TestCase):
    def test_exact_fraction_input_stays_exact(self):
        result = binomial_probability(10, "1/6", at_least=1)
        self.assertEqual(result["event_probability"]["fraction"], "50700551/60466176")

    def test_float_input_gives_decimal_only(self):
        result = binomial_probability(4, 0.5, exactly=2)
        self.assertAlmostEqual(result["event_probability"]["decimal"], 0.375, places=6)
        self.assertNotIn("fraction", result["event_probability"])

    def test_no_event_specified_raises(self):
        with self.assertRaises(ValueError):
            binomial_probability(10, 0.5)

    def test_out_of_range_probability_raises(self):
        with self.assertRaises(ValueError):
            binomial_probability(10, 1.5, exactly=1)

    def test_negative_n_raises(self):
        with self.assertRaises(ValueError):
            binomial_probability(-1, 0.5, exactly=0)

    def test_verify_matches_exact_answer(self):
        result = binomial_probability(10, "1/6", at_least=1, verify=True, verify_trials=30000)
        exact = result["event_probability"]["decimal"]
        sim = result["simulation"]
        assert_matches_simulation(self, sim["successes"], sim["trials"], exact)


class BayesUpdateTests(unittest.TestCase):
    def test_certain_evidence_gives_certain_posterior(self):
        result = bayes_update("1/3", 1, 0)
        self.assertEqual(result["posterior"]["fraction"], "1/1")

    def test_matches_monty_hall_switch_probability_independently(self):
        # H = "the car is behind door 2" (not the contestant's original pick).
        # P(host opens door 3 | car behind door2) = 1 (forced).
        # P(host opens door 3 | car NOT behind door2) = 1/4 (derived in the
        # docstring/README). This is an independent route to the same answer
        # monty_hall() computes via its own closed-form formula.
        bayes_result = bayes_update(Fraction(1, 3), 1, Fraction(1, 4))
        monty_result = monty_hall()
        self.assertEqual(
            bayes_result["posterior"]["fraction"],
            monty_result["win_probability_if_switch"]["fraction"],
        )

    def test_impossible_evidence_raises(self):
        with self.assertRaises(ValueError):
            bayes_update(0.5, 0, 0)

    def test_verify_matches_exact_answer(self):
        result = bayes_update(1 / 3, 0.9, 0.1, verify=True, verify_trials=30000)
        exact = result["posterior"]
        sim = result["simulation"]
        assert_matches_simulation(self, sim["successes"], sim["trials"], exact)


class MontyHallTests(unittest.TestCase):
    def test_classic_three_door_version(self):
        result = monty_hall()
        self.assertEqual(result["win_probability_if_stay"]["fraction"], "1/3")
        self.assertEqual(result["win_probability_if_switch"]["fraction"], "2/3")
        self.assertTrue(result["switching_is_better"])

    def test_generalized_ten_door_version(self):
        result = monty_hall(doors=10, cars=1, reveal=8)
        self.assertEqual(result["win_probability_if_stay"]["fraction"], "1/10")
        self.assertEqual(result["win_probability_if_switch"]["fraction"], "9/10")

    def test_no_reveal_switching_is_no_better_than_staying(self):
        result = monty_hall(doors=3, cars=1, reveal=0)
        self.assertEqual(
            result["win_probability_if_stay"]["fraction"],
            result["win_probability_if_switch"]["fraction"],
        )

    def test_too_few_doors_raises(self):
        with self.assertRaises(ValueError):
            monty_hall(doors=2)

    def test_cars_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            monty_hall(doors=3, cars=3)

    def test_reveal_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            monty_hall(doors=3, cars=1, reveal=2)

    def test_verify_matches_exact_answers_for_both_strategies(self):
        result = monty_hall(verify=True, verify_trials=30000)
        sim = result["simulation"]
        assert_matches_simulation(
            self, sim["stay"]["successes"], sim["trials"],
            result["win_probability_if_stay"]["decimal"],
        )
        assert_matches_simulation(
            self, sim["switch"]["successes"], sim["trials"],
            result["win_probability_if_switch"]["decimal"],
        )


class SimulationMachineryTests(unittest.TestCase):
    """Confirms the confidence-interval check actually catches a wrong claim,
    not just that it passes a correct one -- the same "prove it has teeth"
    pattern secure-random uses for its chi-square test.
    """

    def test_wilson_interval_is_narrow_and_centered_for_large_n(self):
        lo, hi = _wilson_interval(5000, 10000)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertLess(hi - lo, 0.02)

    def test_correct_claim_falls_inside_interval(self):
        report = _simulation_report(successes=6667, trials=10000, exact=Fraction(2, 3))
        self.assertTrue(report["exact_within_confidence_interval"])

    def test_wrong_claim_is_flagged_outside_interval(self):
        # 6667/10000 is close to 2/3, nowhere near 1/3 -- a genuinely wrong
        # "exact" answer must be flagged, not silently accepted.
        report = _simulation_report(successes=6667, trials=10000, exact=Fraction(1, 3))
        self.assertFalse(report["exact_within_confidence_interval"])


if __name__ == "__main__":
    unittest.main()
