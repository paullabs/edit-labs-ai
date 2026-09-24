#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.extract_audio import extract_analysis_audio
from scripts.media_probe import probe_media
from scripts.metrics import audit_candidates, temporal_dedupe_from_audit
from scripts.normalize_transcript import normalize_transcript
from scripts.output_qc import verify_clip_output
from scripts.preflight import print_preflight, run_preflight
from scripts.render import render_all
from scripts.reports import consolidate_final, write_context_index, write_run_report
from scripts.subtitles import build_caption_files
from scripts.transcribe import transcribe_faster_whisper
from scripts.utils import (
    HarnessError,
    PROJECT_ROOT,
    ensure_run_dir,
    load_json,
    load_yaml,
    now_iso,
    set_stage,
    slugify,
    timestamp_id,
    update_manifest,
    write_json,
)
from scripts.validation import ARTIFACT_SCHEMAS, validate_json_file, validate_project, validate_run_artifacts
from scripts.visual_index import build_contact_sheets, extract_visual_index

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".m2ts"}
TRANSCRIPT_EXTENSIONS = {".json", ".json3", ".srt", ".vtt", ".txt", ".md", ".csv"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def config(run: str | Path | None = None) -> dict[str, Any]:
    cfg = load_yaml(PROJECT_ROOT / "config" / "default.yaml")
    platform_name = os.environ.get("VCH_PLATFORM")
    if run and not platform_name:
        manifest = load_json(Path(run) / "00-manifest.json", {})
        platform_name = manifest.get("inputs", {}).get("platform")
    platform_name = str(platform_name or "cross-platform")
    platform_path = PROJECT_ROOT / "config" / "platforms" / f"{platform_name}.yaml"
    if platform_path.exists():
        platform = load_yaml(platform_path)
        platform_overlay = {
            "selected_platform": platform_name,
            "platform": platform,
            "render": {
                "width": platform.get("width", cfg.get("render", {}).get("width", 1080)),
                "height": platform.get("height", cfg.get("render", {}).get("height", 1920)),
            },
            "captions": {"safe_zone": platform.get("caption_safe_zone", {})},
        }
        cfg = _deep_merge(cfg, platform_overlay)
    override = os.environ.get("VCH_CONFIG")
    if override:
        cfg = _deep_merge(cfg, load_yaml(Path(override).expanduser().resolve()))
    return cfg


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_preflight(_: argparse.Namespace) -> int:
    report = run_preflight()
    print_preflight(report)
    return 0 if report["ready_for_analysis"] else 2


def _classify_inputs(first: str | None, second: str | None) -> tuple[str | None, str | None]:
    if not first:
        return None, second
    path = Path(first).expanduser()
    suffix = path.suffix.lower()
    if suffix in TRANSCRIPT_EXTENSIONS and suffix not in VIDEO_EXTENSIONS and not second:
        return None, str(path)
    return str(path), str(Path(second).expanduser()) if second else None


def cmd_init(args: argparse.Namespace) -> int:
    if args.run:
        run = ensure_run_dir(args.run)
        print(f"RUN_DIR={run}")
        return 0
    video_path, transcript_path = _classify_inputs(args.input, args.transcript)
    if not video_path and not transcript_path:
        raise HarnessError("Forneça vídeo, transcript ou --run")
    for value, label in [(video_path, "vídeo"), (transcript_path, "transcript"), (args.brief, "brief")]:
        if value and not Path(value).expanduser().exists():
            raise HarnessError(f"{label.capitalize()} não encontrado: {value}")
    source_name = Path(video_path or transcript_path or "run").stem
    run_id = f"{timestamp_id()}-{slugify(source_name, 48)}"
    workspace = Path(args.workspace or PROJECT_ROOT / "workspace" / "runs").expanduser().resolve()
    run = workspace / run_id
    run.mkdir(parents=True, exist_ok=False)
    (run / "assets" / "frames").mkdir(parents=True)
    (run / "assets" / "contact-sheets").mkdir(parents=True)
    (run / "iterations").mkdir(parents=True)
    (run / "output" / "final-clips").mkdir(parents=True)
    capabilities = run_preflight()
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "mode": args.mode,
        "status": "initialized",
        "inputs": {
            "video_path": str(Path(video_path).expanduser().resolve()) if video_path else "",
            "transcript_path": str(Path(transcript_path).expanduser().resolve()) if transcript_path else "",
            "brief_path": str(Path(args.brief).expanduser().resolve()) if args.brief else "",
            "max_clips": args.max_clips,
            "platform": args.platform,
        },
        "capabilities": capabilities,
        "stages": {"init": {"status": "complete", "updated_at": now_iso()}},
        "artifacts": ["00-manifest.json"],
        "errors": [],
        "warnings": [],
    }
    write_json(run / "00-manifest.json", manifest)
    if args.brief:
        brief_source = Path(args.brief).expanduser().resolve()
        brief_target = run / "00-brief.yaml"
        shutil.copy2(brief_source, brief_target)
        set_stage(run, "brief", "complete", artifacts=["00-brief.yaml"])
    print(f"RUN_DIR={run}")
    return 0


def _prepare_media(
    run: Path, manifest: dict[str, Any], cfg: dict[str, Any], *, build_visual_index: bool = False
) -> list[str]:
    artifacts = []
    video = manifest.get("inputs", {}).get("video_path")
    if video:
        media = probe_media(video)
        write_json(run / "01-media.json", media)
        artifacts.append("01-media.json")
        if media.get("audio"):
            audio_path = run / "assets" / "audio-analysis.wav"
            extract_analysis_audio(video, audio_path)
            artifacts.append("assets/audio-analysis.wav")
        if build_visual_index:
            visual_cfg = cfg.get("visual_index", {})
            try:
                visual = extract_visual_index(
                    video,
                    run / "assets" / "frames",
                    run / "03-visual-index.json",
                    interval_seconds=float(visual_cfg.get("interval_seconds", 5.0)),
                    scene_threshold=float(visual_cfg.get("scene_threshold", 0.32)),
                    jpeg_quality=int(visual_cfg.get("jpeg_quality", 3)),
                )
                sheets = build_contact_sheets(
                    visual,
                    run / "assets" / "contact-sheets",
                    columns=int(visual_cfg.get("contact_sheet_columns", 4)),
                    width=int(visual_cfg.get("contact_sheet_width", 1600)),
                )
                visual["contact_sheets"] = sheets
                write_json(run / "03-visual-index.json", visual)
                artifacts += ["03-visual-index.json"] + [str(Path(p).relative_to(run)) for p in sheets]
            except Exception as exc:
                write_json(run / "03-visual-index.json", {
                    "schema_version": "1.0", "source": video, "periodic_frames": [], "scene_frames": [],
                    "warnings": [f"Índice visual não gerado: {exc}"]
                })
                artifacts.append("03-visual-index.json")
        else:
            # Índice visual ADIADO por padrão: decodifica o vídeo inteiro duas
            # vezes (frames periódicos + detecção de cena) e é caro demais
            # para rodar antes de sequer saber quais trechos interessam.
            # A seleção (context-mapper / clip-hunter) roda só com o
            # transcript. Depois de escolhidos os candidatos, gere o índice
            # escopado às janelas deles com `vch visual-index --windows`.
            write_json(run / "03-visual-index.json", {
                "schema_version": "1.0", "source": video, "periodic_frames": [], "scene_frames": [],
                "warnings": [
                    "Índice visual adiado (padrão): rode `vch visual-index --run <dir> "
                    "--windows START-END,...` escopado aos candidatos escolhidos, ou "
                    "`vch prepare --run <dir> --visual-index` para forçar o vídeo inteiro."
                ]
            })
            artifacts.append("03-visual-index.json")
    else:
        write_json(run / "01-media.json", {
            "schema_version": "1.0", "path": "", "filename": "", "duration_seconds": None,
            "video": None, "audio": [], "analysis_only": True
        })
        write_json(run / "03-visual-index.json", {
            "schema_version": "1.0", "source": "", "periodic_frames": [], "scene_frames": [],
            "warnings": ["Sem vídeo: auditoria visual desativada."]
        })
        artifacts += ["01-media.json", "03-visual-index.json"]
    return artifacts


def _prepare_transcript(run: Path, manifest: dict[str, Any], cfg: dict[str, Any]) -> str:
    transcript_path = manifest.get("inputs", {}).get("transcript_path")
    video_path = manifest.get("inputs", {}).get("video_path")
    output = run / "02-transcript.json"
    if transcript_path:
        normalize_transcript(transcript_path, output)
        return "02-transcript.json"
    if not video_path:
        raise HarnessError("Sem vídeo e sem transcript")
    tcfg = cfg.get("transcription", {})
    backend = tcfg.get("backend", "auto")
    if backend not in {"auto", "faster-whisper"}:
        raise HarnessError(f"Backend de transcrição não implementado neste pacote: {backend}")
    transcribe_faster_whisper(
        video_path,
        output,
        model_name=str(tcfg.get("model", "small")),
        language=tcfg.get("language", "pt"),
        device=str(tcfg.get("device", "auto")),
        compute_type=str(tcfg.get("compute_type", "auto")),
        vad_filter=bool(tcfg.get("vad_filter", True)),
    )
    return "02-transcript.json"


def cmd_prepare(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    cfg = config(run)
    manifest = load_json(run / "00-manifest.json")
    set_stage(run, "prepare", "running")
    # Transcript primeiro: é o que a seleção (context-mapper/clip-hunter) usa
    # e é barato. O índice visual fica de fora por padrão — ver _prepare_media.
    artifacts = [_prepare_transcript(run, manifest, cfg)]
    artifacts += _prepare_media(run, manifest, cfg, build_visual_index=bool(args.visual_index))
    set_stage(run, "prepare", "complete", artifacts=artifacts)
    update_manifest(run, status="prepared")
    _print_json({"run": str(run), "artifacts": artifacts})
    return 0


def _parse_windows(raw: str | None) -> list[tuple[float, float]]:
    if not raw:
        return []
    windows = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        start_s, _, end_s = chunk.partition("-")
        start, end = float(start_s), float(end_s)
        if end <= start:
            raise HarnessError(f"Janela inválida (fim <= início): {chunk}")
        windows.append((start, end))
    return windows


def cmd_visual_index(args: argparse.Namespace) -> int:
    """Gera (ou completa) o índice visual — cheio ou escopado a janelas.

    Uso normal do pipeline: depois que a seleção já escolheu os candidatos,
    rode escopado às janelas deles (com folga de alguns segundos), nunca o
    vídeo inteiro de novo. `--full` existe para vídeos curtos ou quando o
    índice completo é realmente necessário (ex.: revisão manual extensa).
    """
    run = ensure_run_dir(args.run)
    cfg = config(run)
    manifest = load_json(run / "00-manifest.json")
    video = manifest.get("inputs", {}).get("video_path")
    if not video:
        raise HarnessError("Run sem vídeo: não há o que indexar.")
    visual_cfg = cfg.get("visual_index", {})
    frames_dir = run / "assets" / "frames"
    existing = load_json(run / "03-visual-index.json", {}) if (run / "03-visual-index.json").exists() else {}
    periodic: list[dict[str, Any]] = list(existing.get("periodic_frames") or [])
    scenes: list[dict[str, Any]] = list(existing.get("scene_frames") or [])

    windows = _parse_windows(args.windows)
    if args.full or not windows:
        visual = extract_visual_index(
            video, frames_dir, run / "03-visual-index.json",
            interval_seconds=float(visual_cfg.get("interval_seconds", 5.0)),
            scene_threshold=float(visual_cfg.get("scene_threshold", 0.32)),
            jpeg_quality=int(visual_cfg.get("jpeg_quality", 3)),
        )
        periodic, scenes = visual["periodic_frames"], visual["scene_frames"]
    else:
        for idx, (start, end) in enumerate(windows):
            visual = extract_visual_index(
                video, frames_dir, run / "03-visual-index.json",
                interval_seconds=float(visual_cfg.get("interval_seconds", 5.0)),
                scene_threshold=float(visual_cfg.get("scene_threshold", 0.32)),
                jpeg_quality=int(visual_cfg.get("jpeg_quality", 3)),
                start_seconds=start, duration_seconds=end - start,
                frame_prefix=f"w{idx:03d}-",
            )
            periodic += visual["periodic_frames"]
            scenes += visual["scene_frames"]
        periodic.sort(key=lambda f: f["timestamp"])
        scenes.sort(key=lambda f: (f["timestamp"] is None, f["timestamp"]))

    index = {
        "schema_version": "1.0",
        "source": video,
        "periodic_interval_seconds": float(visual_cfg.get("interval_seconds", 5.0)),
        "scene_threshold": float(visual_cfg.get("scene_threshold", 0.32)),
        "periodic_frames": periodic,
        "scene_frames": scenes,
        "warnings": [] if (args.full or not windows) else [
            f"Índice escopado a {len(windows)} janela(s); frames fora delas não existem."
        ],
    }
    sheets = build_contact_sheets(
        index, run / "assets" / "contact-sheets",
        columns=int(visual_cfg.get("contact_sheet_columns", 4)),
        width=int(visual_cfg.get("contact_sheet_width", 1600)),
    )
    index["contact_sheets"] = sheets
    write_json(run / "03-visual-index.json", index)
    set_stage(run, "visual-index", "complete", artifacts=["03-visual-index.json"])
    _print_json({"run": str(run), "windows": windows, "frames": len(periodic) + len(scenes)})
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    cfg = config(run)
    candidates = run / "06-candidates.json"
    if not candidates.exists():
        raise HarnessError("06-candidates.json não encontrado")
    media = load_json(run / "01-media.json", {})
    transcript = run / "02-transcript.json"
    manifest = load_json(run / "00-manifest.json")
    video = manifest.get("inputs", {}).get("video_path") or None
    selection = cfg.get("selection", {})
    silence_cfg = cfg.get("silence", {})
    output = run / "08-technical-audit.json"
    audit_candidates(
        candidates,
        output,
        transcript_path=transcript if transcript.exists() else None,
        media_path=video,
        media_duration=media.get("duration_seconds"),
        repetition_limit=float(selection.get("maximum_highlight_repetition_approved", 0.30)),
        overlap_limit=float(selection.get("maximum_duplicate_overlap_approved", 0.50)),
        silence_noise_db=float(silence_cfg.get("noise_db", -36)),
        silence_min_duration=float(silence_cfg.get("minimum_duration_seconds", 0.55)),
        detect_silence=bool(silence_cfg.get("detect", True)) and bool(video),
    )
    set_stage(run, "technical_audit", "complete", artifacts=["08-technical-audit.json"])
    _print_json(load_json(output))
    return 0


def cmd_dedupe(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    audit_path = run / "08-technical-audit.json"
    if not audit_path.exists():
        raise HarnessError("08-technical-audit.json não encontrado")
    output = run / "10-temporal-deduplication.json"
    result = temporal_dedupe_from_audit(load_json(audit_path), output)
    set_stage(run, "temporal_dedupe", "complete", artifacts=["10-temporal-deduplication.json"])
    _print_json(result)
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    dedupe_path = run / "10-deduplication.json"
    if not dedupe_path.exists():
        write_json(dedupe_path, {"schema_version": "1.0", "decisions": []})
    final, rejected = consolidate_final(run, config(run))
    report = write_run_report(run, final, rejected)
    index = write_context_index(run, final)
    set_stage(run, "finalize", "complete", artifacts=[
        "13-final-clips.json", "14-rejected-clips.json", "15-run-report.md", "output/context-index.md"
    ])
    update_manifest(run, status="finalized")
    _print_json({"approved": len(final.get("clips", [])), "rejected_or_other": len(rejected.get("clips", [])), "report": str(report), "index": str(index)})
    return 0


def _plans_by_id(run: Path) -> dict[str, dict[str, Any]]:
    plans_data = load_json(run / "11-edit-plans.json")
    return {str(plan["clip_id"]): plan for plan in plans_data.get("plans", [])}


def cmd_subtitles(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    cfg = config(run)
    transcript = run / "02-transcript.json"
    if not transcript.exists():
        raise HarnessError("02-transcript.json não encontrado")
    final = load_json(run / "13-final-clips.json")
    plans = _plans_by_id(run)
    caption_cfg = cfg.get("captions", {})
    style_name = caption_cfg.get("style", "clean")
    style = dict(load_yaml(PROJECT_ROOT / "config" / "caption_styles" / f"{style_name}.yaml"))
    render_cfg = cfg.get("render", {})
    width = int(render_cfg.get("width", 1080))
    height = int(render_cfg.get("height", 1920))
    style["play_res_x"] = width
    style["play_res_y"] = height
    safe_zone = caption_cfg.get("safe_zone", {})
    style["margin_l"] = max(float(style.get("margin_l", 0)), float(safe_zone.get("left_px", 0)))
    style["margin_r"] = max(float(style.get("margin_r", 0)), float(safe_zone.get("right_px", 0)))
    if int(style.get("alignment", 2)) in {1, 2, 3}:
        style["margin_v"] = max(float(style.get("margin_v", 0)), float(safe_zone.get("bottom_px", 0)))
    if bool(caption_cfg.get("scale_style_to_render", True)):
        scale = min(width / 1080.0, height / 1920.0)
        for key in ("font_size", "outline", "shadow", "margin_l", "margin_r", "margin_v"):
            if key in style:
                style[key] = max(1, round(float(style[key]) * scale))
    artifacts = []
    results = []
    for clip in final.get("clips", []):
        clip_id = str(clip.get("id"))
        plan = plans.get(clip_id)
        if not plan:
            raise HarnessError(f"Edit plan ausente para {clip_id}")
        context = slugify(plan.get("primary_context") or clip.get("primary_context") or "outro")
        output_slug = slugify(plan.get("output_slug") or f"{clip_id}-{clip.get('title', '')}")
        output = run / "output" / "final-clips" / context / output_slug
        timeline = plan.get("timeline") or clip.get("segments") or []
        result = build_caption_files(transcript, timeline, output, caption_config=caption_cfg, style=style)
        results.append({"clip_id": clip_id, **result})
        for path in [result["srt"], result["ass"], result["caption_map"]]:
            artifacts.append(str(Path(path).relative_to(run)))
    set_stage(run, "subtitles", "complete", artifacts=artifacts)
    _print_json({"clips": results})
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    manifest = load_json(run / "00-manifest.json")
    video = manifest.get("inputs", {}).get("video_path")
    if not video:
        raise HarnessError("Render exige vídeo fonte")
    final = load_json(run / "13-final-clips.json")
    plans = load_json(run / "11-edit-plans.json")
    rendered = render_all(run, video, final, plans, config(run).get("render", {}))
    artifact_paths = []
    for metadata in rendered:
        for value in metadata.get("output", {}).values():
            if value and Path(value).exists():
                artifact_paths.append(str(Path(value).relative_to(run)))
    set_stage(run, "render", "complete", artifacts=artifact_paths)
    update_manifest(run, status="rendered")
    _print_json({"rendered": len(rendered), "clips": [item.get("clip_id") for item in rendered]})
    return 0


def cmd_verify_output(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    final = load_json(run / "13-final-clips.json", {"clips": []})
    plans = _plans_by_id(run) if (run / "11-edit-plans.json").exists() else {}
    audit = {
        str(item["clip_id"]): item
        for item in load_json(run / "08-technical-audit.json", {"clips": []}).get("clips", [])
    }
    cfg = config(run)
    render_cfg = cfg.get("render", {})
    caption_cfg = cfg.get("captions", {})
    qc_cfg = cfg.get("quality_control", {})
    checks = []
    for clip in final.get("clips", []):
        clip_id = str(clip.get("id"))
        plan = plans.get(clip_id, {})
        context = slugify(plan.get("primary_context") or clip.get("primary_context") or "outro")
        output_slug = slugify(plan.get("output_slug") or f"{clip_id}-{clip.get('title', '')}")
        directory = run / "output" / "final-clips" / context / output_slug
        # A duração esperada é a do plano (já com o colapso de pausas); a da auditoria é a do candidato, pré-colapso.
        expected_duration = float(
            plan.get("estimated_final_duration_seconds")
            or audit.get(clip_id, {}).get("duration_seconds", 0)
            or 0
        )
        checks.append(verify_clip_output(
            clip_id=clip_id,
            directory=directory,
            expected_duration=expected_duration,
            render_cfg=render_cfg,
            caption_cfg=caption_cfg,
            qc_cfg=qc_cfg,
        ))
    all_valid = all(item.get("valid", False) for item in checks)
    report = {"schema_version": "1.0", "valid": all_valid, "checks": checks}
    write_json(run / "16-output-verification.json", report)
    set_stage(run, "verify_output", "complete" if all_valid else "failed", artifacts=["16-output-verification.json"])
    update_manifest(run, status="complete" if all_valid else "output_failed")
    _print_json(report)
    return 0 if all_valid else 3



def cmd_validate_artifact(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    filename = Path(args.file).name
    schema = args.schema or ARTIFACT_SCHEMAS.get(filename)
    if not schema:
        raise HarnessError(f"Nenhum schema conhecido para {filename}; forneça --schema")
    path = run / args.file
    if not path.exists():
        raise HarnessError(f"Artefato não encontrado: {path}")
    errors = validate_json_file(path, schema)
    result = {"file": str(path), "schema": schema, "valid": not errors, "errors": errors}
    _print_json(result)
    return 0 if not errors else 3


def cmd_blind_packets(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    candidates = load_json(run / "06-candidates.json")
    feed_by_id = {str(item.get("clip_id")): item for item in load_json(run / "07-feed-review.json", {"reviews": []}).get("reviews", [])}
    audit_by_id = {str(item.get("clip_id")): item for item in load_json(run / "08-technical-audit.json", {"clips": []}).get("clips", [])}
    output_dir = run / "blind-packets"
    output_dir.mkdir(parents=True, exist_ok=True)
    packets = []
    for clip in candidates.get("clips", []):
        clip_id = str(clip.get("id"))
        feed = feed_by_id.get(clip_id, {})
        audit = audit_by_id.get(clip_id, {})
        if feed.get("status") == "REJECT" or audit.get("hard_fails"):
            continue
        packet = {
            "schema_version": "1.0",
            "clip_id": clip_id,
            "timeline": [
                {
                    "order": segment.get("order", index),
                    "source_start": segment.get("source_start"),
                    "source_end": segment.get("source_end"),
                    "role": segment.get("role", ""),
                }
                for index, segment in enumerate(clip.get("segments", []), start=1)
            ],
            "duration_seconds": audit.get("duration_seconds", clip.get("estimated_final_duration_seconds")),
            "reconstructed_transcript": clip.get("reconstructed_transcript", ""),
            "visual_events": clip.get("visual_events", []),
        }
        path = output_dir / f"{slugify(clip_id)}.json"
        write_json(path, packet)
        packets.append(str(path.relative_to(run)))
    set_stage(run, "blind_packets", "complete", artifacts=packets)
    _print_json({"count": len(packets), "packets": packets})
    return 0

def cmd_autoframe(args: argparse.Namespace) -> int:
    """Preenche crop_anchor_x/zoom por segmento usando deteccao de locutor ativo."""
    from scripts.autoframe import plan_segments, detect_silences, DEFAULT_MODEL

    run = ensure_run_dir(args.run)
    manifest = load_json(run / "00-manifest.json")
    video = manifest.get("inputs", {}).get("video_path")
    if not video:
        raise HarnessError("Run sem video: autoframe exige midia de origem.")
    model = Path(args.model) if args.model else DEFAULT_MODEL
    if not model.exists():
        raise HarnessError(
            f"Modelo YuNet ausente em {model}. Baixe o modelo de deteccao facial "
            "para habilitar o enquadramento por locutor ativo.")

    plans_path = run / "11-edit-plans.json"
    if not plans_path.exists():
        raise HarnessError("11-edit-plans.json ausente: rode o Edit Director antes do autoframe.")
    doc = load_json(plans_path)
    zones = json.loads(args.exclude_zones) if args.exclude_zones else None
    silences = detect_silences(video)
    total = 0
    for plan in doc.get("plans", []):
        # dicts inteiros: o autoframe herda layout/framing_reason do Edit Director
        segs = plan.get("timeline", [])
        if not segs:
            continue
        timeline, _ = plan_segments(video, segs, str(model), silences, zones)
        plan["timeline"] = timeline
        total += len(timeline)
    write_json(plans_path, doc)
    print(f"autoframe: {len(doc.get('plans', []))} plano(s), {total} subsegmento(s)")
    return 0


def cmd_validate_project(_: argparse.Namespace) -> int:
    result = validate_project()
    _print_json(result)
    return 0 if result["valid"] else 3


def cmd_validate_run(args: argparse.Namespace) -> int:
    run = ensure_run_dir(args.run)
    result = validate_run_artifacts(run)
    _print_json(result)
    return 0 if result["valid"] else 3


def cmd_digest(args: argparse.Namespace) -> int:
    """Digest de leitura: texto + timestamp, sem `words[]`.

    O `02-transcript.json` completo fica muitas vezes maior que o digest, e o
    digest diz a mesma coisa para quem esta ESCOLHENDO trecho. O timing por
    palavra continua no artefato original, para os scripts.
    """
    from digest import escrever, escrever_janelas

    run = ensure_run_dir(args.run)
    if getattr(args, "windows", None):
        result = escrever_janelas(run, args.windows)
    else:
        result = escrever(run, janela=args.janela, marcar=args.marcar)
    _print_json(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vch", description="Viral Clip Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("preflight")
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser("init")
    p.add_argument("input", nargs="?", help="Vídeo ou transcript")
    p.add_argument("transcript", nargs="?", help="Transcript opcional")
    p.add_argument("--mode", choices=["analyze", "verify", "render", "full"], default="full")
    p.add_argument("--brief")
    p.add_argument("--max-clips", type=int, default=0)
    p.add_argument("--platform", choices=["cross-platform", "tiktok", "instagram-reels"], default="cross-platform")
    p.add_argument("--workspace")
    p.add_argument("--run")
    p.set_defaults(func=cmd_init)

    for name, func in [
        ("audit", cmd_audit), ("dedupe", cmd_dedupe),
        ("finalize", cmd_finalize), ("subtitles", cmd_subtitles), ("render", cmd_render),
        ("verify-output", cmd_verify_output), ("validate-run", cmd_validate_run),
    ]:
        p = sub.add_parser(name)
        p.add_argument("--run", required=True)
        p.set_defaults(func=func)

    p = sub.add_parser("prepare")
    p.add_argument("--run", required=True)
    p.add_argument(
        "--visual-index", action="store_true",
        help="Gera o índice visual do vídeo inteiro já no prepare (caro; default é adiar)."
    )
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("visual-index")
    p.add_argument("--run", required=True)
    p.add_argument("--windows", help='Janelas "start-end,start-end,..." em segundos, escopadas a candidatos')
    p.add_argument("--full", action="store_true", help="Força o vídeo inteiro (ignora --windows)")
    p.set_defaults(func=cmd_visual_index)

    p = sub.add_parser("validate-artifact")
    p.add_argument("--run", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--schema")
    p.set_defaults(func=cmd_validate_artifact)

    p = sub.add_parser("blind-packets")
    p.add_argument("--run", required=True)
    p.set_defaults(func=cmd_blind_packets)

    p = sub.add_parser("autoframe")
    p.add_argument("--run", required=True)
    p.add_argument("--model")
    p.add_argument("--exclude-zones", help='JSON normalizado [[x0,y0,x1,y1],...] p/ telas do cenario')
    p.set_defaults(func=cmd_autoframe)

    p = sub.add_parser("digest")
    p.add_argument("--run", required=True)
    p.add_argument("--janela", type=float, default=20.0)
    p.add_argument("--marcar", type=float, default=3.0)
    p.add_argument("--windows", help='timing por palavra so destas janelas: "120-210,900-960"')
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("validate-project")
    p.set_defaults(func=cmd_validate_project)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except HarnessError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrompido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
