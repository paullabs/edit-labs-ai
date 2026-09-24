from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.media_probe import probe_media
from scripts.utils import HarnessError, parse_timecode, run_command, which

BLACK_RE = re.compile(
    r"black_start:(?P<start>[0-9.]+)\s+black_end:(?P<end>[0-9.]+)\s+black_duration:(?P<duration>[0-9.]+)"
)
MEAN_VOLUME_RE = re.compile(r"mean_volume:\s*(-?(?:inf|[0-9.]+))\s*dB", re.IGNORECASE)
MAX_VOLUME_RE = re.compile(r"max_volume:\s*(-?(?:inf|[0-9.]+))\s*dB", re.IGNORECASE)
SRT_TIME_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
)


def parse_blackdetect(log: str) -> list[dict[str, float]]:
    intervals = []
    for match in BLACK_RE.finditer(log or ""):
        intervals.append({
            "start": float(match.group("start")),
            "end": float(match.group("end")),
            "duration": float(match.group("duration")),
        })
    return intervals


def parse_volumedetect(log: str) -> dict[str, float | None]:
    def value(pattern: re.Pattern[str]) -> float | None:
        match = pattern.search(log or "")
        if not match:
            return None
        raw = match.group(1).lower()
        if raw in {"-inf", "inf"}:
            return float("-inf") if raw == "-inf" else float("inf")
        return float(raw)

    return {"mean_volume_db": value(MEAN_VOLUME_RE), "max_volume_db": value(MAX_VOLUME_RE)}


def analyze_black_frames(path: str | Path, *, min_duration: float = 0.15, pixel_threshold: float = 0.10) -> list[dict[str, float]]:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise HarnessError("FFmpeg não encontrado")
    result = run_command([
        ffmpeg, "-hide_banner", "-loglevel", "info", "-i", str(path),
        "-vf", f"blackdetect=d={float(min_duration):.3f}:pix_th={float(pixel_threshold):.3f}",
        "-an", "-f", "null", "-",
    ], check=False)
    return parse_blackdetect((result.stderr or "") + "\n" + (result.stdout or ""))


def analyze_audio(path: str | Path) -> dict[str, float | None]:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise HarnessError("FFmpeg não encontrado")
    result = run_command([
        ffmpeg, "-hide_banner", "-loglevel", "info", "-i", str(path),
        "-vn", "-af", "volumedetect", "-f", "null", "-",
    ], check=False)
    return parse_volumedetect((result.stderr or "") + "\n" + (result.stdout or ""))


def parse_srt(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {"count": 0, "entries": [], "errors": ["srt_missing"]}
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    entries = []
    errors: list[str] = []
    for match in SRT_TIME_RE.finditer(text):
        try:
            start = parse_timecode(match.group("start"))
            end = parse_timecode(match.group("end"))
        except ValueError:
            errors.append("srt_timestamp_invalid")
            continue
        if end <= start:
            errors.append("srt_non_positive_duration")
        # Capture text until the next blank line. This is enough for structural QC.
        tail = text[match.end():]
        block = re.split(r"\r?\n\s*\r?\n", tail, maxsplit=1)[0]
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        entries.append({"start": start, "end": end, "lines": lines})
    if not entries and text.strip():
        errors.append("srt_has_no_timed_entries")
    previous_end = -1.0
    for entry in entries:
        if entry["start"] + 0.001 < previous_end:
            errors.append("srt_entries_overlap_or_out_of_order")
        previous_end = max(previous_end, entry["end"])
    return {"count": len(entries), "entries": entries, "errors": sorted(set(errors))}


def parse_ass_layout(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {"errors": ["ass_missing"]}
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    result: dict[str, Any] = {"errors": []}
    for key in ("PlayResX", "PlayResY"):
        match = re.search(rf"^{key}:\s*(\d+)\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
        result[key.lower()] = int(match.group(1)) if match else None
    format_match = re.search(r"^Format:\s*(.+)$", text, flags=re.MULTILINE | re.IGNORECASE)
    style_match = re.search(r"^Style:\s*(.+)$", text, flags=re.MULTILINE | re.IGNORECASE)
    if not format_match or not style_match:
        result["errors"].append("ass_style_missing")
        return result
    fields = [part.strip().lower() for part in format_match.group(1).split(",")]
    # The first Style format line in generated ASS is the style schema. If a later
    # event Format line was matched, fall back to the canonical field order.
    if "marginl" not in fields or "alignment" not in fields:
        style_format = re.search(r"\[V4\+ Styles\].*?^Format:\s*(.+)$", text, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
        if style_format:
            fields = [part.strip().lower() for part in style_format.group(1).split(",")]
    values = [part.strip() for part in style_match.group(1).split(",")]
    style = {field: values[index] for index, field in enumerate(fields) if index < len(values)}
    for field in ("marginl", "marginr", "marginv", "alignment", "fontsize"):
        try:
            result[field] = int(float(style[field])) if field in style else None
        except (TypeError, ValueError):
            result[field] = None
    dialogue_count = len(re.findall(r"^Dialogue:", text, flags=re.MULTILINE | re.IGNORECASE))
    result["dialogue_count"] = dialogue_count
    return result


def verify_caption_files(
    srt_path: str | Path,
    ass_path: str | Path,
    *,
    media_duration: float,
    width: int,
    height: int,
    caption_cfg: dict[str, Any],
    qc_cfg: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    srt = parse_srt(srt_path)
    ass = parse_ass_layout(ass_path)
    errors.extend(srt.get("errors", []))
    errors.extend(ass.get("errors", []))
    captions_required = bool(qc_cfg.get("captions_required", True))
    if captions_required and srt.get("count", 0) <= 0:
        errors.append("captions_empty")
    if captions_required and int(ass.get("dialogue_count") or 0) <= 0:
        errors.append("ass_dialogue_empty")
    tolerance = float(qc_cfg.get("caption_end_tolerance_seconds", 0.30))
    entries = srt.get("entries", [])
    if entries:
        if max(entry["end"] for entry in entries) > media_duration + tolerance:
            errors.append("caption_ends_after_media")
        if min(entry["start"] for entry in entries) < -0.001:
            errors.append("caption_starts_before_zero")
        max_lines = int(caption_cfg.get("max_lines", 2))
        if any(len(entry.get("lines", [])) > max_lines for entry in entries):
            errors.append("caption_exceeds_max_lines")
    if ass.get("playresx") not in {None, width} or ass.get("playresy") not in {None, height}:
        errors.append("ass_resolution_mismatch")
    if bool(qc_cfg.get("verify_safe_zone", True)):
        safe = caption_cfg.get("safe_zone", {})
        scale = min(width / 1080.0, height / 1920.0) if bool(caption_cfg.get("scale_style_to_render", True)) else 1.0
        expected_left = round(int(safe.get("left_px", 0)) * scale)
        expected_right = round(int(safe.get("right_px", 0)) * scale)
        expected_bottom = round(int(safe.get("bottom_px", 0)) * scale)
        if ass.get("marginl") is not None and ass["marginl"] < expected_left:
            errors.append("caption_left_outside_safe_zone")
        if ass.get("marginr") is not None and ass["marginr"] < expected_right:
            errors.append("caption_right_outside_safe_zone")
        alignment = ass.get("alignment")
        if alignment in {1, 2, 3} and ass.get("marginv") is not None and ass["marginv"] < expected_bottom:
            errors.append("caption_bottom_outside_safe_zone")
        if alignment not in {1, 2, 3, 4, 5, 6, 7, 8, 9, None}:
            warnings.append("caption_alignment_unknown")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "srt_count": srt.get("count", 0),
        "ass_dialogue_count": ass.get("dialogue_count", 0),
        "ass_layout": {key: ass.get(key) for key in ("playresx", "playresy", "marginl", "marginr", "marginv", "alignment", "fontsize")},
    }


def verify_clip_output(
    *,
    clip_id: str,
    directory: str | Path,
    expected_duration: float,
    render_cfg: dict[str, Any],
    caption_cfg: dict[str, Any],
    qc_cfg: dict[str, Any],
) -> dict[str, Any]:
    folder = Path(directory)
    required = [
        "clip-vertical.mp4", "clip-clean.mp4", "captions.srt", "captions.ass",
        "caption-map.json", "edit-plan.json", "metadata.json", "transcript.txt", "editor-notes.md",
    ]
    if bool(render_cfg.get("make_preview_image", True)):
        required.append("preview.jpg")
    missing = [name for name in required if not (folder / name).exists()]
    errors: list[str] = []
    warnings: list[str] = []
    media = None
    clean_media = None
    black_intervals: list[dict[str, float]] = []
    audio_metrics: dict[str, float | None] = {}
    caption_metrics: dict[str, Any] = {}

    if not missing:
        try:
            vertical = folder / "clip-vertical.mp4"
            clean = folder / "clip-clean.mp4"
            media = probe_media(vertical)
            clean_media = probe_media(clean)
            width = int(render_cfg.get("width", 1080))
            height = int(render_cfg.get("height", 1920))
            video = media.get("video") or {}
            if video.get("width") != width or video.get("height") != height:
                errors.append(f"resolution_not_{width}x{height}")
            expected_pixel = render_cfg.get("pixel_format")
            if expected_pixel and video.get("pixel_format") != expected_pixel:
                errors.append("pixel_format_mismatch")
            actual = float(media.get("duration_seconds") or 0)
            clean_actual = float(clean_media.get("duration_seconds") or 0)
            tolerance = max(float(qc_cfg.get("duration_tolerance_seconds", 0.75)), expected_duration * float(qc_cfg.get("duration_tolerance_ratio", 0.02)))
            if expected_duration and abs(actual - expected_duration) > tolerance:
                errors.append("duration_outside_tolerance")
            if abs(actual - clean_actual) > float(qc_cfg.get("clean_captioned_duration_tolerance_seconds", 0.12)):
                errors.append("clean_captioned_duration_mismatch")
            if not media.get("audio"):
                errors.append("audio_missing")
            else:
                expected_rate = int(render_cfg.get("audio_sample_rate", 48000))
                if any(stream.get("sample_rate") not in {None, expected_rate} for stream in media.get("audio", [])):
                    errors.append("audio_sample_rate_mismatch")
            min_size = int(qc_cfg.get("minimum_file_size_bytes", 10_000))
            if vertical.stat().st_size < min_size or clean.stat().st_size < min_size:
                errors.append("media_file_too_small")

            caption_metrics = verify_caption_files(
                folder / "captions.srt", folder / "captions.ass",
                media_duration=actual, width=width, height=height,
                caption_cfg=caption_cfg, qc_cfg=qc_cfg,
            )
            errors.extend(caption_metrics.get("errors", []))
            warnings.extend(caption_metrics.get("warnings", []))

            if bool(qc_cfg.get("detect_black_frames", True)):
                black_intervals = analyze_black_frames(
                    vertical,
                    min_duration=float(qc_cfg.get("black_min_duration_seconds", 0.15)),
                    pixel_threshold=float(qc_cfg.get("black_pixel_threshold", 0.10)),
                )
                boundary_warning = float(qc_cfg.get("boundary_black_warning_seconds", 0.15))
                boundary_fail = float(qc_cfg.get("boundary_black_hard_fail_seconds", 0.75))
                boundary_black = [
                    item for item in black_intervals
                    if item["start"] <= 0.05 or item["end"] >= max(0.0, actual - 0.05)
                ]
                if any(item["duration"] >= boundary_fail for item in boundary_black):
                    errors.append("black_boundary_above_hard_limit")
                elif any(item["duration"] >= boundary_warning for item in boundary_black):
                    warnings.append("black_boundary_detected")
                total_black = sum(item["duration"] for item in black_intervals)
                ratio = total_black / actual if actual > 0 else 0.0
                if ratio >= float(qc_cfg.get("black_ratio_warning", 0.10)):
                    warnings.append("high_black_frame_ratio")

            if bool(qc_cfg.get("analyze_audio", True)) and media.get("audio"):
                audio_metrics = analyze_audio(vertical)
                mean_db = audio_metrics.get("mean_volume_db")
                max_db = audio_metrics.get("max_volume_db")
                if mean_db is None or mean_db == float("-inf") or mean_db <= float(qc_cfg.get("silent_mean_volume_db", -65.0)):
                    errors.append("audio_effectively_silent")
                if max_db is not None and max_db != float("-inf") and max_db > float(qc_cfg.get("clipping_warning_db", -0.10)):
                    warnings.append("audio_peak_near_clipping")
        except Exception as exc:
            errors.append(f"output_probe_or_qc_failed:{exc}")

    valid = not missing and not errors
    return {
        "clip_id": str(clip_id),
        "directory": str(folder),
        "valid": valid,
        "missing": missing,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "media": media,
        "clean_media": clean_media,
        "black_intervals": black_intervals,
        "audio_metrics": audio_metrics,
        "caption_metrics": caption_metrics,
    }
