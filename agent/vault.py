import hashlib
import re
from collections import deque
from pathlib import Path
from typing import Iterable

from agent.security import SecurityError, is_supported_file, validate_source_path


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def _id_for(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


class VaultIndex:
    def __init__(
        self,
        source_documents: Iterable[dict[str, object]] = (),
        roots: Iterable[Path] = (),
    ) -> None:
        self.source_documents = list(source_documents)
        self.roots = tuple(Path(root) for root in roots)
        self.nodes: dict[str, dict[str, object]] = {}
        self.edges: set[tuple[str, str]] = set()

    @classmethod
    def from_roots(cls, roots: Iterable[Path]) -> "VaultIndex":
        return cls(roots=roots)

    def build(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self._add_source_documents()
        self._add_root_documents()
        self._add_wikilink_edges()

    def add_edges(self, edges: Iterable[dict[str, object]]) -> None:
        for edge in edges:
            source = str(edge["source"])
            target = str(edge["target"])
            if source in self.nodes and target in self.nodes and source != target:
                self.edges.add((source, target))

    def search(self, query: str, limit: int = 8) -> list[dict[str, object]]:
        terms = [term.casefold() for term in query.split() if term.strip()]
        if not terms or limit <= 0:
            return []

        scored: list[tuple[int, dict[str, object]]] = []
        for node in self.nodes.values():
            haystack = " ".join(
                str(node.get(field, "")) for field in ("title", "preview", "text")
            ).casefold()
            score = sum(haystack.count(term) for term in terms)
            if score:
                scored.append((score, dict(node)))
        return [
            node
            for _, node in sorted(
                scored, key=lambda pair: (-pair[0], str(pair[1]["title"]).casefold())
            )[:limit]
        ]

    def graph(self) -> dict[str, list[dict[str, object]]]:
        degrees = {node_id: 0 for node_id in self.nodes}
        relationships = self._relationships()
        for source, target in self.edges:
            degrees[source] += 1
            degrees[target] += 1
        nodes = [
            {**node, "degree": degrees[node_id], **relationships[node_id]}
            for node_id, node in self.nodes.items()
        ]
        edges = [{"source": source, "target": target} for source, target in sorted(self.edges)]
        return {"nodes": nodes, "edges": edges}

    def node(self, node_id: str) -> dict[str, object] | None:
        if node_id not in self.nodes:
            return None
        return {**self.nodes[node_id], **self._relationships()[node_id]}

    def shortest_path(self, start: str, end: str) -> list[str]:
        if start not in self.nodes or end not in self.nodes:
            return []
        adjacency = {node_id: set() for node_id in self.nodes}
        for source, target in self.edges:
            adjacency[source].add(target)
            adjacency[target].add(source)
        queue = deque([(start, [start])])
        seen = {start}
        while queue:
            current, path = queue.popleft()
            if current == end:
                return path
            for neighbor in sorted(adjacency[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def _add_source_documents(self) -> None:
        for item in self.source_documents:
            node = dict(item)
            self.nodes[str(node["id"])] = node

    def _add_root_documents(self) -> None:
        for root in self.roots:
            resolved_root = root.resolve(strict=True)
            for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
                try:
                    safe_path = validate_source_path(path, (resolved_root,))
                except SecurityError:
                    continue
                if not is_supported_file(safe_path):
                    continue
                relative = safe_path.relative_to(resolved_root).as_posix()
                node_id = _id_for(f"{resolved_root.as_posix()}:{relative}")
                is_pdf = safe_path.suffix.lower() == ".pdf"
                text = "" if is_pdf else safe_path.read_text(encoding="utf-8", errors="replace")
                self.nodes[node_id] = {
                    "id": node_id,
                    "title": safe_path.stem,
                    "filename": safe_path.name,
                    "path": str(safe_path),
                    "type": safe_path.suffix.lower().lstrip("."),
                    "preview": text[:280],
                    "text": text,
                    "modified_at": safe_path.stat().st_mtime,
                    "tags": [],
                    "outgoing_links": WIKILINK_RE.findall(text),
                    "extraction_status": "metadata_only" if is_pdf else "complete",
                }

    def _add_wikilink_edges(self) -> None:
        by_title: dict[str, str] = {}
        for node_id, node in self.nodes.items():
            by_title.setdefault(str(node.get("title", "")).strip().casefold(), node_id)
        for source_id, node in self.nodes.items():
            for title in node.get("outgoing_links", []):
                target_id = by_title.get(str(title).strip().casefold())
                if target_id and target_id != source_id:
                    self.edges.add((source_id, target_id))

    def _relationships(self) -> dict[str, dict[str, list[str]]]:
        relationships = {
            node_id: {"outgoing": [], "incoming": []} for node_id in self.nodes
        }
        for source, target in sorted(self.edges):
            relationships[source]["outgoing"].append(target)
            relationships[target]["incoming"].append(source)
        return relationships
