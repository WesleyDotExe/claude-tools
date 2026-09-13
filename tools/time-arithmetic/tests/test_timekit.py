"""Tests aimed squarely at the failure modes the search turned up:
DST spring-forward/fall-back, leap-year/month-rollover clamping, and
cross-timezone elapsed time. Run: python3 -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from timekit import add_delta, convert, day_info, diff, find_timezones  # noqa: E402


class ConvertTests(unittest.TestCase):
    def test_new_york_to_london_summer(self):
        result = convert("2026-07-04T09:00", "America/New_York", "Europe/London")
        self.assertEqual(result["output"]["iso"][:19], "2026-07-04T14:00:00")
        self.assertTrue(result["input"]["is_dst"])

    def test_unknown_timezone_raises(self):
        with self.assertRaises(ValueError):
            convert("2026-01-01T00:00", "Mars/Colony_One", "UTC")


class AddDeltaDSTTests(unittest.TestCase):
    def test_spring_forward_skips_the_missing_hour(self):
        # 2026-03-08 01:30 US/Eastern + 1 hour must land at 03:30, not 02:30
        # (02:30 does not exist that night).
        result = add_delta("2026-03-08T01:30", "America/New_York", hours=1)
        self.assertEqual(result["output"]["iso"][:16], "2026-03-08T03:30")
        self.assertFalse(result["input"]["is_dst"])
        self.assertTrue(result["output"]["is_dst"])

    def test_calendar_day_add_preserves_wall_clock_across_fall_back(self):
        # "+1 day" is calendar semantics ("same time tomorrow"), so it must
        # land on 12:00 the next day even though the intervening night has
        # 25 real hours in it because of the 2026-11-01 fall-back.
        result = add_delta("2026-10-31T12:00", "America/New_York", days=1)
        self.assertEqual(result["output"]["iso"][:16], "2026-11-01T12:00")
        self.assertTrue(result["input"]["is_dst"])
        self.assertFalse(result["output"]["is_dst"])

    def test_hour_add_is_real_elapsed_time_across_fall_back(self):
        # "+1 hour" is clock/elapsed semantics: 01:30 EDT is followed by a
        # repeated 01:30 EST an hour later (the fall-back fold), not 02:30.
        result = add_delta("2026-11-01T01:30", "America/New_York", hours=1)
        self.assertEqual(result["output"]["iso"][:16], "2026-11-01T01:30")
        self.assertTrue(result["input"]["is_dst"])
        self.assertFalse(result["output"]["is_dst"])


class AddDeltaCalendarTests(unittest.TestCase):
    def test_month_end_clamps_instead_of_overflowing(self):
        # Jan 31 + 1 month must be Feb 28 (2026 is not a leap year),
        # not an exception and not "March 3".
        result = add_delta("2026-01-31T09:00", "UTC", months=1)
        self.assertEqual(result["output"]["date"] if "date" in result["output"] else result["output"]["iso"][:10], "2026-02-28")

    def test_leap_day_plus_one_year_clamps(self):
        result = add_delta("2024-02-29T09:00", "UTC", years=1)
        self.assertEqual(result["output"]["iso"][:10], "2025-02-28")


class DiffTests(unittest.TestCase):
    def test_same_wall_clock_different_zones_is_not_zero(self):
        # 09:00 in Los Angeles and 09:00 in Berlin on the same date are
        # NOT simultaneous; the naive "same time" reading is the classic bug.
        result = diff("2026-06-15T09:00", "America/Los_Angeles", "2026-06-15T09:00", "Europe/Berlin")
        # LA is UTC-7 in June, Berlin is UTC+2 -> 9 hours apart.
        self.assertAlmostEqual(abs(result["total_seconds"]), 9 * 3600, delta=1)

    def test_negative_diff_is_signed(self):
        result = diff("2026-06-15T12:00", "UTC", "2026-06-15T10:00", "UTC")
        self.assertTrue(result["human"].startswith("-"))


class DayInfoTests(unittest.TestCase):
    def test_leap_year_detection(self):
        self.assertTrue(day_info("2024-02-01")["is_leap_year"])
        self.assertFalse(day_info("2026-02-01")["is_leap_year"])

    def test_days_in_month(self):
        self.assertEqual(day_info("2026-02-01")["days_in_month"], 28)
        self.assertEqual(day_info("2024-02-01")["days_in_month"], 29)


class FindTimezonesTests(unittest.TestCase):
    def test_finds_known_city(self):
        self.assertIn("Europe/Berlin", find_timezones("berlin"))

    def test_no_match_is_empty_list(self):
        self.assertEqual(find_timezones("not_a_real_place_xyz"), [])


if __name__ == "__main__":
    unittest.main()
