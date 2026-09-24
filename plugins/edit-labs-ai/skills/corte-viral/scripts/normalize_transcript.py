from __future__ import annotations

import json
import html
import re
from pathlib import Path
from typing import Any

from scripts.utils import HarnessError, parse_timecode, write_json

TIMESTAMP_LINE = re.compile(
    r"^\s*(?:\[)?(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)(?:\])?\s*(?:[-–—:]\s*)?(?P<text>.*)$"
)
SRT_RANGE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
)
VTT_RANGE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[.]\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[.]\d{1,3})"
)


def _clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^(?:>>\s*)+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_youtube_json3(data: dict[str, Any], source: str) -> dict[str, Any]:
    """Normalize YouTube json3 captions without the rolling-cue duplication in VTT."""
    raw_events = data.get("events") or []
    if not isinstance(raw_events, list):
        raise HarnessError("JSON3 do YouTube não contém uma lista de events")

    duration_seconds = 0.0
    content_events: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        start_ms = float(event.get("tStartMs", 0) or 0)
        duration_ms = float(event.get("dDurationMs", 0) or 0)
        duration_seconds = max(duration_seconds, (start_ms + duration_ms) / 1000.0)
        segs = event.get("segs") or []
        if not isinstance(segs, list):
            continue
        visible = "".join(str(seg.get("utf8", "")) for seg in segs if isinstance(seg, dict))
        if _clean_text(visible):
            content_events.append(event)

    if not content_events:
        raise HarnessError("Nenhuma fala válida foi encontrada no JSON3 do YouTube")

    segments: list[dict[str, Any]] = []
    speaker_index = 1
    for event_index, event in enumerate(content_events):
        event_start = float(event.get("tStartMs", 0) or 0) / 1000.0
        event_end = event_start + float(event.get("dDurationMs", 0) or 0) / 1000.0
        if event_index + 1 < len(content_events):
            next_start = float(content_events[event_index + 1].get("tStartMs", 0) or 0) / 1000.0
            if next_start > event_start:
                event_end = min(event_end, next_start)

        raw_segs = [seg for seg in event.get("segs", []) if isinstance(seg, dict)]
        if any(seg.get("isSpeakerChange") for seg in raw_segs):
            speaker_index += 1

        fragments: list[tuple[float, str]] = []
        for seg in raw_segs:
            fragment = html.unescape(str(seg.get("utf8", "")))
            if not fragment.strip() or fragment.strip() == ">>":
                continue
            fragment_start = event_start + float(seg.get("tOffsetMs", 0) or 0) / 1000.0
            fragments.append((fragment_start, fragment))
        if not fragments:
            continue

        if event_end <= fragments[-1][0]:
            event_end = fragments[-1][0] + 0.4

        words: list[dict[str, Any]] = []
        for fragment_index, (fragment_start, fragment) in enumerate(fragments):
            fragment_tokens = fragment.strip().split()
            if not fragment_tokens:
                continue
            fragment_end = (
                fragments[fragment_index + 1][0]
                if fragment_index + 1 < len(fragments)
                else event_end
            )
            fragment_end = max(fragment_end, fragment_start + 0.04 * len(fragment_tokens))
            step = (fragment_end - fragment_start) / len(fragment_tokens)
            for token_index, token in enumerate(fragment_tokens):
                token = token.lstrip(">")
                if not token:
                    continue
                start = fragment_start + token_index * step
                end = fragment_start + (token_index + 1) * step
                words.append({"word": token, "start": start, "end": end})

        content = _clean_text("".join(fragment for _, fragment in fragments))
        if not content or not words:
            continue
        segments.append({
            "id": len(segments),
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "text": content,
            "speaker": f"SPEAKER_{speaker_index:02d}",
            "words": words,
        })

    return {
        "schema_version": "1.0",
        "source": source,
        "language": "pt",
        "duration_seconds": duration_seconds or max(segment["end"] for segment in segments),
        "segments": segments,
        "warnings": ["Transcript de legendas automáticas do YouTube; confirmar falas-chave no áudio."],
    }


def _normalize_json(data: Any, source: str) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        return _normalize_youtube_json3(data, source)
    if isinstance(data, list):
        raw_segments = data
        language = None
        duration = None
    elif isinstance(data, dict):
        raw_segments = data.get("segments") or data.get("transcript") or data.get("items")
        language = data.get("language")
        duration = data.get("duration_seconds") or data.get("duration")
    else:
        raise HarnessError("Formato JSON de transcript não reconhecido")
    if not isinstance(raw_segments, list):
        raise HarnessError("JSON não contém uma lista de segments/transcript/items")
    segments = []
    for idx, item in enumerate(raw_segments):
        if not isinstance(item, dict):
            continue
        start = item.get("start", item.get("start_time"))
        end = item.get("end", item.get("end_time"))
        text = item.get("text", item.get("content", ""))
        if start is None or end is None:
            continue
        try:
            start_f = parse_timecode(start)
            end_f = parse_timecode(end)
        except ValueError:
            continue
        if end_f <= start_f:
            continue
        words = []
        for word in item.get("words", []) or []:
            if not isinstance(word, dict) or word.get("start") is None or word.get("end") is None:
                continue
            try:
                w_start = parse_timecode(word["start"])
                w_end = parse_timecode(word["end"])
            except ValueError:
                continue
            if w_end <= w_start:
                continue
            words.append({
                "word": str(word.get("word", word.get("text", ""))).strip(),
                "start": w_start,
                "end": w_end,
                "probability": word.get("probability", word.get("confidence")),
            })
        segment = {
            "id": item.get("id", idx),
            "start": start_f,
            "end": end_f,
            "text": _clean_text(str(text)),
            "speaker": str(item.get("speaker", item.get("speaker_label", "UNKNOWN"))),
            "confidence": item.get("confidence", item.get("avg_logprob")),
        }
        if words:
            segment["words"] = words
        segments.append(segment)
    if not segments:
        raise HarnessError("Nenhum segmento com timestamps válidos foi encontrado")
    segments.sort(key=lambda s: (s["start"], s["end"]))
    for idx, seg in enumerate(segments):
        seg["id"] = idx
    computed_duration = max(s["end"] for s in segments)
    try:
        duration_f = float(duration) if duration is not None else computed_duration
    except (TypeError, ValueError):
        duration_f = computed_duration
    return {
        "schema_version": "1.0",
        "source": source,
        "language": language or "unknown",
        "duration_seconds": duration_f,
        "segments": segments,
    }


WORD_TAG = re.compile(r"<(\d\d:\d\d:\d\d\.\d\d\d)>(?:<c[^>]*>)?([^<]*)(?:</c>)?")
CUE_HEADER = re.compile(
    r"(\d\d):(\d\d):(\d\d)\.(\d\d\d)\s+-->\s+(\d\d):(\d\d):(\d\d)\.(\d\d\d)"
)


def _looks_like_youtube_vtt(text: str) -> bool:
    """Legenda automatica do YouTube: traz timing por palavra em <hh:mm:ss.mmm><c>."""
    return "-->" in text and "<c>" in text


def _parse_youtube_vtt(text: str, source: str) -> dict[str, Any]:
    """
    Extrai timing POR PALAVRA da legenda automatica do YouTube.

    Duas armadilhas deste formato, as duas resolvidas aqui:

    1. Cue rolante: cada cue repete o final do cue anterior antes do texto novo.
       Parsear ingenuamente triplica o transcript. A correcao e casar o maior
       sufixo do cue anterior com o prefixo do atual e emitir so a cauda nova.
    2. Timestamp por palavra e explicito, nao interpolado: `<00:26:48.520><c> x</c>`.
       Usar o valor real em vez de dividir a duracao do cue pelo numero de palavras
       e o que permite cortar sem truncar palavra.

    O marcador `>>` do YouTube indica troca de locutor e vira fronteira de segmento.
    """
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    palavras: list[dict[str, Any]] = []
    anterior: list[str] = []
    locutor = 0

    for block in blocks:
        match = CUE_HEADER.search(block)
        if not match:
            continue
        g = list(map(int, match.groups()))
        inicio = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        fim = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        if fim - inicio < 0.05:
            continue  # cue de "assentamento": so repete o texto ja emitido

        payload = "\n".join(
            line for line in block[match.end():].splitlines()
            if not line.lstrip().startswith("align:")
        )
        payload = html.unescape(payload)

        # (tempo, token) na ordem em que aparecem
        cronometrados: list[tuple[float, str]] = []
        primeira_tag = WORD_TAG.search(payload)
        if primeira_tag:
            cabeca = payload[:primeira_tag.start()]
            t = primeira_tag.group(1)
            limite_cabeca = int(t[0:2]) * 3600 + int(t[3:5]) * 60 + float(t[6:])
        else:
            cabeca, limite_cabeca = payload, fim
        # O texto antes da primeira tag nao tem timestamp proprio: distribui no
        # intervalo ate a primeira palavra cronometrada. Empilhar tudo no inicio
        # do cue criaria palavras com o mesmo instante e legenda sobreposta.
        tokens_cabeca = cabeca.split()
        if tokens_cabeca:
            vao = max(0.0, limite_cabeca - inicio)
            passo = vao / len(tokens_cabeca) if vao > 0 else 0.0
            for indice, token in enumerate(tokens_cabeca):
                cronometrados.append((inicio + indice * passo, token))
        for m in WORD_TAG.finditer(payload):
            t = m.group(1)
            quando = int(t[0:2]) * 3600 + int(t[3:5]) * 60 + float(t[6:])
            for token in m.group(2).split():
                cronometrados.append((quando, token))
        if not cronometrados:
            continue

        atual = [tok for _, tok in cronometrados]
        # dedupe da cue rolante: maior sufixo do anterior == prefixo do atual
        sobreposicao = 0
        for tamanho in range(min(len(anterior), len(atual)), 0, -1):
            if anterior[-tamanho:] == atual[:tamanho]:
                sobreposicao = tamanho
                break
        novos = cronometrados[sobreposicao:]
        if not novos and atual != anterior:
            novos = cronometrados
        anterior = atual

        for quando, token in novos:
            if token == ">>":
                locutor += 1
                continue
            limpo = token.lstrip(">").strip()
            if not limpo:
                continue
            palavras.append({"word": limpo, "start": quando, "speaker": locutor, "cue_end": fim})

    if not palavras:
        raise HarnessError("VTT do YouTube sem palavras cronometradas utilizaveis")

    # ordem estrita: instantes iguais ou invertidos tornam impossivel qualquer
    # janela de legenda sem sobreposicao mais adiante.
    for i in range(1, len(palavras)):
        if palavras[i]["start"] <= palavras[i - 1]["start"]:
            palavras[i]["start"] = palavras[i - 1]["start"] + 0.001

    # fim de cada palavra = inicio da proxima, limitado pelo fim do cue
    for i, w in enumerate(palavras):
        proximo = palavras[i + 1]["start"] if i + 1 < len(palavras) else w["cue_end"]
        # Cues do YouTube se sobrepoem no tempo. O teto e sempre o inicio da
        # proxima palavra: um piso de duracao que o ultrapasse geraria legenda
        # sobreposta la na frente.
        teto = proximo if proximo > w["start"] else w["start"] + 0.04
        fim = min(w["cue_end"], teto)
        fim = max(fim, min(w["start"] + 0.04, teto))
        w["end"] = fim if fim > w["start"] else w["start"] + 0.001

    # agrupa em segmentos: troca de locutor, pausa longa ou tamanho maximo
    segments: list[dict[str, Any]] = []
    atual_words: list[dict[str, Any]] = []

    def fechar() -> None:
        if not atual_words:
            return
        segments.append({
            "id": len(segments),
            "start": atual_words[0]["start"],
            "end": atual_words[-1]["end"],
            "text": _clean_text(" ".join(w["word"] for w in atual_words)),
            "speaker": f"SPEAKER_{atual_words[0]['speaker']:02d}",
            "words": [{"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)}
                      for w in atual_words],
        })

    for w in palavras:
        if atual_words:
            trocou = w["speaker"] != atual_words[-1]["speaker"]
            pausa = w["start"] - atual_words[-1]["end"] > 0.7
            longo = w["end"] - atual_words[0]["start"] > 12.0
            if trocou or pausa or longo:
                fechar()
                atual_words = []
        atual_words.append(w)
    fechar()

    return {
        "schema_version": "1.0",
        "source": source,
        "language": "unknown",
        "duration_seconds": max(s["end"] for s in segments),
        "segments": segments,
    }


def _parse_srt_or_vtt(text: str, source: str) -> dict[str, Any]:
    lines = text.replace("\r\n", "\n").split("\n")
    segments = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = SRT_RANGE.search(line) or VTT_RANGE.search(line)
        if not match:
            i += 1
            continue
        start = parse_timecode(match.group("start"))
        end = parse_timecode(match.group("end"))
        i += 1
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i].strip())
            i += 1
        content = _clean_text(" ".join(text_lines))
        if content and end > start:
            segments.append({"id": len(segments), "start": start, "end": end, "text": content, "speaker": "UNKNOWN"})
        i += 1
    if not segments:
        raise HarnessError("Nenhuma cue SRT/VTT válida foi encontrada")
    return {
        "schema_version": "1.0",
        "source": source,
        "language": "unknown",
        "duration_seconds": max(s["end"] for s in segments),
        "segments": segments,
    }


def _parse_timestamp_text(text: str, source: str) -> dict[str, Any]:
    starts: list[tuple[float, str]] = []
    current_start: float | None = None
    current_text: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = TIMESTAMP_LINE.match(line)
        if match:
            if current_start is not None and current_text:
                starts.append((current_start, _clean_text(" ".join(current_text))))
            current_start = parse_timecode(match.group("start"))
            current_text = [match.group("text")] if match.group("text") else []
        elif current_start is not None:
            current_text.append(line)
    if current_start is not None and current_text:
        starts.append((current_start, _clean_text(" ".join(current_text))))
    if not starts:
        raise HarnessError(
            "Transcript sem timestamps reconhecíveis. Use JSON, SRT, VTT ou linhas como [00:01:23] texto."
        )
    segments = []
    for idx, (start, content) in enumerate(starts):
        if idx + 1 < len(starts):
            end = starts[idx + 1][0]
        else:
            # O fim real da última cue é desconhecido. Estimativa técnica conservadora baseada em fala,
            # registrada somente para permitir análise; render deve ser revisado.
            end = start + max(1.0, min(12.0, len(content.split()) / 2.5))
        if end <= start:
            continue
        segments.append({"id": len(segments), "start": start, "end": end, "text": content, "speaker": "UNKNOWN"})
    return {
        "schema_version": "1.0",
        "source": source,
        "language": "unknown",
        "duration_seconds": max(s["end"] for s in segments),
        "segments": segments,
        "warnings": ["O fim da última cue foi estimado porque o formato fornecia apenas timestamps de início."],
    }


def normalize_transcript(input_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise HarnessError(f"Transcript não encontrado: {path}")
    suffix = path.suffix.lower()
    raw_text = path.read_text(encoding="utf-8-sig", errors="replace")
    if suffix in {".json", ".json3"}:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise HarnessError(f"Transcript JSON inválido: {exc}") from exc
        normalized = _normalize_json(data, str(path))
    elif suffix in {".srt", ".vtt"}:
        if suffix == ".vtt" and _looks_like_youtube_vtt(raw_text):
            normalized = _parse_youtube_vtt(raw_text, str(path))
        else:
            normalized = _parse_srt_or_vtt(raw_text, str(path))
    else:
        normalized = _parse_timestamp_text(raw_text, str(path))
    if output_path:
        write_json(output_path, normalized)
    return normalized
