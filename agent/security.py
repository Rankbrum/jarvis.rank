from pathlib import Path
from typing import Sequence


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}
IGNORED_PARTS = {".git", "node_modules", "__pycache__", ".cache"}


class SecurityError(ValueError):
    pass


def validate_source_path(candidate: Path, roots: Sequence[Path]) -> Path:
    resolved = candidate.resolve(strict=False)
    allowed = [root.resolve(strict=True) for root in roots]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise SecurityError("UNSAFE_PATH: path is outside configured read-only roots")
    return resolved


def is_supported_file(path: Path, max_bytes: int = 2_097_152) -> bool:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    if any(part in IGNORED_PARTS or (part.startswith(".") and part not in {".", ".."}) for part in path.parts):
        return False
    try:
        return path.is_file() and path.stat().st_size <= max_bytes
    except OSError:
        return False
