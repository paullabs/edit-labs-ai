from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from scripts.utils import load_json, slugify, write_json


def _by_id(items: list[dict[str, Any]], key: str = "clip_id") -> dict[str, dict[str, Any]]:
    return {str(item.get(key)): item for item in items if item.get(key) is not None}


def consolidate_final(run_dir: str | Path, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    run = Path(run_dir)
    candidates_data = load_json(run / "06-candidates.json")
    candidates = candidates_data.get("clips", [])
    feed = _by_id(load_json(run / "07-feed-review.json", {"reviews": []}).get("reviews", []))
    audits = _by_id(load_json(run / "08-technical-audit.json", {"clips": []}).get("clips", []))
    blind = _by_id(load_json(run / "09-blind-review.json", {"reviews": []}).get("reviews", []))
    dedupe = load_json(run / "10-deduplication.json", {"decisions": []}).get("decisions", [])
    quality = _by_id(load_json(run / "12-quality-review.json", {"reviews": []}).get("reviews", []))
    duplicate_losers = set()
    duplicate_winner = {}
    for decision in dedupe:
        winner = decision.get("winner")
        for clip_id in decision.get("duplicates", []):
            duplicate_losers.add(clip_id)
            duplicate_winner[clip_id] = winner
        if winner:
            for clip_id in decision.get("clip_ids", []):
                if clip_id != winner and clip_id not in decision.get("duplicates", []):
                    # Only mark explicit groups with a selected winner.
                    duplicate_losers.add(clip_id)
                    duplicate_winner[clip_id] = winner

    selection = config.get("selection", {})
    min_score = float(selection.get("minimum_publishability_score", 7.5))
    min_critical = float(selection.get("minimum_critical_score", 7.0))
    truth_gate = float(selection.get("truthfulness_gate", 9.0))
    weights = config.get("scoring_weights", {})
    approved = []
    rejected = []

    for original in candidates:
        clip = dict(original)
        clip_id = str(clip.get("id"))
        feed_review = feed.get(clip_id, {})
        audit = audits.get(clip_id, {})
        blind_review = blind.get(clip_id, {})
        quality_review = quality.get(clip_id, {})
        scores = dict(clip.get("scores", {}))
        scores.update(feed_review.get("scores", {}))
        clip["scores"] = scores
        if feed_review.get("events"):
            clip["events"] = feed_review["events"]
        # Falha técnica (medida por script: auditoria, validação) é diferente de "hard fail" que um
        # agente revisor declara. Com aprovação humana, só a técnica bloqueia; a do revisor vira aviso.
        technical_fails = sorted(set(list(clip.get("hard_fails", [])) + list(audit.get("hard_fails", []))))
        reviewer_fails = sorted(set(quality_review.get("hard_fails", [])))
        if clip.get("human_approval"):
            hard_fails = technical_fails
            clip["reviewer_hard_fails_overridden"] = reviewer_fails
        else:
            hard_fails = sorted(set(technical_fails + reviewer_fails))
        clip["hard_fails"] = hard_fails
        clip["technical_metrics"] = audit
        clip["blind_review"] = blind_review
        clip["feed_review"] = feed_review
        clip["quality_review"] = quality_review

        weighted = 0.0
        weight_total = 0.0
        for name, weight in weights.items():
            if name in scores:
                weighted += float(scores[name]) * float(weight)
                weight_total += float(weight)
        weighted_score = weighted / weight_total if weight_total else 0.0
        critical_values = [
            float(scores.get("proposition_clarity", 0)),
            float(scores.get("payoff", 0)),
            float(scores.get("self_contained", 0)),
            float(scores.get("truthfulness", 0)),
        ]
        critical_floor = min(critical_values)
        adjusted = weighted_score * (0.70 + 0.30 * critical_floor / 10.0)
        clip["publishability_score"] = round(adjusted, 3)

        reasons = []
        if clip_id in duplicate_losers:
            status = "DUPLICATE"
            reasons.append(f"Duplicado de {duplicate_winner.get(clip_id) or 'outro clipe'}")
        elif hard_fails:
            status = "REJECTED"
            reasons.extend(hard_fails)
        elif clip.get("human_approval"):
            # Portão humano: o usuário assistiu o preview e aprovou. Isso vale mais que nota ou
            # parecer de agente (que pode ter sido dado sobre uma versão anterior do corte).
            # Hard fail técnico e duplicata continuam bloqueando; o resto vira aviso registrado.
            avisos = []
            if quality_review and quality_review.get("decision") != "PASS":
                avisos.append(f"quality_review:{quality_review.get('decision')}")
            if clip.get("reviewer_hard_fails_overridden"):
                avisos.append(f"quality_review_hard_fails:{len(clip['reviewer_hard_fails_overridden'])}")
            if feed_review and feed_review.get("status") != "PASS":
                avisos.append(f"feed_review:{feed_review.get('status')}")
            if blind_review and blind_review.get("decision") != "PASS":
                avisos.append(f"blind_review:{blind_review.get('decision')}")
            if float(scores.get("truthfulness", 0)) < truth_gate:
                avisos.append("truthfulness_below_gate")
            if critical_floor < min_critical or adjusted < min_score:
                avisos.append("score_below_publishability_gate")
            clip["machine_review_warnings"] = avisos
            reasons.append("aprovado_pelo_usuario")
            duration = float(audit.get("duration_seconds", clip.get("estimated_final_duration_seconds", 0)) or 0)
            status = "LONG_CLIP" if duration > 120 or clip.get("profile") == "long_clip" else "APPROVED"
        elif quality_review and quality_review.get("decision") != "PASS":
            quality_decision = quality_review.get("decision")
            status = "REBUILD" if quality_decision in {None, "REBUILD"} else "REJECTED"
            reasons.extend(quality_review.get("reasons", ["quality_review_missing_or_not_passed"]))
        elif feed_review and feed_review.get("status") != "PASS":
            status = "REBUILD" if feed_review.get("status") == "REBUILD" else "REJECTED"
            reasons.extend(feed_review.get("problems", ["feed_review_not_passed"]))
        elif blind_review and blind_review.get("decision") != "PASS":
            status = "REBUILD" if blind_review.get("decision") == "REBUILD" else "REJECTED"
            reasons.extend(blind_review.get("problems", ["blind_review_not_passed"]))
        elif float(scores.get("truthfulness", 0)) < truth_gate:
            status = "REJECTED"
            reasons.append("truthfulness_below_gate")
        elif critical_floor < min_critical or adjusted < min_score:
            status = "WEAK"
            reasons.append("score_below_publishability_gate")
        else:
            duration = float(audit.get("duration_seconds", clip.get("estimated_final_duration_seconds", 0)) or 0)
            status = "LONG_CLIP" if duration > 120 or clip.get("profile") == "long_clip" else "APPROVED"
        clip["status"] = status
        clip["final_decision_reasons"] = reasons
        if status in {"APPROVED", "LONG_CLIP"}:
            approved.append(clip)
        else:
            rejected.append(clip)

    approved.sort(key=lambda item: item.get("publishability_score", 0), reverse=True)
    final = {"schema_version": "1.0", "run_id": run.name, "clips": approved}
    rejected_data = {"schema_version": "1.0", "run_id": run.name, "clips": rejected}
    write_json(run / "13-final-clips.json", final)
    write_json(run / "14-rejected-clips.json", rejected_data)
    return final, rejected_data


def write_run_report(run_dir: str | Path, final: dict[str, Any], rejected: dict[str, Any]) -> Path:
    run = Path(run_dir)
    all_clips = final.get("clips", []) + rejected.get("clips", [])
    counts = Counter(clip.get("status", "UNKNOWN") for clip in all_clips)
    lines = [
        f"# Relatório do run `{run.name}`", "", "## Resumo", "",
        f"- Aprovados: {counts.get('APPROVED', 0)}",
        f"- Long clips: {counts.get('LONG_CLIP', 0)}",
        f"- Rebuild: {counts.get('REBUILD', 0)}",
        f"- Duplicatas: {counts.get('DUPLICATE', 0)}",
        f"- Fracos: {counts.get('WEAK', 0)}",
        f"- Rejeitados: {counts.get('REJECTED', 0)}", "",
        "## Clipes aprovados", "",
    ]
    if not final.get("clips"):
        lines.append("Nenhum clipe passou por todos os gates. Isso é um resultado válido.\n")
    for clip in final.get("clips", []):
        lines += [
            f"### {clip.get('id')} — {clip.get('title', '')}", "",
            f"- Status: `{clip.get('status')}`",
            f"- Contexto: `{clip.get('primary_context')}`",
            f"- Perfil: `{clip.get('profile')}`",
            f"- Score: {clip.get('publishability_score', 0):.2f}",
            f"- Duração: {clip.get('technical_metrics', {}).get('duration_seconds', 'n/d')}s",
            f"- Por que funciona: {clip.get('why_it_can_work', '')}", "",
        ]
    lines += ["## Não aprovados", ""]
    for clip in rejected.get("clips", []):
        reasons = "; ".join(clip.get("final_decision_reasons", [])) or "sem motivo registrado"
        lines.append(f"- `{clip.get('id')}` — **{clip.get('status')}**: {reasons}")
    lines += ["", "## Arquivos", "", f"- JSON final: `{run / '13-final-clips.json'}`", f"- Rejeitados: `{run / '14-rejected-clips.json'}`", f"- Saída: `{run / 'output'}`", ""]
    path = run / "15-run-report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_context_index(run_dir: str | Path, final: dict[str, Any]) -> Path:
    run = Path(run_dir)
    plans = {
        str(plan.get("clip_id")): plan
        for plan in load_json(run / "11-edit-plans.json", {"plans": []}).get("plans", [])
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for clip in final.get("clips", []):
        plan = plans.get(str(clip.get("id")), {})
        context = slugify(plan.get("primary_context") or clip.get("primary_context") or "outro")
        grouped.setdefault(context, []).append(clip)
    lines = ["# Índice de clipes por contexto", ""]
    for context in sorted(grouped):
        lines += [f"## {context}", ""]
        for clip in grouped[context]:
            plan = plans.get(str(clip.get("id")), {})
            slug = slugify(plan.get("output_slug") or f"{clip.get('id')}-{clip.get('title', '')}")
            lines.append(f"- `{clip.get('id')}` — {clip.get('title', '')} — pasta: `{context}/{slug}`")
        lines.append("")
    path = run / "output" / "context-index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
