from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validation import validate_run_artifacts
from scripts.vch import config


class ConfigAndModeTests(unittest.TestCase):
    def _run(self, mode: str, platform: str = "tiktok"):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "00-manifest.json").write_text(json.dumps({
            "schema_version": "1.0",
            "run_id": "test",
            "created_at": "1970-01-01T00:00:00+00:00",
            "mode": mode,
            "status": "initialized",
            "inputs": {"platform": platform},
            "stages": {},
        }), encoding="utf-8")
        return temp, root

    def test_platform_config_is_loaded_from_manifest(self) -> None:
        temp, run = self._run("analyze", "tiktok")
        try:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("VCH_PLATFORM", None)
                os.environ.pop("VCH_CONFIG", None)
                cfg = config(run)
            self.assertEqual(cfg["selected_platform"], "tiktok")
            self.assertEqual(cfg["captions"]["safe_zone"]["right_px"], 190)
        finally:
            temp.cleanup()

    def test_override_config_wins_after_platform_overlay(self) -> None:
        temp, run = self._run("full", "instagram-reels")
        try:
            smoke = Path(__file__).resolve().parents[1] / "config" / "testing" / "smoke.yaml"
            with patch.dict(os.environ, {"VCH_CONFIG": str(smoke)}, clear=False):
                cfg = config(run)
            self.assertEqual(cfg["render"]["width"], 360)
            self.assertEqual(cfg["render"]["height"], 640)
            self.assertEqual(cfg["selected_platform"], "instagram-reels")
        finally:
            temp.cleanup()

    def test_analysis_mode_does_not_require_post_render_report(self) -> None:
        temp, run = self._run("analyze")
        try:
            result = validate_run_artifacts(run)
            names = {item["file"] for item in result["files"]}
            self.assertNotIn("16-output-verification.json", names)
        finally:
            temp.cleanup()

    def test_full_mode_requires_post_render_report(self) -> None:
        temp, run = self._run("full")
        try:
            result = validate_run_artifacts(run)
            names = {item["file"] for item in result["files"]}
            self.assertIn("16-output-verification.json", names)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
