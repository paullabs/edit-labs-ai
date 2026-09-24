from __future__ import annotations

import unittest

from scripts.utils import (
    format_timecode,
    intervals_duration,
    intervals_intersection_duration,
    normalize_intervals,
    parse_timecode,
    slugify,
)


class TimecodeTests(unittest.TestCase):
    def test_parse_supported_formats(self) -> None:
        self.assertAlmostEqual(parse_timecode("01:02:03.500"), 3723.5)
        self.assertAlmostEqual(parse_timecode("02:03,250"), 123.25)
        self.assertAlmostEqual(parse_timecode(4.5), 4.5)

    def test_parse_rejects_invalid_values(self) -> None:
        for value in ["00:60:00", "00:00:60", "-1", "abc"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_timecode(value)

    def test_format_carries_into_next_minute_and_hour(self) -> None:
        self.assertEqual(format_timecode(59.9996, srt=True), "00:01:00,000")
        self.assertEqual(format_timecode(3599.9996), "01:00:00.000")
        self.assertEqual(format_timecode(1.2344), "00:00:01.234")


class IntervalTests(unittest.TestCase):
    def test_normalization_and_duration(self) -> None:
        intervals = [(0, 3), (2, 5), (8, 10), (10, 12), (7, 7)]
        self.assertEqual(normalize_intervals(intervals), [(0.0, 5.0), (8.0, 12.0)])
        self.assertEqual(intervals_duration(intervals), 9.0)

    def test_intersection(self) -> None:
        self.assertAlmostEqual(
            intervals_intersection_duration([(0, 10), (20, 30)], [(5, 12), (25, 40)]),
            10.0,
        )

    def test_slugify(self) -> None:
        self.assertEqual(slugify("Preço: R$ 9 Mil"), "preco-r-9-mil")


if __name__ == "__main__":
    unittest.main()
