"""
JARVIS AI - OpenAI Provider Implementation

Implementation of the AIProvider interface for OpenAI API.
Supports GPT-3.5, GPT-4, and future models.
"""

import os
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime

from .base import (
    AIProvider,
    ChatMessage,
    ToolDefinition,
    ProviderCapability,
    ProviderResponse,
    ProviderStatus,
    MessageRole
)


class OpenAIProvider(AIProvider):
    """OpenAI API Provider implementation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(api_key, base_url)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or "https://api.openai.com/v1"
        self._client = None
        self._models_cache: List[str] = []
        self._last_test_time: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.TEXT,
            ProviderCapability.VISION,  # GPT-4 Vision
            ProviderCapability.FUNCTION_CALLING,
            ProviderCapability.STREAMING,
            ProviderCapability.JSON_MODE
        ]
    
    async def initialize(self) -> bool:
        """Initialize OpenAI client and fetch available models."""
        if not self.api_key:
            return False
        
        try:
            # Lazy import to avoid dependency if not used
            from openai import AsyncOpenAI
            
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # Fetch models
            self._models_cache = await self.get_available_models()
            self._initialized = True
            return True
            
        except ImportError:
            print("OpenAI library not installed. Run: pip install openai")
            return False
        except Exception as e:
            print(f"Failed to initialize OpenAI provider: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Fetch available OpenAI models."""
        if self._models_cache and self._last_test_time:
            # Cache for 5 minutes
            if (datetime.now() - self._last_test_time).total_seconds() < 300:
                return self._models_cache
        
        if not self._client:
            return []
        
        try:
            models = await self._client.models.list()
            model_list = [m.id for m in models.data]
            
            # Filter to common chat models
            chat_models = [
                m for m in model_list 
                if any(x in m.lower() for x in ['gpt-', 'o1-'])
            ]
            
            self._models_cache = chat_models or model_list
            self._last_test_time = datetime.now()
            return self._models_cache
            
        except Exception:
            # Return default models if API fails
            return [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo"
            ]
    
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
        """Send chat completion request to OpenAI."""
        if not self._client:
            raise RuntimeError("OpenAI provider not initialized")
        
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            if msg.name:
                openai_msg["name"] = msg.name
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            openai_messages.append(openai_msg)
        
        # Convert tools to OpenAI format
        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                }
                for tool in tools
            ]
        
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=openai_tools,
                stream=False,
                **kwargs
            )
            
            choice = response.choices[0]
            
            # Extract tool calls if present
            tool_calls = None
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in choice.message.tool_calls
                ]
            
            return ProviderResponse(
                content=choice.message.content or "",
                model=model,
                provider=self.name,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=choice.finish_reason,
                tool_calls=tool_calls,
                raw_response=response.model_dump()
            )
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    async def chat_completion_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat completion from OpenAI."""
        if not self._client:
            raise RuntimeError("OpenAI provider not initialized")
        
        # Convert messages
        openai_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        
        # Convert tools
        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                }
                for tool in tools
            ]
        
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=openai_tools,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {str(e)}")
    
    async def test_connection(self) -> ProviderStatus:
        """Test connection to OpenAI API."""
        start_time = time.time()
        
        if not self.api_key:
            return ProviderStatus(
                name=self.name,
                connected=False,
                error="API key not configured"
            )
        
        try:
            if not self._client:
                await self.initialize()
            
            # Try to fetch models as a connectivity test
            models = await self.get_available_models()
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ProviderStatus(
                name=self.name,
                connected=True,
                models=models[:10],  # Return first 10 models
                capabilities=self.capabilities,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            return ProviderStatus(
                name=self.name,
                connected=False,
                error=str(e)
            )
    
    async def shutdown(self) -> None:
        """Cleanup OpenAI client."""
        if self._client:
            # AsyncOpenAI doesn't have explicit cleanup
            pass
        self._initialized = False
