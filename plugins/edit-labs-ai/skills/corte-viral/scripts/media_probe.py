from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from scripts.utils import HarnessError, run_command, which


def _ratio_to_float(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def probe_media(path: str | Path) -> dict[str, Any]:
    media = Path(path).expanduser().resolve()
    if not media.exists():
        raise HarnessError(f"Mídia não encontrada: {media}")
    ffprobe = which("ffprobe")
    if not ffprobe:
        raise HarnessError("FFprobe não encontrado")
    result = run_command([
        ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(media)
    ])
    raw = json.loads(result.stdout or "{}")
    streams = raw.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    duration_values = []
    for source in [raw.get("format", {}), *(streams or [])]:
        try:
            duration_values.append(float(source.get("duration")))
        except (TypeError, ValueError):
            pass
    duration = max(duration_values) if duration_values else None
    rotation = 0
    if video_stream:
        tags = video_stream.get("tags", {})
        side_data = video_stream.get("side_data_list", [])
        try:
            rotation = int(tags.get("rotate", 0))
        except (TypeError, ValueError):
            rotation = 0
        for item in side_data:
            if "rotation" in item:
                try:
                    rotation = int(item["rotation"])
                except (TypeError, ValueError):
                    pass
    return {
        "schema_version": "1.0",
        "path": str(media),
        "filename": media.name,
        "size_bytes": media.stat().st_size,
        "duration_seconds": duration,
        "format_name": raw.get("format", {}).get("format_name"),
        "format_long_name": raw.get("format", {}).get("format_long_name"),
        "video": None if not video_stream else {
            "codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": _ratio_to_float(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
            "pixel_format": video_stream.get("pix_fmt"),
            "rotation": rotation,
            "time_base": video_stream.get("time_base"),
        },
        "audio": [{
            "codec": stream.get("codec_name"),
            "channels": stream.get("channels"),
            "channel_layout": stream.get("channel_layout"),
            "sample_rate": int(stream["sample_rate"]) if str(stream.get("sample_rate", "")).isdigit() else None,
            "bit_rate": int(stream["bit_rate"]) if str(stream.get("bit_rate", "")).isdigit() else None,
        } for stream in audio_streams],
        "raw_stream_count": len(streams),
    }
