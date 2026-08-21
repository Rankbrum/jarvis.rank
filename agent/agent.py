from dataclasses import dataclass

from agent.llm import LLMProvider
from agent.router import FallbackRouter
from agent.tools import ToolRegistry, ToolResult


@dataclass(frozen=True)
class Turn:
    role: str
    text: str


class JarvisAgent:
    """Maintains a short conversation context around local, deterministic tools."""

    def __init__(
        self,
        tools: ToolRegistry,
        router: FallbackRouter | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self.tools = tools
        self.router = router or FallbackRouter()
        self.llm = llm
        self.history: list[Turn] = []
        self.last_items: list[dict[str, object]] = []

    def respond(self, text: str) -> ToolResult:
        self._append(Turn("user", text))
        if "segundo" in text.casefold() and len(self.last_items) >= 2:
            item = self.last_items[1]
            result = ToolResult(
                f"O segundo é {item['title']}.",
                {"type": "reference", "item": item},
            )
        else:
            intent = self.router.route(text, self.history)
            if intent.kind == "tool" and intent.tool:
                result = self.tools.execute(intent.tool, intent.arguments)
            elif self.llm is not None:
                answer = self.llm.complete(
                    [
                        {"role": turn.role, "content": turn.text}
                        for turn in self.history
                    ]
                )
                result = ToolResult(
                    answer[:240], {"type": "conversation", "text": answer}
                )
            else:
                result = ToolResult(
                    "Estou em modo limitado. Posso buscar, planejar, resumir ou memorizar.",
                    {
                        "type": "limited_mode",
                        "available_tools": [
                            "search_brain",
                            "brief_me",
                            "plan_day",
                            "remember",
                        ],
                    },
                )
        items = result.card.get("items")
        if isinstance(items, list):
            self.last_items = items
        self._append(Turn("assistant", result.spoken))
        return result

    def _append(self, turn: Turn) -> None:
        self.history.append(turn)
        self.history[:] = self.history[-10:]
