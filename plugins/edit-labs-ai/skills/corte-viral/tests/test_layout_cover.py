# -*- coding: utf-8 -*-
"""O vertical nunca divide a tela: todo segmento sai num crop único (cover), mesmo que o plano diga 'split'."""
import sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.render as R


class TestSemTelaDividida(unittest.TestCase):
    def _comando(self, layout):
        visto = {}

        def falso(cmd, *a, **k):
            visto["cmd"] = cmd

        seg = {"source_start": 0.0, "source_end": 2.0, "layout": layout, "crop_anchor_x": 0.4}
        with mock.patch.object(R, "run_command", side_effect=falso):
            R._render_segment("ffmpeg", Path("in.mp4"), Path("out.mp4"), seg, {"width": 1080, "height": 1920},
                              has_audio=False, src_w=1920, src_h=1080)
        return " ".join(visto["cmd"])

    def test_plano_com_split_sai_em_cover(self):
        cmd = self._comando("split")
        self.assertNotIn("vstack", cmd)
        self.assertNotIn("-filter_complex", cmd)
        self.assertIn("-vf", cmd)

    def test_cover_e_um_filtro_simples(self):
        vf = R._video_filter(1080, 1920, 0.5, 1.0)
        self.assertNotIn("vstack", vf)
        self.assertIn("crop=1080:1920", vf)

    def test_render_nao_tem_split(self):
        self.assertFalse(hasattr(R, "split_geometry"))
        self.assertFalse(hasattr(R, "_split_filter"))


if __name__ == "__main__":
    unittest.main()
