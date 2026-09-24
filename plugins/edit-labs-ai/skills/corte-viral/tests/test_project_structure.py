from __future__ import annotations

import unittest
from pathlib import Path

from scripts.utils import PROJECT_ROOT
from scripts.validation import _frontmatter

AGENT_NAMES = {"context-mapper", "clip-hunter", "clip-builder", "clip-deduplicator", "edit-director"}
REVISORES_DE_LLM = {"blind-reviewer", "feed-psychologist", "quality-controller"}


class ProjectStructureTests(unittest.TestCase):
    def test_pacote_nao_traz_revisores_de_llm(self) -> None:
        """A revisão é humana: o pacote não traz revisores de LLM."""
        for nome in REVISORES_DE_LLM:
            self.assertFalse((PROJECT_ROOT / "agentes" / f"{nome}.md").exists(), nome)

    def test_package_ships_every_agent(self) -> None:
        found = set()
        for path in (PROJECT_ROOT / "agentes").glob("*.md"):
            data, errors = _frontmatter(path)
            self.assertEqual(errors, [], f"frontmatter invalido em {path.name}")
            found.add(str((data or {}).get("name")))
        self.assertEqual(found, AGENT_NAMES)

    def test_skill_is_self_contained(self) -> None:
        """A skill e instalada: nada pode depender de ${CLAUDE_PROJECT_DIR}."""
        skill = (PROJECT_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("CLAUDE_PROJECT_DIR", skill)

    def test_motion_is_out_of_scope(self) -> None:
        """Motion e legenda queimada sao da skill motion-vox, nao desta."""
        self.assertFalse((PROJECT_ROOT / "scripts" / "composite_motion.py").exists())
        self.assertEqual(list((PROJECT_ROOT / "schemas").glob("motion-*.json")), [])


if __name__ == "__main__":
    unittest.main()
