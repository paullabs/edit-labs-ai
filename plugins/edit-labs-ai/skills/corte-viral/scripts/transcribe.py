from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.utils import HarnessError, write_json


def transcribe_faster_whisper(
    media_path: str | Path,
    output_path: str | Path,
    *,
    model_name: str = "small",
    language: str | None = "pt",
    device: str = "auto",
    compute_type: str = "auto",
    vad_filter: bool = True,
) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise HarnessError(
            "faster-whisper não está instalado. Forneça uma transcrição ou execute: pip install faster-whisper"
        ) from exc
    if device == "auto":
        device = "cuda" if _cuda_available() else "cpu"
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        str(Path(media_path).expanduser().resolve()),
        language=language,
        word_timestamps=True,
        vad_filter=vad_filter,
        beam_size=5,
    )
    segments = []
    for idx, segment in enumerate(segments_iter):
        words = []
        for word in segment.words or []:
            words.append({
                "word": word.word.strip(),
                "start": float(word.start),
                "end": float(word.end),
                "probability": float(word.probability) if word.probability is not None else None,
            })
        segments.append({
            "id": idx,
            "start": float(segment.start),
            "end": float(segment.end),
            "text": segment.text.strip(),
            "speaker": "UNKNOWN",
            "confidence": None,
            "words": words,
        })
    if not segments:
        raise HarnessError("O backend de transcrição não retornou segmentos")
    output = {
        "schema_version": "1.0",
        "source": str(Path(media_path).expanduser().resolve()),
        "language": getattr(info, "language", language or "unknown"),
        "language_probability": getattr(info, "language_probability", None),
        "duration_seconds": max(s["end"] for s in segments),
        "backend": "faster-whisper",
        "model": model_name,
        "segments": segments,
    }
    write_json(output_path, output)
    return output


def _cuda_available() -> bool:
    try:
        import ctranslate2
        return any("cuda" in device.lower() for device in ctranslate2.get_supported_compute_types("cuda"))
    except Exception:
        return False
