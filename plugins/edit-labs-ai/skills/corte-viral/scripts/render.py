from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from scripts.media_probe import probe_media
from scripts.utils import HarnessError, load_json, run_command, sha256_file, slugify, which, write_json


def _filter_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    value = value.replace(":", r"\:").replace("'", r"\'")
    return value


def _video_filter(width: int, height: int, anchor_x: float, zoom: float, fps: Any = "source") -> str:
    zoom = max(1.0, min(2.0, float(zoom)))
    target_w = int(math.ceil(width * zoom / 2) * 2)
    target_h = int(math.ceil(height * zoom / 2) * 2)
    anchor_x = max(0.0, min(1.0, float(anchor_x)))
    filters = [
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase",
        f"crop={width}:{height}:x='max(0,min(iw-ow,(iw-ow)*{anchor_x:.6f}))':y='max(0,(ih-oh)/2)'",
        "setsar=1",
    ]
    if fps not in {None, "source", "inherit"}:
        filters.append(f"fps={float(fps):g}")
    return ",".join(filters)


def _even(value: float) -> int:
    """FFmpeg/yuv420p exige dimensoes pares."""
    return max(2, int(round(value / 2)) * 2)


def _render_segment(
    ffmpeg: str,
    source: Path,
    output: Path,
    segment: dict[str, Any],
    render_cfg: dict[str, Any],
    has_audio: bool,
    src_w: int | None = None,
    src_h: int | None = None,
    fade_in: bool = False,
    fade_out: bool = False,
) -> None:
    start = float(segment["source_start"])
    end = float(segment["source_end"])
    duration = end - start
    if duration <= 0:
        raise HarnessError(f"Segmento inválido: {start}–{end}")
    # Micro-fade (25ms) nas bordas de corte real -- mata o clique de descontinuidade
    # de onda na emenda sem soar como transição (curto demais pra perceber). Nunca
    # aplicado na abertura/fechamento do proprio clipe, so entre segmentos que tem
    # gap real entre si (ver render_clip). Sem isso, o concat -c copy costura as
    # ondas exatamente no ponto de corte e pode estourar em clique audivel.
    click_fade = 0.025
    width = int(render_cfg.get("width", 1080))
    height = int(render_cfg.get("height", 1920))
    anchor = float(segment.get("crop_anchor_x", render_cfg.get("crop_anchor_x", 0.5)))
    zoom = float(segment.get("zoom", 1.0))
    # Regra da skill: o vertical nunca divide a tela. Todo segmento sai num crop único (cover) em quem fala;
    # um plano que traga layout "split" também sai em cover.
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        # Input seeking avoids decoding the whole source before every distant
        # segment. FFmpeg's default accurate seek still decodes from the
        # preceding keyframe and discards frames up to the requested timestamp.
        "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{duration:.6f}",
    ]
    vf = _video_filter(width, height, anchor, zoom, render_cfg.get("fps", "source"))
    command += ["-map", "0:v:0", "-vf", vf]
    command += [
        "-c:v", str(render_cfg.get("video_codec", "libx264")),
        "-preset", str(render_cfg.get("preset", "medium")),
        "-crf", str(render_cfg.get("crf", 18)),
        "-pix_fmt", str(render_cfg.get("pixel_format", "yuv420p")),
    ]
    if has_audio:
        afilters = ["aresample=async=1:first_pts=0"]
        if fade_in:
            afilters.append(f"afade=t=in:st=0:d={click_fade}")
        if fade_out:
            afilters.append(f"afade=t=out:st={max(duration - click_fade, 0):.6f}:d={click_fade}")
        command += [
            "-map", "0:a:0", "-af", ",".join(afilters),
            "-c:a", str(render_cfg.get("audio_codec", "aac")), "-b:a", "192k",
            "-ar", str(render_cfg.get("audio_sample_rate", 48000)),
        ]
    else:
        command += ["-an"]
    command += ["-movflags", "+faststart", str(output)]
    run_command(command)


def _concat_segments(ffmpeg: str, segment_files: list[Path], output: Path) -> None:
    if not segment_files:
        raise HarnessError("Nenhum segmento para concatenar")
    list_file = output.parent / "concat-list.txt"
    list_file.write_text(
        "".join(f"file '{str(path.resolve()).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for path in segment_files),
        encoding="utf-8",
    )
    result = run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", "-fflags", "+genpts", str(output)
    ], check=False)
    if result.returncode != 0:
        # Fallback re-encodes if the concat demuxer rejects stream parameters.
        run_command([
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)
        ])


def _normalize_audio(ffmpeg: str, input_path: Path, output_path: Path, render_cfg: dict[str, Any], has_audio: bool) -> None:
    if not has_audio:
        shutil.copy2(input_path, output_path)
        return
    target = float(render_cfg.get("loudness_lufs", -14))
    peak = float(render_cfg.get("true_peak_db", -1.0))
    lra = float(render_cfg.get("loudness_range", 11))
    run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(input_path),
        "-c:v", "copy", "-af", f"loudnorm=I={target}:TP={peak}:LRA={lra}",
        "-c:a", str(render_cfg.get("audio_codec", "aac")), "-b:a", "192k",
        "-ar", str(render_cfg.get("audio_sample_rate", 48000)),
        "-movflags", "+faststart", str(output_path)
    ])


def _tem_filtro_ass(ffmpeg: str) -> bool:
    import re as _re
    resultado = run_command([ffmpeg, "-hide_banner", "-filters"], check=False)
    saida = (resultado.stdout or "") + (resultado.stderr or "")
    # Palavra inteira: "ass" como substring casa com lowpass/highpass/bass/allpass.
    return bool(_re.search(r"^\s*\S*\s+(subtitles|ass)\s", saida, _re.MULTILINE))


def _burn_subtitles(ffmpeg: str, clean: Path, ass: Path, output: Path, render_cfg: dict[str, Any]) -> None:
    if not ass.exists():
        raise HarnessError(f"Legenda ASS não encontrada: {ass}")
    if not _tem_filtro_ass(ffmpeg):
        # Sem esta checagem o ffmpeg morre com "No option name near ..." — erro
        # que não diz o problema real. Nesta skill a queima é opcional: o padrão
        # entrega o vertical limpo e a motion-vox queima por outro caminho.
        raise HarnessError(
            "Este ffmpeg não tem o filtro `ass` (compilado sem libass), então não "
            "há como queimar legenda por aqui. Desligue `render.make_captioned_version` "
            "no config — o vertical limpo é o entregável desta skill — ou instale um "
            "ffmpeg com libass. Ver INSTALAR.md."
        )
    run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(clean),
        "-vf", f"ass='{_filter_path(ass)}'",
        "-c:v", str(render_cfg.get("video_codec", "libx264")),
        "-preset", str(render_cfg.get("preset", "medium")),
        "-crf", str(render_cfg.get("crf", 18)),
        "-pix_fmt", str(render_cfg.get("pixel_format", "yuv420p")),
        "-c:a", "copy", "-movflags", "+faststart", str(output)
    ])


def _preview(ffmpeg: str, video: Path, output: Path) -> None:
    run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-ss", "0.2", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(output)
    ])


def render_clip(
    source_video: str | Path,
    clip: dict[str, Any],
    plan: dict[str, Any],
    output_dir: str | Path,
    render_cfg: dict[str, Any],
) -> dict[str, Any]:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise HarnessError("FFmpeg não encontrado")
    source = Path(source_video).expanduser().resolve()
    if not source.exists():
        raise HarnessError(f"Vídeo fonte não encontrado: {source}")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    media = probe_media(source)
    has_audio = bool(media.get("audio"))
    src_video = media.get("video") or {}
    src_w, src_h = int(src_video.get("width") or 0), int(src_video.get("height") or 0)
    timeline = plan.get("timeline") or clip.get("segments") or []
    if not timeline:
        raise HarnessError(f"Clip {clip.get('id')} sem timeline")
    timeline = sorted(timeline, key=lambda item: item.get("order", 0))

    # Um corte real e uma descontinuidade de tempo-fonte entre segmentos vizinhos
    # (gap ou overlap); segmentos que so seguem um ao outro no bruto (fronteira de
    # decupagem interna, sem pular nada) nao levam fade -- teriam fade dos dois
    # lados e soariam como um mergulho de volume no meio de fala continua.
    gap_eps = 0.05
    n = len(timeline)
    fade_before = [False] * n
    fade_after = [False] * n
    for i in range(n - 1):
        gap = abs(float(timeline[i + 1].get("source_start", 0)) - float(timeline[i].get("source_end", 0)))
        if gap > gap_eps:
            fade_after[i] = True
            fade_before[i + 1] = True

    with tempfile.TemporaryDirectory(prefix="vch-render-") as temp_name:
        temp = Path(temp_name)
        segment_files = []
        for idx, segment in enumerate(timeline, start=1):
            segment_path = temp / f"segment-{idx:03d}.mp4"
            _render_segment(
                ffmpeg, source, segment_path, segment, render_cfg, has_audio, src_w, src_h,
                fade_in=fade_before[idx - 1], fade_out=fade_after[idx - 1],
            )
            segment_files.append(segment_path)
        concat_path = temp / "concat.mp4"
        _concat_segments(ffmpeg, segment_files, concat_path)
        clean = output / "clip-clean.mp4"
        _normalize_audio(ffmpeg, concat_path, clean, render_cfg, has_audio)

    captioned = output / "clip-vertical.mp4"
    ass = output / "captions.ass"
    if render_cfg.get("make_captioned_version", True):
        _burn_subtitles(ffmpeg, clean, ass, captioned, render_cfg)
    else:
        shutil.copy2(clean, captioned)

    preview = output / "preview.jpg"
    if render_cfg.get("make_preview_image", True):
        _preview(ffmpeg, captioned, preview)

    write_json(output / "edit-plan.json", plan)
    transcript_text = clip.get("reconstructed_transcript", "")
    (output / "transcript.txt").write_text(transcript_text + ("\n" if transcript_text else ""), encoding="utf-8")
    (output / "editor-notes.md").write_text(
        f"# {clip.get('title', clip.get('id', 'Clip'))}\n\n{plan.get('editor_notes') or clip.get('editor_notes', '')}\n",
        encoding="utf-8",
    )
    final_probe = probe_media(captioned)
    metadata = {
        "schema_version": "1.0",
        "clip_id": clip.get("id"),
        "title": clip.get("title"),
        "primary_context": clip.get("primary_context"),
        "profile": clip.get("profile"),
        "tags": clip.get("tags", []),
        "status": clip.get("status"),
        "scores": clip.get("scores", {}),
        "events": clip.get("events", {}),
        "segments": clip.get("segments", []),
        "output": {
            "clip_vertical": str(captioned),
            "clip_clean": str(clean),
            "captions_srt": str(output / "captions.srt"),
            "captions_ass": str(ass),
            "preview": str(preview) if preview.exists() else None,
        },
        "rendered_media": final_probe,
        "sha256": sha256_file(captioned),
    }
    write_json(output / "metadata.json", metadata)
    return metadata


def render_all(
    run_dir: str | Path,
    source_video: str | Path,
    final_clips: dict[str, Any],
    edit_plans: dict[str, Any],
    render_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    run = Path(run_dir)
    plans = {str(plan["clip_id"]): plan for plan in edit_plans.get("plans", [])}
    rendered = []
    for clip in final_clips.get("clips", []):
        if clip.get("status") not in {"APPROVED", "LONG_CLIP"}:
            continue
        clip_id = str(clip.get("id"))
        plan = plans.get(clip_id)
        if not plan:
            raise HarnessError(f"Edit plan ausente para {clip_id}")
        context = slugify(plan.get("primary_context") or clip.get("primary_context") or "outro")
        slug = slugify(plan.get("output_slug") or f"{clip_id}-{clip.get('title', '')}")
        output = run / "output" / "final-clips" / context / slug
        rendered.append(render_clip(source_video, clip, plan, output, render_cfg))
    return rendered
