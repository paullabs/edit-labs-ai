from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.metrics import (
    highlight_repetition_ratio,
    pairwise_overlap,
    timeline_duration,
    validate_clip_timestamps,
)


class MetricTests(unittest.TestCase):
    def test_highlight_repetition_is_measured_against_body(self) -> None:
        clip = {
            "segments": [
                {"source_start": 10, "source_end": 20, "role": "highlight", "order": 1},
                {"source_start": 0, "source_end": 15, "role": "context", "order": 2},
            ]
        }
        self.assertAlmostEqual(highlight_repetition_ratio(clip), 0.5)
        self.assertEqual(timeline_duration(clip), 25.0)

    def test_pairwise_containment(self) -> None:
        clips = [
            {"id": "A", "segments": [{"source_start": 0, "source_end": 60}]},
            {"id": "B", "segments": [{"source_start": 40, "source_end": 60}]},
        ]
        result = pairwise_overlap(clips)[0]
        self.assertEqual(result["overlap_seconds"], 20.0)
        self.assertAlmostEqual(result["ratio_a"], 1 / 3, places=5)
        self.assertEqual(result["ratio_b"], 1.0)
        self.assertTrue(result["contained"])

    def test_timestamp_validation_detects_order_and_bounds(self) -> None:
        clip = {
            "segments": [
                {"source_start": 1, "source_end": 4, "order": 2},
                {"source_start": 4, "source_end": 12, "order": 1},
            ]
        }
        valid, errors = validate_clip_timestamps(clip, 10)
        self.assertFalse(valid)
        self.assertIn("segment_order_not_monotonic", errors)
        self.assertIn("segment_2_outside_media", errors)


if __name__ == "__main__":
    unittest.main()
