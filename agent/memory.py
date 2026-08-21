import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Callable


class MemoryConfirmationRequired(PermissionError):
    pass


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:64] or "memory"


class MemoryStore:
    def __init__(self, root: Path, today: Callable[[], str] | None = None) -> None:
        self.root = root
        self.today = today or (lambda: date.today().isoformat())

    def remember(self, fact: str, why: str, category: str, source: str, confirmed: bool) -> Path:
        if not confirmed:
            raise MemoryConfirmationRequired("Memory write requires explicit confirmation")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{self.today()}_{_slug(fact)}.md"
        body = (
            f"# Memory\n\nCreated: {self.today()}\nSource: {source}\nCategory: {category}\n\n"
            f"## Fact\n\n{fact.strip()}\n\n## Why it matters\n\n{why.strip()}\n"
        )
        with path.open("x", encoding="utf-8") as handle:
            handle.write(body)
        return path

    def list_memories(self) -> list[dict[str, str]]:
        return [{"path": str(path), "text": path.read_text(encoding="utf-8")} for path in sorted(self.root.glob("*.md"))]
