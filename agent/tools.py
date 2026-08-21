from dataclasses import dataclass
from typing import Callable

from agent.memory import MemoryStore
from agent.vault import VaultIndex


@dataclass(frozen=True)
class ToolResult:
    spoken: str
    card: dict[str, object]


class ToolRegistry:
    """Deterministic, local tools exposed to the JARVIS agent."""

    def __init__(self, index: VaultIndex, memory: MemoryStore) -> None:
        self.index = index
        self.memory = memory
        self._tools: dict[str, Callable[[dict[str, object]], ToolResult]] = {
            "search_brain": self._search,
            "brief_me": self._brief,
            "plan_day": self._plan,
            "remember": self._remember,
        }

    def execute(self, name: str, arguments: dict[str, object]) -> ToolResult:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name](arguments)

    def _search(self, arguments: dict[str, object]) -> ToolResult:
        items = self.index.search(str(arguments.get("query", "")))
        sources = [
            str(item["filename"])
            for item in items
            if str(item.get("filename", "")).strip()
        ]
        if not sources:
            spoken = "Não encontrei uma fonte correspondente."
        else:
            spoken = f"Encontrei em {', '.join(sources[:3])}."
        return ToolResult(
            spoken,
            {"type": "search_results", "items": items, "sources": sources},
        )

    def _brief(self, arguments: dict[str, object]) -> ToolResult:
        del arguments
        items = sorted(
            self.index.graph()["nodes"],
            key=lambda item: (
                -int(item.get("urgency", 0)),
                -int(item.get("priority", 0)),
            ),
        )[:5]
        return ToolResult(
            f"Há {len(items)} itens que merecem atenção.",
            {"type": "brief", "items": items},
        )

    def _plan(self, arguments: dict[str, object]) -> ToolResult:
        del arguments

        def score(item: dict[str, object]) -> tuple[int, int, int, int]:
            return (
                int(item.get("revenue_impact", 0)),
                int(item.get("customer_impact", 0)),
                int(item.get("urgency", 0)),
                int(item.get("priority", 0)),
            )

        items = sorted(self.index.graph()["nodes"], key=score, reverse=True)[:5]
        return ToolResult(
            f"Priorizei {len(items)} ações para hoje.",
            {"type": "day_plan", "items": items},
        )

    def _remember(self, arguments: dict[str, object]) -> ToolResult:
        fact = str(arguments["fact"])
        path = self.memory.remember(
            fact,
            str(arguments.get("why", "Informação durável solicitada pelo usuário.")),
            str(arguments.get("category", "general")),
            "user",
            arguments.get("confirmed") is True,
        )
        return ToolResult(
            f"Salvei a memória {path.name}.",
            {"type": "memory", "path": str(path), "fact": fact},
        )
