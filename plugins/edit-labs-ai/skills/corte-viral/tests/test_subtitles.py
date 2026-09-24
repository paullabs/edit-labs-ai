from __future__ import annotations

import unittest

from scripts.subtitles import chunk_tokens, map_transcript_to_timeline


class SubtitleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transcript = {
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 4.0,
                    "text": "A resposta vem primeiro porque reduz o esforço.",
                    "words": [
                        {"word": "A", "start": 0.0, "end": 0.2},
                        {"word": "resposta", "start": 0.2, "end": 0.8},
                        {"word": "vem", "start": 0.8, "end": 1.1},
                        {"word": "primeiro", "start": 1.1, "end": 1.7},
                        {"word": "porque", "start": 1.7, "end": 2.2},
                        {"word": "reduz", "start": 2.2, "end": 2.7},
                        {"word": "o", "start": 2.7, "end": 2.9},
                        {"word": "esforço.", "start": 2.9, "end": 3.7},
                    ],
                },
                {
                    "id": 1,
                    "start": 5.0,
                    "end": 7.0,
                    "text": "Depois vem a prova.",
                    "words": [
                        {"word": "Depois", "start": 5.0, "end": 5.5},
                        {"word": "vem", "start": 5.5, "end": 5.8},
                        {"word": "a", "start": 5.8, "end": 6.0},
                        {"word": "prova.", "start": 6.0, "end": 6.8},
                    ],
                },
            ]
        }

    def test_map_discontinuous_source_to_continuous_output(self) -> None:
        timeline = [
            {"source_start": 5.0, "source_end": 7.0, "order": 1},
            {"source_start": 0.0, "source_end": 2.0, "order": 2},
        ]
        tokens = map_transcript_to_timeline(self.transcript, timeline)
        self.assertEqual(tokens[0].text, "Depois")
        self.assertAlmostEqual(tokens[0].start, 0.0)
        first_second_segment = next(token for token in tokens if token.text == "A")
        self.assertAlmostEqual(first_second_segment.start, 2.0)

    def test_chunking_respects_limits(self) -> None:
        timeline = [{"source_start": 0.0, "source_end": 4.0, "order": 1}]
        tokens = map_transcript_to_timeline(self.transcript, timeline)
        captions = chunk_tokens(tokens, min_words=2, max_words=5, target_max_duration=2.0)
        self.assertGreaterEqual(len(captions), 2)
        self.assertTrue(all(len(caption.words) <= 5 for caption in captions))
        self.assertTrue(all(caption.end > caption.start for caption in captions))


if __name__ == "__main__":
    unittest.main()
