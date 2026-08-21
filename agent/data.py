import os


_DEMO_VALUE = os.getenv("JARVIS_DEMO", "1").strip().lower()
_DEMO_MODE = _DEMO_VALUE not in {"0", "false", "off", "no"}


def is_demo_mode() -> bool:
    return _DEMO_MODE
