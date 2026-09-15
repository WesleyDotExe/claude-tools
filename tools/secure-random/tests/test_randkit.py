"""Tests aimed at: dice-notation parsing/validation, CSPRNG output staying in
range, the hand-rolled chi-square machinery being numerically correct (checked
against textbook critical values), and that machinery actually catching a
biased distribution -- not just passing a real one. Run:
python3 -m unittest discover -s tests -v
"""
import math
import sys
import unittest
import uuid as uuid_module
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from randkit import (  # noqa: E402
    _chi_square_fit,
    _chi_square_uniform,
    chi2_sf,
    flip_coins,
    generate_password,
    generate_token,
    generate_uuid4,
    pick_random,
    random_floats,
    random_integers,
    roll_dice,
    shuffle_list,
    verify_uniformity,
    verify_weighted_distribution,
)


class RollDiceTests(unittest.TestCase):
    def test_standard_notation(self):
        result = roll_dice("2d6")
        self.assertEqual(len(result["rolls"]), 2)
        self.assertTrue(all(1 <= r <= 6 for r in result["rolls"]))
        self.assertEqual(result["total"], sum(result["rolls"]))

    def test_implicit_count_of_one(self):
        result = roll_dice("d20")
        self.assertEqual(len(result["rolls"]), 1)
        self.assertTrue(1 <= result["rolls"][0] <= 20)

    def test_modifier_applied_to_total_not_rolls(self):
        result = roll_dice("3d8+2")
        self.assertTrue(all(1 <= r <= 8 for r in result["rolls"]))
        self.assertEqual(result["total"], sum(result["rolls"]) + 2)

    def test_negative_modifier(self):
        result = roll_dice("1d100-5")
        self.assertEqual(result["total"], result["rolls"][0] - 5)

    def test_invalid_notation_raises(self):
        for bad in ["", "6", "2x6", "d", "6d", "2d6*3"]:
            with self.assertRaises(ValueError):
                roll_dice(bad)

    def test_sides_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            roll_dice("1d1")


class RandomIntegersTests(unittest.TestCase):
    def test_inclusive_bounds_respected(self):
        values = random_integers(1, 6, count=500)
        self.assertEqual(len(values), 500)
        self.assertTrue(all(1 <= v <= 6 for v in values))
        # With 500 draws over 6 values, seeing every face is overwhelmingly
        # likely for a working uniform generator (this is not a strict
        # statistical test -- verify_uniformity below is).
        self.assertEqual(set(values), {1, 2, 3, 4, 5, 6})

    def test_single_value_range(self):
        self.assertEqual(random_integers(4, 4, count=5), [4, 4, 4, 4, 4])

    def test_low_greater_than_high_raises(self):
        with self.assertRaises(ValueError):
            random_integers(10, 1)


class RandomFloatsTests(unittest.TestCase):
    def test_bounds_respected(self):
        values = random_floats(2.0, 3.0, count=200)
        self.assertTrue(all(2.0 <= v < 3.0 for v in values))

    def test_default_unit_interval(self):
        values = random_floats(count=200)
        self.assertTrue(all(0.0 <= v < 1.0 for v in values))


class FlipCoinsTests(unittest.TestCase):
    def test_only_heads_or_tails(self):
        result = flip_coins(count=300)
        self.assertEqual(result["heads"] + result["tails"], 300)
        self.assertTrue(set(result["results"]) <= {"heads", "tails"})
        self.assertEqual(result["heads"], result["results"].count("heads"))


class ShuffleAndPickTests(unittest.TestCase):
    def test_shuffle_is_a_permutation_and_does_not_mutate_input(self):
        original = list(range(20))
        shuffled = shuffle_list(original)
        self.assertEqual(sorted(shuffled), original)
        self.assertEqual(original, list(range(20)))  # untouched

    def test_shuffle_actually_reorders_over_many_trials(self):
        original = list(range(10))
        # Probability every one of 20 independent shuffles matches identity
        # is (1/10!)^20 -- not a real risk of flakiness.
        self.assertTrue(any(shuffle_list(original) != original for _ in range(20)))

    def test_pick_unique_has_no_repeats_and_right_count(self):
        picked = pick_random(list(range(50)), count=10, unique=True)
        self.assertEqual(len(picked), len(set(picked)))
        self.assertEqual(len(picked), 10)

    def test_pick_unique_count_too_large_raises(self):
        with self.assertRaises(ValueError):
            pick_random([1, 2, 3], count=4, unique=True)

    def test_pick_with_replacement_can_repeat(self):
        # Not deterministic, but over 200 draws from 2 items with replacement,
        # getting each item at least once is essentially certain.
        picked = pick_random(["a", "b"], count=200, unique=False)
        self.assertEqual(len(picked), 200)
        self.assertEqual(set(picked), {"a", "b"})

    def test_empty_items_raises(self):
        with self.assertRaises(ValueError):
            pick_random([], count=1)

    def test_weighted_pick_favors_heavy_item_over_many_trials(self):
        # 1000:1:1 weighting -- "a" should dominate, but "b"/"c" must still
        # be reachable (probability zero only for an actual zero weight).
        results = [
            pick_random(["a", "b", "c"], count=1, unique=False, weights=[1000, 1, 1])[0]
            for _ in range(500)
        ]
        self.assertGreater(results.count("a"), 480)

    def test_weighted_pick_never_returns_a_zero_weight_item(self):
        for _ in range(200):
            picked = pick_random(["a", "b"], count=1, unique=False, weights=[1, 0])
            self.assertEqual(picked, ["a"])

    def test_weighted_unique_pick_has_no_repeats_and_right_count(self):
        picked = pick_random(list(range(10)), count=5, unique=True, weights=list(range(1, 11)))
        self.assertEqual(len(picked), 5)
        self.assertEqual(len(picked), len(set(picked)))

    def test_weighted_pick_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            pick_random(["a", "b"], count=1, weights=[1, 2, 3])

    def test_weighted_pick_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            pick_random(["a", "b"], count=1, weights=[1, -1])

    def test_weighted_pick_all_zero_weights_raises(self):
        with self.assertRaises(ValueError):
            pick_random(["a", "b"], count=1, weights=[0, 0])


class GeneratePasswordTests(unittest.TestCase):
    def test_length_and_entropy(self):
        result = generate_password(length=20)
        self.assertEqual(len(result["password"]), 20)
        self.assertEqual(result["length"], 20)
        self.assertAlmostEqual(
            result["entropy_bits"], 20 * math.log2(result["alphabet_size"]), places=1
        )

    def test_every_enabled_class_is_represented_over_many_generations(self):
        # A single 16-char password could plausibly lack a class by chance if
        # it weren't guaranteed; generate_password guarantees it every time.
        for _ in range(50):
            pw = generate_password(length=16)["password"]
            self.assertTrue(any(c.islower() for c in pw))
            self.assertTrue(any(c.isupper() for c in pw))
            self.assertTrue(any(c.isdigit() for c in pw))
            self.assertTrue(any(not c.isalnum() for c in pw))

    def test_length_shorter_than_class_count_raises(self):
        with self.assertRaises(ValueError):
            generate_password(length=2, use_upper=True, use_lower=True, use_digits=True, use_symbols=True)

    def test_no_classes_enabled_raises(self):
        with self.assertRaises(ValueError):
            generate_password(use_upper=False, use_lower=False, use_digits=False, use_symbols=False)

    def test_exclude_ambiguous_removes_confusable_chars(self):
        for _ in range(50):
            pw = generate_password(length=16, exclude_ambiguous=True)["password"]
            self.assertFalse(set(pw) & {"I", "l", "1", "O", "0"})


class GenerateTokenAndUuidTests(unittest.TestCase):
    def test_hex_token_length(self):
        token = generate_token(nbytes=16, encoding="hex")
        self.assertEqual(len(token), 32)
        int(token, 16)  # raises if not valid hex

    def test_urlsafe_token_is_nonempty_and_url_safe(self):
        token = generate_token(nbytes=16, encoding="urlsafe")
        self.assertTrue(token)
        self.assertTrue(set(token) <= set(string_urlsafe_alphabet()))

    def test_bad_encoding_raises(self):
        with self.assertRaises(ValueError):
            generate_token(encoding="base64")

    def test_uuid4_is_well_formed_version_4(self):
        value = generate_uuid4()
        parsed = uuid_module.UUID(value)
        self.assertEqual(parsed.version, 4)


def string_urlsafe_alphabet():
    import string as _s

    return _s.ascii_letters + _s.digits + "-_"


class Chi2SfAgainstTextbookCriticalValuesTests(unittest.TestCase):
    # (df, x, expected p) from a standard chi-square table.
    CASES = [
        (1, 3.841, 0.05),
        (1, 6.635, 0.01),
        (2, 5.991, 0.05),
        (5, 11.070, 0.05),
        (10, 18.307, 0.05),
        (10, 23.209, 0.01),
    ]

    def test_matches_textbook_critical_values(self):
        for df, x, expected_p in self.CASES:
            with self.subTest(df=df, x=x):
                self.assertAlmostEqual(chi2_sf(x, df), expected_p, delta=0.001)

    def test_zero_statistic_is_p_one(self):
        self.assertEqual(chi2_sf(0, 5), 1.0)


class ChiSquareUniformTests(unittest.TestCase):
    def test_perfectly_uniform_counts_give_p_near_one(self):
        chi2, df, p = _chi_square_uniform([100] * 10)
        self.assertEqual(chi2, 0.0)
        self.assertEqual(df, 9)
        self.assertEqual(p, 1.0)

    def test_strongly_biased_counts_are_flagged(self):
        # Mimics the documented "asks for 1-50, always says 27" failure mode:
        # bucket 27 (index 26) takes 90% of 10000 draws that should be spread
        # evenly over 50 buckets.
        counts = [100] * 50
        counts[26] += 5000
        chi2, df, p = _chi_square_uniform(counts)
        self.assertEqual(sum(counts), 10000)
        self.assertLess(p, 1e-10)


class ChiSquareFitTests(unittest.TestCase):
    def test_uniform_is_a_special_case_of_fit(self):
        # _chi_square_uniform([100]*10) should equal _chi_square_fit against
        # a flat expected distribution built by hand.
        counts = [80, 95, 110, 105, 90, 120, 100, 95, 105, 100]
        expected = [100.0] * 10
        self.assertEqual(_chi_square_fit(counts, expected), _chi_square_uniform(counts))

    def test_exact_match_to_non_uniform_expected_gives_p_one(self):
        chi2, df, p = _chi_square_fit([400, 400, 200], [400.0, 400.0, 200.0])
        self.assertEqual(chi2, 0.0)
        self.assertEqual(df, 2)
        self.assertEqual(p, 1.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            _chi_square_fit([1, 2], [1.0, 2.0, 3.0])


class VerifyWeightedDistributionTests(unittest.TestCase):
    def test_real_csprng_draws_match_requested_weights(self):
        # Loose threshold, same rationale as the uniformity integration test:
        # this only fails if the weighted-draw machinery is actually broken.
        result = verify_weighted_distribution([1, 2, 7], samples=60000)
        self.assertGreater(result["p_value"], 1e-6)
        self.assertEqual(result["buckets"], 3)
        for observed, expected in zip(result["observed_shares"], result["expected_shares"]):
            self.assertAlmostEqual(observed, expected, delta=0.02)

    def test_too_few_weights_raises(self):
        with self.assertRaises(ValueError):
            verify_weighted_distribution([1])

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            verify_weighted_distribution([1, 0], samples=1000)

    def test_too_few_samples_for_buckets_raises(self):
        with self.assertRaises(ValueError):
            verify_weighted_distribution([1, 1, 1], samples=5)


class VerifyUniformityIntegrationTests(unittest.TestCase):
    def test_real_csprng_draws_pass_as_uniform(self):
        # Real secrets-backed draws, not a synthetic histogram. Threshold is
        # deliberately loose (this would only fail if the CSPRNG were
        # actually broken, not from ordinary sampling noise).
        result = verify_uniformity(1, 6, samples=60000)
        self.assertGreater(result["p_value"], 1e-6)
        self.assertEqual(result["buckets"], 6)
        self.assertAlmostEqual(
            result["most_sampled_share"], result["expected_share"], delta=0.02
        )

    def test_too_few_samples_for_buckets_raises(self):
        with self.assertRaises(ValueError):
            verify_uniformity(1, 50, samples=10)

    def test_low_not_less_than_high_raises(self):
        with self.assertRaises(ValueError):
            verify_uniformity(5, 5, samples=1000)


if __name__ == "__main__":
    unittest.main()
