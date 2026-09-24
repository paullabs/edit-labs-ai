from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HarnessError(RuntimeError):
    """Expected operational failure with a user-readable message."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(value: str, max_length: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return (slug[:max_length].rstrip("-") or "run")


def load_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        raise HarnessError(f"Arquivo JSON não encontrado: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HarnessError(f"JSON inválido em {p}: {exc}") from exc


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix(p.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(p)
    return p


def load_yaml(path: str | Path) -> dict[str, Any]:
    if yaml is None:
        raise HarnessError("PyYAML não está instalado. Execute: pip install -r requirements.txt")
    p = Path(path)
    if not p.exists():
        raise HarnessError(f"YAML não encontrado: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data or {}


def which(command: str) -> str | None:
    return shutil.which(command)


def run_command(
    command: Sequence[str],
    *,
    check: bool = True,
    capture: bool = True,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            check=False,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise HarnessError(f"Comando não encontrado: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HarnessError(f"Comando excedeu o tempo limite: {' '.join(command)}") from exc
    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or f"código {result.returncode}"
        raise HarnessError(f"Falha ao executar {' '.join(command)}\n{detail}")
    return result


def parse_timecode(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        if float(value) < 0:
            raise ValueError("Timestamp negativo")
        return float(value)
    text = value.strip().replace(",", ".")
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    parts = text.split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"Timestamp inválido: {value}")
    try:
        nums = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError(f"Timestamp inválido: {value}") from exc
    if len(nums) == 3:
        hours, minutes, seconds = nums
    elif len(nums) == 2:
        hours, minutes, seconds = 0.0, nums[0], nums[1]
    else:
        hours, minutes, seconds = 0.0, 0.0, nums[0]
    if minutes >= 60 or seconds >= 60 or min(hours, minutes, seconds) < 0:
        raise ValueError(f"Timestamp inválido: {value}")
    return hours * 3600 + minutes * 60 + seconds


def format_timecode(seconds: float, *, srt: bool = False, decimals: int = 3) -> str:
    """Format a non-negative timestamp with correct carry at minute/hour boundaries."""
    seconds = max(0.0, float(seconds))
    if srt:
        total_millis = int(round(seconds * 1000))
        hours, remainder = divmod(total_millis, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole, millis = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}"
    if decimals < 0:
        raise ValueError("decimals deve ser >= 0")
    factor = 10 ** decimals
    total_units = int(round(seconds * factor))
    hours, remainder = divmod(total_units, 3600 * factor)
    minutes, remainder = divmod(remainder, 60 * factor)
    whole, fraction = divmod(remainder, factor)
    if decimals:
        return f"{hours:02d}:{minutes:02d}:{whole:02d}.{fraction:0{decimals}d}"
    return f"{hours:02d}:{minutes:02d}:{whole:02d}"


def normalize_intervals(intervals: Iterable[Sequence[float]]) -> list[tuple[float, float]]:
    cleaned: list[tuple[float, float]] = []
    for pair in intervals:
        if len(pair) != 2:
            continue
        start, end = float(pair[0]), float(pair[1])
        if end <= start:
            continue
        cleaned.append((start, end))
    cleaned.sort()
    merged: list[tuple[float, float]] = []
    for start, end in cleaned:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def intervals_duration(intervals: Iterable[Sequence[float]]) -> float:
    return sum(end - start for start, end in normalize_intervals(intervals))


def intervals_intersection_duration(
    intervals_a: Iterable[Sequence[float]], intervals_b: Iterable[Sequence[float]]
) -> float:
    a = normalize_intervals(intervals_a)
    b = normalize_intervals(intervals_b)
    i = j = 0
    total = 0.0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if end > start:
            total += end - start
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def ensure_run_dir(run_dir: str | Path) -> Path:
    p = Path(run_dir).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise HarnessError(f"Run não encontrado: {p}")
    if not (p / "00-manifest.json").exists():
        raise HarnessError(f"Pasta não parece um run válido: {p}")
    return p


def update_manifest(run_dir: str | Path, **changes: Any) -> dict[str, Any]:
    run = Path(run_dir)
    path = run / "00-manifest.json"
    manifest = load_json(path)
    manifest.update(changes)
    manifest["updated_at"] = now_iso()
    write_json(path, manifest)
    return manifest


def set_stage(
    run_dir: str | Path,
    stage: str,
    status: str,
    *,
    artifacts: list[str] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    run = Path(run_dir)
    path = run / "00-manifest.json"
    manifest = load_json(path)
    stage_data = {"status": status, "updated_at": now_iso()}
    if artifacts is not None:
        stage_data["artifacts"] = artifacts
    if message:
        stage_data["message"] = message
    manifest.setdefault("stages", {})[stage] = stage_data
    manifest["updated_at"] = now_iso()
    if artifacts:
        existing = set(manifest.setdefault("artifacts", []))
        for artifact in artifacts:
            if artifact not in existing:
                manifest["artifacts"].append(artifact)
    write_json(path, manifest)
    return manifest


def relative_to_run(path: str | Path, run_dir: str | Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(run_dir).resolve()))
    except ValueError:
        return str(Path(path).resolve())


def words(text: str) -> list[str]:
    return re.findall(r"\b[\wÀ-ÿ'-]+\b", text, flags=re.UNICODE)
