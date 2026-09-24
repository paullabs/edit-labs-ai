from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.utils import HarnessError, run_command, which, write_json

PTS_RE = re.compile(r"pts_time:(?P<pts>[0-9.]+)")


def extract_visual_index(
    video_path: str | Path,
    output_dir: str | Path,
    output_json: str | Path,
    *,
    interval_seconds: float = 5.0,
    scene_threshold: float = 0.32,
    jpeg_quality: int = 3,
    start_seconds: float | None = None,
    duration_seconds: float | None = None,
    frame_prefix: str = "",
) -> dict[str, Any]:
    """Extrai frames periódicos e frames de troca de cena.

    Por padrão processa o arquivo inteiro — caro para vídeos longos (cada
    segundo decodificado duas vezes: uma para os frames periódicos, uma para
    detecção de cena). Para escopar a uma janela específica (ex.: só a região
    de um candidato já selecionado), passe `start_seconds`/`duration_seconds`:
    o `-ss` antes do `-i` faz seek rápido sem decodificar o resto do vídeo.
    """
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise HarnessError("FFmpeg não encontrado")
    source = Path(video_path).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    periodic_dir = out_dir / "periodic"
    scene_dir = out_dir / "scenes"
    periodic_dir.mkdir(parents=True, exist_ok=True)
    scene_dir.mkdir(parents=True, exist_ok=True)

    seek_args: list[str] = []
    if start_seconds is not None:
        seek_args += ["-ss", str(max(0.0, start_seconds))]
    duration_args: list[str] = []
    if duration_seconds is not None:
        duration_args = ["-t", str(max(0.1, duration_seconds))]
    offset = start_seconds or 0.0

    periodic_pattern = periodic_dir / f"{frame_prefix}frame-%06d.jpg"
    run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        *seek_args, "-i", str(source), *duration_args,
        "-vf", f"fps=1/{interval_seconds}", "-q:v", str(jpeg_quality), str(periodic_pattern)
    ])
    periodic_files = sorted(periodic_dir.glob(f"{frame_prefix}frame-*.jpg"))
    periodic = [
        {"timestamp": round(offset + idx * interval_seconds, 3), "path": str(path)}
        for idx, path in enumerate(periodic_files)
    ]

    scene_pattern = scene_dir / f"{frame_prefix}scene-%06d.jpg"
    result = run_command([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "info",
        *seek_args, "-i", str(source), *duration_args,
        "-vf", f"select='gt(scene,{scene_threshold})',showinfo", "-fps_mode", "vfr",
        "-q:v", str(jpeg_quality), str(scene_pattern)
    ], check=False)
    scene_pts = [float(m.group("pts")) for m in PTS_RE.finditer((result.stderr or "") + (result.stdout or ""))]
    scene_files = sorted(scene_dir.glob(f"{frame_prefix}scene-*.jpg"))
    scenes = []
    for idx, path in enumerate(scene_files):
        pts = scene_pts[idx] if idx < len(scene_pts) else None
        scenes.append({"timestamp": round(offset + pts, 3) if pts is not None else None, "path": str(path)})

    index = {
        "schema_version": "1.0",
        "source": str(source),
        "periodic_interval_seconds": interval_seconds,
        "scene_threshold": scene_threshold,
        "periodic_frames": periodic,
        "scene_frames": scenes,
        "warnings": [] if len(scene_files) == len(scene_pts) else [
            "Alguns scene frames não receberam timestamp exato; revise o índice."
        ],
    }
    write_json(output_json, index)
    return index


def build_contact_sheets(
    visual_index: dict[str, Any], output_dir: str | Path, *, columns: int = 4, width: int = 1600
) -> list[str]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise HarnessError("Pillow não está instalado") from exc
    frames = visual_index.get("periodic_frames", [])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not frames:
        return []
    rows_per_sheet = 4
    per_sheet = max(1, columns * rows_per_sheet)
    cell_w = width // columns
    cell_h = int(cell_w * 9 / 16) + 34
    outputs = []
    for page, start in enumerate(range(0, len(frames), per_sheet), start=1):
        batch = frames[start:start + per_sheet]
        rows = (len(batch) + columns - 1) // columns
        sheet = Image.new("RGB", (width, rows * cell_h), "black")
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
        for idx, frame in enumerate(batch):
            path = Path(frame["path"])
            if not path.exists():
                continue
            image = Image.open(path).convert("RGB")
            image.thumbnail((cell_w, cell_h - 34))
            x = (idx % columns) * cell_w + (cell_w - image.width) // 2
            y = (idx // columns) * cell_h
            sheet.paste(image, (x, y))
            label = f"{frame.get('timestamp', 0):.1f}s"
            draw.text((idx % columns * cell_w + 8, y + cell_h - 28), label, fill="white", font=font)
        output = out / f"contact-sheet-{page:03d}.jpg"
        sheet.save(output, quality=88)
        outputs.append(str(output))
    return outputs
