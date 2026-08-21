import tempfile
import unittest
from pathlib import Path

from agent.memory import MemoryConfirmationRequired, MemoryStore
from agent.tools import ToolRegistry
from agent.vault import VaultIndex


class ToolTests(unittest.TestCase):
    def setUp(self):
        docs = [
            {
                "id": f"n{i}",
                "title": f"Projeto {i}",
                "filename": f"p{i}.md",
                "path": f"demo/p{i}.md",
                "type": "project",
                "preview": "RANKBRUM vendas",
                "priority": i,
                "revenue_impact": 100 - i,
                "customer_impact": 50,
                "urgency": i,
            }
            for i in range(8)
        ]
        self.index = VaultIndex(source_documents=docs)
        self.index.build()

    def make_tools(self, tmp):
        application_root = Path(tmp)
        return ToolRegistry(
            self.index,
            MemoryStore(
                application_root / "memory",
                application_root=application_root,
                today=lambda: "2026-08-21",
            ),
        )

    def test_search_names_real_sources_and_card_is_detailed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.make_tools(tmp).execute("search_brain", {"query": "RANKBRUM"})
            self.assertIn("p0.md", result.spoken)
            self.assertGreater(len(result.card["items"]), 1)
            self.assertEqual(result.card["sources"][0], "p0.md")
            self.assertNotEqual(result.spoken, str(result.card))

    def test_plan_day_never_returns_more_than_five_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.make_tools(tmp).execute("plan_day", {})
            self.assertLessEqual(len(result.card["items"]), 5)

    def test_registry_exposes_only_explicit_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = self.make_tools(tmp)
            for name in ("search_brain", "brief_me", "plan_day", "remember"):
                self.assertIn(name, tools._tools)
            with self.assertRaises(KeyError):
                tools.execute("send_email", {})

    def test_remember_requires_confirmation_and_reports_saved_fact(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = self.make_tools(tmp)
            with self.assertRaises(MemoryConfirmationRequired):
                tools.execute("remember", {"fact": "RANKBRUM é prioridade", "confirmed": False})
            memory_root = Path(tmp) / "memory"
            self.assertEqual(list(memory_root.glob("*.md")), [])

            result = tools.execute(
                "remember",
                {
                    "fact": "RANKBRUM é prioridade",
                    "why": "Foco do trimestre",
                    "category": "priority",
                    "confirmed": True,
                },
            )
            self.assertIn("Salvei a memória", result.spoken)
            self.assertIn("2026-08-21_rankbrum-e-prioridade.md", result.spoken)
            self.assertEqual(result.card["fact"], "RANKBRUM é prioridade")
            self.assertEqual(len(list(memory_root.glob("*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
