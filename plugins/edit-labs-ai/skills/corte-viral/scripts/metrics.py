from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

from scripts.utils import (
    HarnessError,
    intervals_duration,
    intervals_intersection_duration,
    load_json,
    normalize_intervals,
    run_command,
    which,
    words,
    write_json,
)

SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")


def clip_intervals(clip: dict[str, Any]) -> list[tuple[float, float]]:
    return [
        (float(seg["source_start"]), float(seg["source_end"]))
        for seg in clip.get("segments", [])
        if seg.get("source_start") is not None and seg.get("source_end") is not None
    ]


def timeline_duration(clip: dict[str, Any]) -> float:
    # Timeline duration sums segments in output order. Overlap in source is still replay in final.
    return sum(max(0.0, float(seg["source_end"]) - float(seg["source_start"])) for seg in clip.get("segments", []))


def highlight_repetition_ratio(clip: dict[str, Any]) -> float:
    highlight = []
    body = []
    for segment in clip.get("segments", []):
        interval = (float(segment["source_start"]), float(segment["source_end"]))
        role = str(segment.get("role", "")).lower()
        if "highlight" in role or role == "hook":
            highlight.append(interval)
        else:
            body.append(interval)
    highlight_duration = intervals_duration(highlight)
    if highlight_duration <= 0:
        return 0.0
    repeated = intervals_intersection_duration(highlight, body)
    return min(1.0, repeated / highlight_duration)


def pairwise_overlap(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for a, b in itertools.combinations(clips, 2):
        a_intervals = clip_intervals(a)
        b_intervals = clip_intervals(b)
        a_duration = intervals_duration(a_intervals)
        b_duration = intervals_duration(b_intervals)
        overlap = intervals_intersection_duration(a_intervals, b_intervals)
        ratio_a = overlap / a_duration if a_duration else 0.0
        ratio_b = overlap / b_duration if b_duration else 0.0
        results.append({
            "clip_a": a.get("id", ""),
            "clip_b": b.get("id", ""),
            "overlap_seconds": round(overlap, 3),
            "ratio_a": round(min(1.0, ratio_a), 6),
            "ratio_b": round(min(1.0, ratio_b), 6),
            "contained": ratio_a >= 0.95 or ratio_b >= 0.95,
        })
    return results


def _segment_word_count(transcript: dict[str, Any], start: float, end: float) -> int:
    count = 0
    for segment in transcript.get("segments", []):
        s_start = float(segment.get("start", 0))
        s_end = float(segment.get("end", 0))
        if s_end <= start or s_start >= end:
            continue
        word_items = segment.get("words") or []
        if word_items:
            count += sum(
                1 for word in word_items
                if float(word.get("end", 0)) > start and float(word.get("start", 0)) < end
            )
        else:
            segment_duration = max(0.001, s_end - s_start)
            overlap = max(0.0, min(end, s_end) - max(start, s_start))
            count += round(len(words(segment.get("text", ""))) * overlap / segment_duration)
    return count


def speech_words_per_second(clip: dict[str, Any], transcript: dict[str, Any] | None) -> float | None:
    if not transcript:
        return None
    duration = timeline_duration(clip)
    if duration <= 0:
        return None
    count = sum(
        _segment_word_count(transcript, float(seg["source_start"]), float(seg["source_end"]))
        for seg in clip.get("segments", [])
    )
    return count / duration


def _detect_silence_in_interval(
    media_path: str | Path, start: float, end: float, noise_db: float, min_duration: float
) -> float:
    ffmpeg = which("ffmpeg")
    if not ffmpeg or end <= start:
        return 0.0
    result = run_command([
        ffmpeg, "-hide_banner", "-loglevel", "info", "-ss", f"{start:.3f}", "-t", f"{end-start:.3f}",
        "-i", str(media_path), "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-"
    ], check=False)
    log = (result.stderr or "") + (result.stdout or "")
    starts = [float(value) for value in SILENCE_START.findall(log)]
    ends = [float(value) for value in SILENCE_END.findall(log)]
    total = 0.0
    for idx, s in enumerate(starts):
        e = ends[idx] if idx < len(ends) else end - start
        total += max(0.0, e - s)
    return total


def detect_clip_silence(
    clip: dict[str, Any], media_path: str | Path | None, *, noise_db: float = -36, min_duration: float = 0.55
) -> float | None:
    if not media_path or not Path(media_path).exists() or not which("ffmpeg"):
        return None
    total = 0.0
    for seg in clip.get("segments", []):
        total += _detect_silence_in_interval(
            media_path, float(seg["source_start"]), float(seg["source_end"]), noise_db, min_duration
        )
    return total


def validate_clip_timestamps(clip: dict[str, Any], media_duration: float | None) -> tuple[bool, list[str]]:
    errors = []
    previous_order = 0
    seen_orders = set()
    for index, segment in enumerate(clip.get("segments", []), start=1):
        try:
            start = float(segment["source_start"])
            end = float(segment["source_end"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"segment_{index}_timestamp_invalid")
            continue
        if start < 0 or end <= start:
            errors.append(f"segment_{index}_range_invalid")
        if media_duration is not None and end > media_duration + 0.25:
            errors.append(f"segment_{index}_outside_media")
        order = int(segment.get("order", index))
        if order in seen_orders:
            errors.append("duplicate_segment_order")
        seen_orders.add(order)
        if order < previous_order:
            errors.append("segment_order_not_monotonic")
        previous_order = order
    if not clip.get("segments"):
        errors.append("no_segments")
    return not errors, sorted(set(errors))


def audit_candidates(
    candidates_path: str | Path,
    output_path: str | Path,
    *,
    transcript_path: str | Path | None = None,
    media_path: str | Path | None = None,
    media_duration: float | None = None,
    repetition_limit: float = 0.30,
    overlap_limit: float = 0.50,
    silence_noise_db: float = -36,
    silence_min_duration: float = 0.55,
    detect_silence: bool = False,
) -> dict[str, Any]:
    candidates = load_json(candidates_path)
    clips = candidates.get("clips", [])
    transcript = load_json(transcript_path) if transcript_path and Path(transcript_path).exists() else None
    audits = []
    for clip in clips:
        valid, timestamp_errors = validate_clip_timestamps(clip, media_duration)
        repetition = highlight_repetition_ratio(clip)
        hard_fails = list(timestamp_errors)
        warnings = []
        if repetition > 0.70:
            hard_fails.append("highlight_repetition_above_70pct")
        elif repetition > repetition_limit:
            warnings.append("highlight_repetition_above_approved_limit")
        duration = timeline_duration(clip)
        wps = speech_words_per_second(clip, transcript)
        silence = detect_clip_silence(
            clip, media_path, noise_db=silence_noise_db, min_duration=silence_min_duration
        ) if detect_silence else None
        if duration <= 0:
            hard_fails.append("zero_duration")
        audits.append({
            "clip_id": clip.get("id", ""),
            "duration_seconds": round(duration, 3),
            "valid_timestamps": valid,
            "highlight_repetition_ratio": round(repetition, 6),
            "speech_words_per_second": None if wps is None else round(wps, 4),
            "silence_seconds": None if silence is None else round(silence, 3),
            "hard_fails": sorted(set(hard_fails)),
            "warnings": sorted(set(warnings)),
        })
    overlap = pairwise_overlap(clips)
    for item in overlap:
        if max(item["ratio_a"], item["ratio_b"]) > overlap_limit:
            item["warning"] = "overlap_above_approved_limit"
    output = {
        "schema_version": "1.0",
        "clips": audits,
        "pairwise_overlap": overlap,
    }
    write_json(output_path, output)
    return output


def temporal_dedupe_from_audit(audit: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    counter = 1
    for pair in audit.get("pairwise_overlap", []):
        if pair.get("contained") or max(pair.get("ratio_a", 0), pair.get("ratio_b", 0)) >= 0.50:
            groups.append({
                "group_id": f"temporal-{counter:03d}",
                "clip_ids": [pair["clip_a"], pair["clip_b"]],
                "winner": "",
                "duplicates": [],
                "reason": "Requer decisão editorial: sobreposição temporal alta.",
                "semantic_similarity": None,
                "temporal_metrics": pair,
            })
            counter += 1
    result = {"schema_version": "1.0", "decisions": groups, "type": "temporal_candidates"}
    write_json(output_path, result)
    return result
