from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reports import consolidate_final

CONFIG = {
    "selection": {"minimum_publishability_score": 7.5, "minimum_critical_score": 7.0, "truthfulness_gate": 9.0},
    "scoring_weights": {"hook": 0.5, "payoff": 0.5},
}
NOTAS_BAIXAS = {"hook": 6, "payoff": 6, "proposition_clarity": 6, "self_contained": 6, "truthfulness": 8}


class FinalizeHumanApprovalTests(unittest.TestCase):
    def _run(self, clip: dict, feed_status: str = "REBUILD", hard_fails: list | None = None,
             qc_hard_fails: list | None = None, sem_revisores: bool = False) -> tuple[dict, dict]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        docs = {
            "06-candidates.json": {"schema_version": "1.0", "clips": [clip]},
            "07-feed-review.json": {"reviews": [{"clip_id": "C1", "status": feed_status}]},
            "08-technical-audit.json": {"clips": [{"clip_id": "C1", "duration_seconds": 60, "hard_fails": hard_fails or []}]},
            "09-blind-review.json": {"reviews": [{"clip_id": "C1", "decision": "PASS"}]},
            "10-deduplication.json": {"decisions": []},
            "12-quality-review.json": {"reviews": [{"clip_id": "C1", "decision": "REBUILD",
                                                    "hard_fails": qc_hard_fails or []}]},
        }
        if sem_revisores:
            for nome in ("07-feed-review.json", "09-blind-review.json", "12-quality-review.json"):
                docs.pop(nome)
        for name, data in docs.items():
            (root / name).write_text(json.dumps(data), encoding="utf-8")
        return consolidate_final(root, CONFIG)

    def _clip(self, **extra) -> dict:
        return {"id": "C1", "profile": "story", "scores": dict(NOTAS_BAIXAS), "hard_fails": [], **extra}

    def test_aprovacao_humana_vence_parecer_e_nota_de_agente(self) -> None:
        final, rejected = self._run(self._clip(human_approval={"gate": 2, "by": "usuario"}))
        self.assertEqual([c["id"] for c in final["clips"]], ["C1"])
        clip = final["clips"][0]
        self.assertEqual(clip["status"], "APPROVED")
        self.assertIn("quality_review:REBUILD", clip["machine_review_warnings"])
        self.assertIn("feed_review:REBUILD", clip["machine_review_warnings"])
        self.assertIn("truthfulness_below_gate", clip["machine_review_warnings"])
        self.assertEqual(rejected["clips"], [])

    def test_hard_fail_tecnico_continua_bloqueando_mesmo_aprovado(self) -> None:
        final, rejected = self._run(self._clip(human_approval={"gate": 2}), hard_fails=["zero_duration"])
        self.assertEqual(final["clips"], [])
        self.assertEqual(rejected["clips"][0]["status"], "REJECTED")

    def test_hard_fail_do_revisor_vira_aviso_com_aprovacao_humana(self) -> None:
        final, _ = self._run(self._clip(human_approval={"gate": 2}), qc_hard_fails=["enquadramento suspeito"])
        clip = final["clips"][0]
        self.assertEqual(clip["status"], "APPROVED")
        self.assertEqual(clip["reviewer_hard_fails_overridden"], ["enquadramento suspeito"])
        self.assertIn("quality_review_hard_fails:1", clip["machine_review_warnings"])

    def test_hard_fail_do_revisor_bloqueia_sem_aprovacao_humana(self) -> None:
        final, rejected = self._run(self._clip(), qc_hard_fails=["enquadramento suspeito"])
        self.assertEqual(final["clips"], [])
        self.assertEqual(rejected["clips"][0]["status"], "REJECTED")

    def test_sem_revisores_e_com_aprovacao_humana_aprova(self) -> None:
        final, _ = self._run(self._clip(human_approval={"gate": 2}), sem_revisores=True)
        self.assertEqual(final["clips"][0]["status"], "APPROVED")
        self.assertNotIn("feed_review:None", final["clips"][0]["machine_review_warnings"])

    def test_sem_revisores_e_sem_aprovacao_decide_pelas_notas(self) -> None:
        final, rejected = self._run(self._clip(), sem_revisores=True)
        self.assertEqual(final["clips"], [])
        self.assertEqual(rejected["clips"][0]["final_decision_reasons"], ["truthfulness_below_gate"])

    def test_sem_aprovacao_humana_o_portao_de_maquina_continua_valendo(self) -> None:
        final, rejected = self._run(self._clip())
        self.assertEqual(final["clips"], [])
        self.assertEqual(rejected["clips"][0]["status"], "REBUILD")


if __name__ == "__main__":
    unittest.main()
