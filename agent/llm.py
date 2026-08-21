from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        ...


class ModelNotConfigured(RuntimeError):
    code = "MODEL_NOT_CONFIGURED"
