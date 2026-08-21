import tempfile
import unittest
from pathlib import Path

from agent.agent import JarvisAgent
from agent.memory import MemoryStore
from agent.router import FallbackRouter
from agent.tools import ToolRegistry
from agent.vault import VaultIndex


class RecordingProvider:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.messages: list[dict[str, str]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return self.answer


class AgentTests(unittest.TestCase):
    def setUp(self) -> None:
        documents = [
            {
                "id": f"n{number}",
                "title": f"Projeto {number}",
                "filename": f"p{number}.md",
                "path": f"demo/p{number}.md",
                "type": "project",
                "preview": "projeto",
                "priority": number,
            }
            for number in range(4)
        ]
        self.index = VaultIndex(source_documents=documents)
        self.index.build()

    def make_agent(self, root: Path, *, llm=None) -> JarvisAgent:
        return JarvisAgent(
            ToolRegistry(self.index, MemoryStore(application_root=root)), llm=llm
        )

    def test_router_distinguishes_search_memory_plan_and_conversation(self):
        router = FallbackRouter()
        self.assertEqual(router.route("procure a proposta", []).tool, "search_brain")
        memory_intent = router.route("lembre que o ONE AI é prioridade", [])
        self.assertEqual(memory_intent.tool, "remember")
        self.assertEqual(memory_intent.arguments["confirmed"], True)
        self.assertEqual(router.route("planeje meu dia", []).tool, "plan_day")
        self.assertEqual(router.route("bom dia", []).kind, "conversation")

    def test_router_rejects_negated_ambiguous_and_empty_memory_requests(self):
        router = FallbackRouter()
        for request in (
            "Não memorize isto.",
            "Talvez lembre que isto é importante.",
            "lembre que",
            "guarde",
        ):
            self.assertEqual(router.route(request, []).kind, "conversation")

    def test_ordinary_conversation_does_not_create_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.make_agent(root).respond("O ONE AI é prioridade")
            self.assertEqual(result.card["type"], "limited_mode")
            self.assertEqual(list((root / "memory").glob("*.md")), [])

    def test_history_is_capped_and_follow_up_resolves_second_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(Path(tmp))
            agent.respond("procure projeto")
            result = agent.respond("e o segundo?")
            for number in range(12):
                agent.respond(f"mensagem {number}")
            self.assertIn("Projeto 1", result.spoken)
            self.assertLessEqual(len(agent.history), 10)

    def test_limited_mode_explains_available_deterministic_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.make_agent(Path(tmp)).respond("como está o tempo?")
            self.assertEqual(result.card["type"], "limited_mode")
            self.assertEqual(
                result.card["available_tools"],
                ["search_brain", "brief_me", "plan_day", "remember"],
            )

    def test_configured_llm_receives_history_and_returns_bounded_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = RecordingProvider("resposta " * 100)
            result = self.make_agent(Path(tmp), llm=provider).respond("bom dia")
            self.assertEqual(len(result.spoken), 240)
            self.assertEqual(result.card["type"], "conversation")
            self.assertEqual(provider.messages[0]["role"], "system")
            self.assertIn("Responda em português do Brasil", provider.messages[0]["content"])
            self.assertEqual(provider.messages[1], {"role": "user", "content": "bom dia"})


if __name__ == "__main__":
    unittest.main()
