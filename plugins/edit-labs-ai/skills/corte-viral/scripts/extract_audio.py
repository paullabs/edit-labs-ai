from __future__ import annotations

from pathlib import Path

from scripts.utils import HarnessError, run_command, which


def extract_analysis_audio(video_path: str | Path, output_path: str | Path) -> Path:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise HarnessError("FFmpeg não encontrado")
    source = Path(video_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output)
    ])
    return output
