"""
JARVIS AI - Providers Package

Provider layer for AI model integration.
Supports multiple providers with automatic fallback and routing.
"""

from .base import (
    AIProvider,
    ChatMessage,
    ToolDefinition,
    ProviderCapability,
    ProviderResponse,
    ProviderStatus,
    MessageRole
)
from .router import (
    ModelRouter,
    RoutingStrategy,
    ModelInfo,
    RouterConfig
)

# Import providers as they are implemented
# from .openai_provider import OpenAIProvider
# from .anthropic_provider import AnthropicProvider
# from .google_provider import GoogleProvider
# from .ollama_provider import OllamaProvider

__all__ = [
    # Base classes
    "AIProvider",
    "ChatMessage",
    "ToolDefinition",
    "ProviderCapability",
    "ProviderResponse",
    "ProviderStatus",
    "MessageRole",
    # Router
    "ModelRouter",
    "RoutingStrategy",
    "ModelInfo",
    "RouterConfig",
]