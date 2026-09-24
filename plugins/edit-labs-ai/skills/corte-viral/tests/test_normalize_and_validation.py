from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.normalize_transcript import normalize_transcript
from scripts.validation import validate_json_data


class NormalizeAndSchemaTests(unittest.TestCase):
    def test_normalize_srt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.srt"
            path.write_text(
                "1\n00:00:00,000 --> 00:00:01,500\nPrimeira frase.\n\n"
                "2\n00:00:01,500 --> 00:00:03,000\nSegunda frase.\n",
                encoding="utf-8",
            )
            result = normalize_transcript(path)
            self.assertEqual(len(result["segments"]), 2)
            self.assertEqual(result["duration_seconds"], 3.0)

    def test_normalize_youtube_json3_without_rolling_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.json3"
            path.write_text(
                json.dumps({
                    "events": [
                        {"tStartMs": 0, "dDurationMs": 5000},
                        {
                            "tStartMs": 1000,
                            "dDurationMs": 2500,
                            "segs": [
                                {"utf8": ">> O", "isSpeakerChange": 1},
                                {"utf8": " produto", "tOffsetMs": 300},
                                {"utf8": " ficou", "tOffsetMs": 800},
                            ],
                        },
                        {
                            "tStartMs": 2500,
                            "dDurationMs": 2000,
                            "segs": [
                                {"utf8": "mais"},
                                {"utf8": " simples.", "tOffsetMs": 400},
                            ],
                        },
                    ]
                }),
                encoding="utf-8",
            )
            result = normalize_transcript(path)
            self.assertEqual([item["text"] for item in result["segments"]], [
                "O produto ficou",
                "mais simples.",
            ])
            self.assertEqual(result["segments"][0]["speaker"], "SPEAKER_02")
            self.assertEqual(result["duration_seconds"], 5.0)
            self.assertTrue(result["segments"][0]["words"])

    def test_valid_candidate_fixture_matches_schema(self) -> None:
        data = {
            "schema_version": "1.0",
            "clips": [
                {
                    "id": "clip-001",
                    "title": "Resposta direta",
                    "status": "REBUILD",
                    "primary_context": "resposta-rapida",
                    "profile": "fast_answer",
                    "segments": [
                        {"source_start": 0.0, "source_end": 3.0, "role": "hook", "order": 1}
                    ],
                    "scores": {},
                    "hard_fails": [],
                }
            ],
        }
        self.assertEqual(validate_json_data(data, "clip-candidates.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
