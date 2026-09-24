# -*- coding: utf-8 -*-
"""Testes do enquadramento por locutor ativo (sem exigir midia real)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# cv2/numpy sao dependencias OPCIONAIS (so o autoframe usa). Sem elas a skill
# continua funcionando com anchor manual, entao estes testes pulam em vez de falhar.
try:
    from scripts.autoframe import anchor_from_cx
    from scripts.active_speaker import _corr
    AUTOFRAME_OK, AUTOFRAME_ERR = True, ""
except ImportError as exc:  # pragma: no cover
    AUTOFRAME_OK, AUTOFRAME_ERR = False, str(exc)

requires_autoframe = unittest.skipUnless(
    AUTOFRAME_OK, f"autoframe indisponivel (opcional): {AUTOFRAME_ERR}"
)


@requires_autoframe
class TestAnchorMath(unittest.TestCase):
    """anchor_from_cx precisa ser o inverso exato do filtro de scripts/render.py."""

    def _render_center(self, anchor, zoom, src_w=1920, src_h=1080, out_w=1080, out_h=1920):
        s = max(out_w*zoom/src_w, out_h*zoom/src_h)
        scaled_w = src_w*s
        x = max(0.0, min(scaled_w-out_w, (scaled_w-out_w)*anchor))
        return (x + out_w/2)/s

    def test_centro(self):
        self.assertAlmostEqual(anchor_from_cx(960, 1.0), 0.5, places=3)

    def test_roundtrip_varios_zooms(self):
        for zoom in (1.0, 1.2, 1.45, 2.0):
            for cx in (400, 700, 960, 1300, 1600):
                a = anchor_from_cx(cx, zoom)
                self.assertGreaterEqual(a, 0.0); self.assertLessEqual(a, 1.0)
                if 0.0 < a < 1.0:   # fora do clamp, tem de bater
                    self.assertAlmostEqual(self._render_center(a, zoom), cx, delta=1.5)

    def test_clamp_nas_bordas(self):
        self.assertEqual(anchor_from_cx(-500, 1.0), 0.0)
        self.assertEqual(anchor_from_cx(99999, 1.0), 1.0)


@requires_autoframe
class TestCorrelacao(unittest.TestCase):
    """A correlacao e o que separa o locutor real de um video tocando numa tela do cenario."""

    def test_boca_sincronizada_com_audio(self):
        audio  = [0.0, 0.9, 0.8, 0.0, 0.0, 0.9, 0.7, 0.0]
        mouth  = [0.1, 0.8, 0.9, 0.1, 0.0, 0.7, 0.8, 0.1]
        self.assertGreater(_corr(mouth, audio), 0.8)

    def test_movimento_constante_nao_correlaciona(self):
        audio  = [0.0, 0.9, 0.8, 0.0, 0.0, 0.9, 0.7, 0.0]
        tv     = [0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6]   # variancia zero
        self.assertEqual(_corr(tv, audio), 0.0)

    def test_serie_curta_e_neutra(self):
        self.assertEqual(_corr([1, 2], [1, 2]), 0.0)


if __name__ == "__main__":
    unittest.main()
