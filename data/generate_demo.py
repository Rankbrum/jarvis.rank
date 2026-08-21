import json
import random
from pathlib import Path


SEED = 777
CATEGORIES = ("project", "lead", "task", "meeting", "proposal", "note", "concept", "invoice")


def generate_dataset(seed: int = SEED) -> dict[str, list[dict[str, object]]]:
    rng = random.Random(seed)
    documents: list[dict[str, object]] = []
    for index in range(48):
        category = CATEGORIES[index % len(CATEGORIES)]
        documents.append(
            {
                "id": f"demo-{index:03d}",
                "title": f"{category.title()} {index + 1}",
                "filename": f"{category}-{index + 1}.md",
                "path": f"demo/{category}/{index + 1}.md",
                "type": category,
                "preview": f"Registro fictício {index + 1} para operação demonstrativa da RANKBRUM ONE AI.",
                "modified_at": f"2026-08-{(index % 20) + 1:02d}T09:00:00Z",
                "tags": [category, "demo"],
                "priority": rng.randint(1, 5),
                "revenue_impact": rng.randint(0, 100),
                "customer_impact": rng.randint(0, 100),
                "urgency": rng.randint(0, 100),
            }
        )
    edges = [
        {"source": documents[index]["id"], "target": documents[(index * 7 + 3) % len(documents)]["id"]}
        for index in range(len(documents))
        if documents[index]["id"] != documents[(index * 7 + 3) % len(documents)]["id"]
    ]
    return {"documents": documents, "edges": edges}


def write_dataset(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(generate_dataset(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_dataset(Path(__file__).parent / "demo" / "jarvis_demo.json")
