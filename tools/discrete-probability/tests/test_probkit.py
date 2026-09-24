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
    _norm_cdf,
    _norm_ppf,
    _simulation_report,
    _wilson_interval,
    bayes_update,
    binomial_probability,
    birthday_collision,
    compare_two_proportions,
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


def _exact_permutation_p_value(successes_a, trials_a, successes_b, trials_b):
    """Ground truth for the permutation-test p-value computed directly, by
    hand, via the hypergeometric distribution over every possible split of
    the pooled outcomes (not via probkit's own simulation code at all) --
    used to check `compare_two_proportions(verify=True)`'s Monte Carlo
    estimate against a real independent derivation, not just against itself.
    """
    n_total = trials_a + trials_b
    total_successes = successes_a + successes_b
    observed_abs_diff = abs(successes_a / trials_a - successes_b / trials_b)
    lo_k = max(0, trials_a - (n_total - total_successes))
    hi_k = min(trials_a, total_successes)
    denom = math.comb(n_total, trials_a)
    total = Fraction(0)
    for k in range(lo_k, hi_k + 1):
        perm_diff = abs(k / trials_a - (total_successes - k) / trials_b)
        if perm_diff >= observed_abs_diff - 1e-9:
            total += Fraction(
                math.comb(total_successes, k) * math.comb(n_total - total_successes, trials_a - k),
                denom,
            )
    return float(total)


class CompareTwoProportionsTests(unittest.TestCase):
    def test_identical_proportions_not_significant(self):
        result = compare_two_proportions(50, 100, 50, 100)
        self.assertEqual(result["p_value"], 1.0)
        self.assertFalse(result["significant"])
        self.assertEqual(result["difference_a_minus_b"], 0.0)

    def test_clear_gap_is_significant(self):
        # 90/100 vs 40/100 -- textbook-obvious real gap.
        result = compare_two_proportions(90, 100, 40, 100)
        self.assertTrue(result["significant"])
        self.assertLess(result["p_value"], 0.001)
        lo, hi = result["difference_ci_newcombe"]
        self.assertGreater(lo, 0)  # CI for the difference excludes 0

    def test_borderline_gap_matches_hand_computed_z_test(self):
        # 62/100 vs 55/100 -- pooled p = 0.585, se = sqrt(0.585*0.415*0.02)
        # ~= 0.069682, z ~= 1.00457 -- worked by hand against the standard
        # pooled two-proportion z-test formula, independent of probkit's code.
        result = compare_two_proportions(62, 100, 55, 100)
        pooled = 117 / 200
        se = math.sqrt(pooled * (1 - pooled) * (1 / 100 + 1 / 100))
        expected_z = (0.62 - 0.55) / se
        self.assertAlmostEqual(result["z_statistic"], expected_z, places=6)
        expected_p = 2 * (1 - _norm_cdf(abs(expected_z)))
        self.assertAlmostEqual(result["p_value"], expected_p, places=6)

    def test_each_group_wilson_ci_matches_wilson_interval_directly(self):
        result = compare_two_proportions(62, 100, 55, 100)
        z = _norm_ppf(0.975)
        expected_a = _wilson_interval(62, 100, z)
        expected_b = _wilson_interval(55, 100, z)
        self.assertAlmostEqual(result["group_a"]["wilson_ci"][0], expected_a[0], places=6)
        self.assertAlmostEqual(result["group_a"]["wilson_ci"][1], expected_a[1], places=6)
        self.assertAlmostEqual(result["group_b"]["wilson_ci"][0], expected_b[0], places=6)
        self.assertAlmostEqual(result["group_b"]["wilson_ci"][1], expected_b[1], places=6)

    def test_zero_trials_raises(self):
        with self.assertRaises(ValueError):
            compare_two_proportions(0, 0, 1, 10)

    def test_successes_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            compare_two_proportions(11, 10, 1, 10)
        with self.assertRaises(ValueError):
            compare_two_proportions(-1, 10, 1, 10)

    def test_confidence_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            compare_two_proportions(5, 10, 5, 10, confidence=1.0)
        with self.assertRaises(ValueError):
            compare_two_proportions(5, 10, 5, 10, confidence=0.0)

    def test_verify_trials_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            compare_two_proportions(5, 10, 5, 10, verify=True, verify_trials=10)

    def test_verify_permutation_budget_exceeded_raises(self):
        with self.assertRaises(ValueError):
            compare_two_proportions(600, 1000, 550, 1000, verify=True, verify_trials=500000)

    def test_verify_permutation_matches_hand_derived_exact_value_small_case(self):
        # Small enough (10 vs 10) to compute the true exact permutation
        # p-value by hand via the hypergeometric distribution, independent
        # of probkit's own simulation loop.
        exact = _exact_permutation_p_value(8, 10, 3, 10)
        result = compare_two_proportions(8, 10, 3, 10, verify=True, verify_trials=30000)
        sim = result["simulation"]
        assert_matches_simulation(self, sim["empirical_p_value"] * 30000, 30000, exact, sigma=6)

    def test_verify_unequal_sample_sizes(self):
        result = compare_two_proportions(9, 10, 40, 200, verify=True, verify_trials=5000)
        self.assertTrue(result["significant"])
        self.assertTrue(result["simulation"]["agrees_on_significance_call"])

    def test_verify_agrees_on_significance_call_for_a_clear_non_gap(self):
        result = compare_two_proportions(50, 100, 51, 100, verify=True, verify_trials=20000)
        self.assertFalse(result["significant"])
        self.assertTrue(result["simulation"]["agrees_on_significance_call"])


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

    def test_norm_ppf_matches_known_z_scores(self):
        # Standard textbook critical values for two-sided confidence levels.
        self.assertAlmostEqual(_norm_ppf(0.975), 1.959964, places=5)
        self.assertAlmostEqual(_norm_ppf(0.95), 1.644854, places=5)
        self.assertAlmostEqual(_norm_ppf(0.995), 2.575829, places=5)

    def test_norm_ppf_and_norm_cdf_are_inverses(self):
        for p in (0.001, 0.1, 0.5, 0.9, 0.999):
            self.assertAlmostEqual(_norm_cdf(_norm_ppf(p)), p, places=6)

    def test_norm_ppf_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            _norm_ppf(0.0)
        with self.assertRaises(ValueError):
            _norm_ppf(1.0)


if __name__ == "__main__":
    unittest.main()
