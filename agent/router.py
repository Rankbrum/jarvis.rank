import re
from dataclasses import dataclass, field
from typing import Sequence


MEMORY_COMMAND_RE = re.compile(
    r"^\s*(?:lembre|memorize|guarde)(?:-se)?\s+(?:que\s+)?(?P<fact>\S(?:.*\S)?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Intent:
    kind: str
    tool: str | None = None
    arguments: dict[str, object] = field(default_factory=dict)


class FallbackRouter:
    """Routes explicit Portuguese requests to the deterministic local tools."""

    def route(self, text: str, history: Sequence[object]) -> Intent:
        del history
        normalized = text.casefold().strip()
        memory_match = MEMORY_COMMAND_RE.match(text)
        if memory_match and memory_match["fact"].casefold() != "que":
            fact = memory_match["fact"]
            return Intent("tool", "remember", {"fact": fact, "confirmed": True})
        if re.search(r"\b(planeje|prioridades|plano do dia)\b", normalized):
            return Intent("tool", "plan_day")
        if re.search(r"\b(resumo|brief|atenção hoje)\b", normalized):
            return Intent("tool", "brief_me")
        if re.search(r"\b(procure|busque|documento|proposta|projeto)\b", normalized):
            return Intent("tool", "search_brain", {"query": text})
        return Intent("conversation")
