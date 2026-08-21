import os
import json
from pathlib import Path


_DEMO_VALUE = os.getenv("JARVIS_DEMO", "1").strip().lower()
_DEMO_MODE = _DEMO_VALUE not in {"0", "false", "off", "no"}


def is_demo_mode() -> bool:
    return _DEMO_MODE


class DataGateway:
    def __init__(self, demo_path: Path | None = None) -> None:
        self.demo_path = demo_path or Path(__file__).parents[1] / "data" / "demo" / "jarvis_demo.json"

    def load_dataset(self) -> dict[str, list[dict[str, object]]]:
        if not is_demo_mode():
            raise RuntimeError("Real data sources require explicit configuration")
        return json.loads(self.demo_path.read_text(encoding="utf-8"))

    def documents(self) -> list[dict[str, object]]:
        return list(self.load_dataset()["documents"])

    def configured_roots(self, config_path: Path | None = None) -> tuple[Path, ...]:
        if is_demo_mode():
            return ()
        path = config_path or Path(__file__).parents[1] / "config" / "sources.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        roots: list[Path] = []
        for source in payload.get("sources", []):
            if source.get("enabled") is True and source.get("read_only") is True:
                candidate = Path(str(source["path"])).expanduser().resolve(strict=True)
                if not candidate.is_dir():
                    raise RuntimeError(f"DATA_SOURCE_UNAVAILABLE: {candidate}")
                roots.append(candidate)
        return tuple(roots)
