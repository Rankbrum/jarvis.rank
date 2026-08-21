import tempfile
import unittest
from pathlib import Path

from agent.memory import MemoryConfirmationRequired, MemoryStore


class MemoryTests(unittest.TestCase):
    def test_memory_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            application_root = Path(tmp)
            memory_root = application_root / "memory"
            store = MemoryStore(memory_root, application_root=application_root)
            with self.assertRaises(MemoryConfirmationRequired):
                store.remember("Priorizar vendas", "Impacta receita", "priority", "user", confirmed=False)
            self.assertEqual(list(memory_root.glob("*.md")), [])

    def test_confirmed_memory_uses_expected_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            application_root = Path(tmp)
            memory_root = application_root / "memory"
            store = MemoryStore(memory_root, application_root=application_root, today=lambda: "2026-08-21")
            path = store.remember("Priorizar RANKBRUM ONE AI", "Projeto central", "priority", "user", True)
            text = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "2026-08-21_priorizar-rankbrum-one-ai.md")
            self.assertIn("## Fact\n\nPriorizar RANKBRUM ONE AI", text)
            self.assertIn("## Why it matters\n\nProjeto central", text)

    def test_memory_rejects_destination_outside_application_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            application_root = Path(tmp)
            destination = application_root / "other"
            with self.assertRaises(ValueError):
                MemoryStore(destination, application_root=application_root)
            self.assertFalse(destination.exists())
            self.assertFalse((application_root / "memory").exists())
