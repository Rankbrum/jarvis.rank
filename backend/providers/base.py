"""
JARVIS AI - Provider Layer

Abstract base classes and interfaces for AI Providers.
All providers must implement this interface to ensure compatibility.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Roles for chat messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Represents a chat message in the conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ToolDefinition(BaseModel):
    """Definition of a tool/function that the model can call."""
    name: str
    description: str
    parameters: Dict[str, Any]


class ProviderCapability(str, Enum):
    """Capabilities supported by providers."""
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"


class ProviderResponse(BaseModel):
    """Standardized response from any provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    raw_response: Optional[Dict[str, Any]] = None


class ProviderStatus(BaseModel):
    """Status information for a provider."""
    name: str
    connected: bool
    models: List[str] = []
    capabilities: List[ProviderCapability] = []
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class AIProvider(ABC):
    """
    Abstract base class for all AI Providers.
    
    All providers (OpenAI, Anthropic, Google, etc.) must implement this interface.
    This ensures the Model Router can work with any provider interchangeably.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[ProviderCapability]:
        """Return list of capabilities supported by this provider."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider (validate credentials, fetch models, etc.).
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Return list of available model names for this provider."""
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = False,
        **kwargs
    ) -> ProviderResponse:
        """
        Send a chat completion request to the provider.
        
        Args:
            messages: List of chat messages
            model: Model name to use
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            tools: List of tools/functions available
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ProviderResponse with standardized format
        """
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response.
        
        Yields:
            Chunks of text as they are generated
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> ProviderStatus:
        """
        Test the connection to the provider.
        
        Returns:
            ProviderStatus with connection details
        """
        pass
    
    async def shutdown(self) -> None:
        """Cleanup resources when shutting down."""
        self._initialized = False
    
    def is_initialized(self) -> bool:
        """Check if provider is initialized and ready."""
        return self._initialized
