from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.utils import HarnessError, format_timecode, load_json, write_json

PUNCT_END = re.compile(r"[.!?…:;]$")
SOFT_PUNCT = re.compile(r"[,)]$")


@dataclass
class Token:
    text: str
    start: float
    end: float
    source_start: float
    source_end: float


@dataclass
class Caption:
    index: int
    start: float
    end: float
    text: str
    words: list[Token]


def _tokenize_text(text: str) -> list[str]:
    # Keeps punctuation attached to the previous lexical token.
    return re.findall(r"\S+", re.sub(r"\s+", " ", text.strip()))


def _segment_tokens(segment: dict[str, Any]) -> list[tuple[str, float, float]]:
    word_items = segment.get("words") or []
    tokens: list[tuple[str, float, float]] = []
    if word_items:
        for item in word_items:
            text = str(item.get("word", "")).strip()
            if not text:
                continue
            try:
                start = float(item["start"])
                end = float(item["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if end > start:
                tokens.append((text, start, end))
        return tokens
    text_tokens = _tokenize_text(str(segment.get("text", "")))
    if not text_tokens:
        return []
    start = float(segment.get("start", 0))
    end = float(segment.get("end", start))
    duration = max(0.001, end - start)
    step = duration / len(text_tokens)
    for idx, text in enumerate(text_tokens):
        t_start = start + idx * step
        t_end = start + (idx + 1) * step
        tokens.append((text, t_start, t_end))
    return tokens


def map_transcript_to_timeline(
    transcript: dict[str, Any], timeline: list[dict[str, Any]]
) -> list[Token]:
    mapped: list[Token] = []
    output_offset = 0.0
    source_segments = transcript.get("segments", [])
    ordered_timeline = sorted(timeline, key=lambda item: item.get("order", 0))
    for part in ordered_timeline:
        source_start = float(part["source_start"])
        source_end = float(part["source_end"])
        if source_end <= source_start:
            continue
        for segment in source_segments:
            seg_start = float(segment.get("start", 0))
            seg_end = float(segment.get("end", 0))
            if seg_end <= source_start or seg_start >= source_end:
                continue
            for text, token_start, token_end in _segment_tokens(segment):
                if token_end <= source_start or token_start >= source_end:
                    continue
                clipped_start = max(source_start, token_start)
                clipped_end = min(source_end, token_end)
                if clipped_end <= clipped_start:
                    continue
                mapped.append(Token(
                    text=text,
                    start=output_offset + (clipped_start - source_start),
                    end=output_offset + (clipped_end - source_start),
                    source_start=clipped_start,
                    source_end=clipped_end,
                ))
        output_offset += source_end - source_start
    mapped.sort(key=lambda token: (token.start, token.end))
    return _dedupe_adjacent_tokens(mapped)


def _dedupe_adjacent_tokens(tokens: list[Token]) -> list[Token]:
    if not tokens:
        return []
    result = [tokens[0]]
    for token in tokens[1:]:
        previous = result[-1]
        same_word = token.text.casefold().strip(".,!?;:") == previous.text.casefold().strip(".,!?;:")
        same_source = abs(token.source_start - previous.source_start) < 0.04
        if same_word and same_source:
            continue
        result.append(token)
    return result


def _caption_text(tokens: list[Token]) -> str:
    text = " ".join(token.text.strip() for token in tokens if token.text.strip())
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def chunk_tokens(
    tokens: list[Token],
    *,
    min_words: int = 2,
    max_words: int = 6,
    min_duration: float = 0.55,
    target_max_duration: float = 2.2,
    max_words_per_second: float = 10.0,
) -> list[Caption]:
    if not tokens:
        return []
    chunks: list[list[Token]] = []
    current: list[Token] = []
    for token in tokens:
        current.append(token)
        duration = max(0.001, current[-1].end - current[0].start)
        word_rate = len(current) / duration
        hard_limit = len(current) >= max_words
        semantic_end = bool(PUNCT_END.search(token.text)) and len(current) >= min_words
        soft_end = bool(SOFT_PUNCT.search(token.text)) and len(current) >= max(min_words, 3)
        too_long = duration >= target_max_duration and len(current) >= min_words
        too_fast_if_more = word_rate >= max_words_per_second and len(current) >= min_words
        if hard_limit or semantic_end or soft_end or too_long or too_fast_if_more:
            chunks.append(current)
            current = []
    if current:
        if chunks and len(current) < min_words and len(chunks[-1]) + len(current) <= max_words + 1:
            chunks[-1].extend(current)
        else:
            chunks.append(current)

    captions: list[Caption] = []
    for idx, chunk in enumerate(chunks, start=1):
        start = chunk[0].start
        end = max(chunk[-1].end, start + min_duration)
        if idx < len(chunks):
            # O piso de duracao minima NAO pode vencer a regra de nao sobrepor:
            # sem teto, o piso empurra o fim para depois do inicio da cue
            # seguinte quando duas caem muito perto uma da outra, e o
            # verify-output reprova com srt_entries_overlap_or_out_of_order.
            # Cue curta e aceitavel; cue sobreposta embaralha a legenda na tela.
            next_start = chunks[idx][0].start
            teto = next_start - 0.02
            end = min(end, teto) if teto > start else max(start + 0.001, min(end, next_start))
        captions.append(Caption(idx, start, end, _caption_text(chunk), chunk))
    return captions


def write_srt(captions: Iterable[Caption], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for caption in captions:
        blocks.append(
            f"{caption.index}\n{format_timecode(caption.start, srt=True)} --> {format_timecode(caption.end, srt=True)}\n{caption.text}\n"
        )
    output.write_text("\n".join(blocks), encoding="utf-8")
    return output


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def _wrap_two_lines(text: str, max_chars: int = 28) -> str:
    if len(text) <= max_chars:
        return text
    parts = text.split()
    best = None
    for split in range(1, len(parts)):
        left = " ".join(parts[:split])
        right = " ".join(parts[split:])
        score = max(len(left), len(right)) + abs(len(left) - len(right)) * 0.25
        if best is None or score < best[0]:
            best = (score, left, right)
    if best:
        return best[1] + r"\N" + best[2]
    return text


def write_ass(captions: Iterable[Caption], path: str | Path, style: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    play_res_x = int(style.get("play_res_x", 1080))
    play_res_y = int(style.get("play_res_y", 1920))
    font_name = style.get("font_name", "Arial")
    font_size = int(style.get("font_size", 68))
    primary = style.get("primary_colour", "&H00FFFFFF")
    secondary = style.get("secondary_colour", "&H00FFFFFF")
    outline_colour = style.get("outline_colour", "&H00101010")
    back_colour = style.get("back_colour", "&H64000000")
    bold = -1 if style.get("bold", True) else 0
    italic = -1 if style.get("italic", False) else 0
    outline = style.get("outline", 5)
    shadow = style.get("shadow", 1)
    alignment = style.get("alignment", 2)
    margin_l = style.get("margin_l", 90)
    margin_r = style.get("margin_r", 170)
    margin_v = style.get("margin_v", 330)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary},{secondary},{outline_colour},{back_colour},{bold},{italic},0,0,100,100,0,0,1,{outline},{shadow},{alignment},{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for caption in captions:
        wrapped = _wrap_two_lines(_ass_escape(caption.text))
        lines.append(f"Dialogue: 0,{_ass_time(caption.start)},{_ass_time(caption.end)},Default,,0,0,0,,{wrapped}\n")
    output.write_text("".join(lines), encoding="utf-8")
    return output


def build_caption_files(
    transcript_path: str | Path,
    timeline: list[dict[str, Any]],
    output_dir: str | Path,
    *,
    caption_config: dict[str, Any],
    style: dict[str, Any],
) -> dict[str, Any]:
    transcript = load_json(transcript_path)
    tokens = map_transcript_to_timeline(transcript, timeline)
    if not tokens:
        raise HarnessError("Nenhum token do transcript intersecta a timeline do clipe")
    captions = chunk_tokens(
        tokens,
        min_words=int(caption_config.get("min_words", 2)),
        max_words=int(caption_config.get("max_words", 6)),
        min_duration=float(caption_config.get("min_duration_seconds", 0.55)),
        target_max_duration=float(caption_config.get("target_max_duration_seconds", 2.2)),
        max_words_per_second=float(caption_config.get("max_words_per_second", 10.0)),
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    srt = write_srt(captions, out / "captions.srt")
    ass = write_ass(captions, out / "captions.ass", style)
    caption_map = {
        "schema_version": "1.0",
        "caption_count": len(captions),
        "captions": [{
            "index": cap.index,
            "start": round(cap.start, 3),
            "end": round(cap.end, 3),
            "text": cap.text,
            "source_words": [{
                "text": token.text,
                "source_start": round(token.source_start, 3),
                "source_end": round(token.source_end, 3),
            } for token in cap.words],
        } for cap in captions],
    }
    write_json(out / "caption-map.json", caption_map)
    return {"srt": str(srt), "ass": str(ass), "caption_map": str(out / "caption-map.json"), "count": len(captions)}
