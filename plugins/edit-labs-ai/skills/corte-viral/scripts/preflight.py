from __future__ import annotations

import importlib.util
import platform
import re
import sys
from typing import Any

from scripts.utils import PROJECT_ROOT, run_command, which


def run_preflight() -> dict[str, Any]:
    python_ok = sys.version_info >= (3, 10)
    ffmpeg = which("ffmpeg")
    ffprobe = which("ffprobe")
    dependencies = {
        "yaml": importlib.util.find_spec("yaml") is not None,
        "jsonschema": importlib.util.find_spec("jsonschema") is not None,
        "PIL": importlib.util.find_spec("PIL") is not None,
        "faster_whisper": importlib.util.find_spec("faster_whisper") is not None,
    }
    ffmpeg_filters = ""
    subtitles_filter = False
    if ffmpeg:
        result = run_command([ffmpeg, "-hide_banner", "-filters"], check=False)
        ffmpeg_filters = (result.stdout or "") + (result.stderr or "")
        # Checagem por palavra inteira: "ass" como substring casa com lowpass,
        # highpass, bass, allpass e bandpass, gerando falso positivo.
        subtitles_filter = bool(
            re.search(r"^\s*\S*\s+(subtitles|ass)\s", ffmpeg_filters, re.MULTILINE)
        )
    schemas = list((PROJECT_ROOT / "schemas").glob("*.json"))
    return {
        "python": {
            "ok": python_ok,
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "ffmpeg": {"ok": bool(ffmpeg), "path": ffmpeg, "subtitles_filter": subtitles_filter},
        "ffprobe": {"ok": bool(ffprobe), "path": ffprobe},
        "dependencies": dependencies,
        "schemas_found": len(schemas),
        "ready_for_analysis": python_ok and dependencies["yaml"] and dependencies["jsonschema"],
        "ready_for_render": python_ok and bool(ffmpeg) and bool(ffprobe),
        "ready_for_auto_transcription": dependencies["faster_whisper"],
    }


def print_preflight(report: dict[str, Any]) -> None:
    def flag(ok: bool) -> str:
        return "OK" if ok else "AUSENTE"

    print(f"Python {report['python']['version']}: {flag(report['python']['ok'])}")
    print(f"FFmpeg: {flag(report['ffmpeg']['ok'])}")
    print(f"FFprobe: {flag(report['ffprobe']['ok'])}")
    print(f"Filtro ASS/subtitles: {flag(report['ffmpeg']['subtitles_filter'])}")
    for name, ok in report["dependencies"].items():
        optional = " (opcional)" if name == "faster_whisper" else ""
        print(f"Python {name}{optional}: {flag(ok)}")
    print(f"Schemas encontrados: {report['schemas_found']}")
    print(f"Análise: {flag(report['ready_for_analysis'])}")
    print(f"Render: {flag(report['ready_for_render'])}")
    print(f"Transcrição automática: {flag(report['ready_for_auto_transcription'])}")
