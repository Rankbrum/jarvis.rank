import re
from dataclasses import dataclass, field
from typing import Sequence


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
        if re.search(r"\b(lembre|memorize|guarde)\b", normalized):
            fact = re.sub(
                r"^.*?\b(?:lembre|memorize|guarde)(?:-se)?\s+(?:que\s+)?",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()
            return Intent("tool", "remember", {"fact": fact, "confirmed": True})
        if re.search(r"\b(planeje|prioridades|plano do dia)\b", normalized):
            return Intent("tool", "plan_day")
        if re.search(r"\b(resumo|brief|atenção hoje)\b", normalized):
            return Intent("tool", "brief_me")
        if re.search(r"\b(procure|busque|documento|proposta|projeto)\b", normalized):
            return Intent("tool", "search_brain", {"query": text})
        return Intent("conversation")
