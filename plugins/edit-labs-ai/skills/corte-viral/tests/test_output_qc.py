from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.output_qc import parse_ass_layout, parse_blackdetect, parse_srt, parse_volumedetect, verify_caption_files


class OutputQcTests(unittest.TestCase):
    def test_parse_blackdetect(self) -> None:
        log = "[blackdetect] black_start:0 black_end:0.8 black_duration:0.8\n"
        self.assertEqual(parse_blackdetect(log), [{"start": 0.0, "end": 0.8, "duration": 0.8}])

    def test_parse_volumedetect(self) -> None:
        metrics = parse_volumedetect("mean_volume: -18.4 dB\nmax_volume: -1.0 dB")
        self.assertEqual(metrics["mean_volume_db"], -18.4)
        self.assertEqual(metrics["max_volume_db"], -1.0)

    def test_caption_structure_and_safe_zone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            srt = root / "captions.srt"
            ass = root / "captions.ass"
            srt.write_text(
                "1\n00:00:00,000 --> 00:00:01,500\nUma resposta rápida\n\n"
                "2\n00:00:01,550 --> 00:00:03,000\ncom contexto mínimo.\n\n",
                encoding="utf-8",
            )
            ass.write_text(
                "[Script Info]\nPlayResX: 1080\nPlayResY: 1920\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Default,Arial,68,&H00FFFFFF,&H00FFFFFF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,2,90,170,330,1\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,Uma resposta rápida\n",
                encoding="utf-8",
            )
            parsed_srt = parse_srt(srt)
            parsed_ass = parse_ass_layout(ass)
            self.assertEqual(parsed_srt["count"], 2)
            self.assertEqual(parsed_ass["marginv"], 330)
            result = verify_caption_files(
                srt,
                ass,
                media_duration=3.1,
                width=1080,
                height=1920,
                caption_cfg={"max_lines": 2, "safe_zone": {"left_px": 90, "right_px": 170, "bottom_px": 310}},
                qc_cfg={"captions_required": True, "verify_safe_zone": True},
            )
            self.assertTrue(result["valid"], result)

    def test_safe_zone_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            srt = root / "captions.srt"
            ass = root / "captions.ass"
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nTeste\n\n", encoding="utf-8")
            ass.write_text(
                "[Script Info]\nPlayResX: 1080\nPlayResY: 1920\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Default,Arial,68,&H00FFFFFF,&H00FFFFFF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,2,20,20,20,1\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Teste\n",
                encoding="utf-8",
            )
            result = verify_caption_files(
                srt,
                ass,
                media_duration=1.1,
                width=1080,
                height=1920,
                caption_cfg={"max_lines": 2, "safe_zone": {"left_px": 90, "right_px": 170, "bottom_px": 310}},
                qc_cfg={"captions_required": True, "verify_safe_zone": True},
            )
            self.assertFalse(result["valid"])
            self.assertIn("caption_bottom_outside_safe_zone", result["errors"])


if __name__ == "__main__":
    unittest.main()
