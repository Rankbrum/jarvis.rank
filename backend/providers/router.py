"""
JARVIS AI - Model Router

Intelligent routing of requests to appropriate AI models based on:
- Strategy (AUTO, BEST_QUALITY, FASTEST, CHEAPEST, etc.)
- Capabilities required
- Availability
- Cost considerations
- User preferences
"""

from typing import Optional, List, Dict, Any, Type
from enum import Enum
from pydantic import BaseModel, Field
import asyncio
import time

from .base import (
    AIProvider,
    ChatMessage,
    ToolDefinition,
    ProviderCapability,
    ProviderResponse,
    ProviderStatus
)


class RoutingStrategy(str, Enum):
    """Model selection strategies."""
    AUTO = "auto"  # Intelligent selection based on task
    BEST_QUALITY = "best_quality"  # Highest quality regardless of cost/speed
    FASTEST = "fastest"  # Lowest latency
    CHEAPEST = "cheapest"  # Lowest cost
    FREE_FIRST = "free_first"  # Try free tiers first
    LOCAL_ONLY = "local_only"  # Only local models (Ollama, etc.)
    MANUAL = "manual"  # User-specified model


class ModelInfo(BaseModel):
    """Information about a model."""
    name: str
    provider: str
    capabilities: List[ProviderCapability]
    max_context_length: int = 128000
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    avg_latency_ms: float = 1000.0
    is_local: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False


class RouterConfig(BaseModel):
    """Configuration for the Model Router."""
    default_strategy: RoutingStrategy = RoutingStrategy.AUTO
    fallback_enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 60
    preferred_providers: List[str] = []
    blocked_models: List[str] = []
    cost_limit_per_request: float = 1.0
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300


class ModelRouter:
    """
    Intelligent router for selecting the best AI model for a given task.
    
    Features:
    - Multiple routing strategies
    - Automatic fallback on failure
    - Capability-based selection
    - Cost and latency optimization
    - Provider health monitoring
    """
    
    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()
        self._providers: Dict[str, AIProvider] = {}
        self._model_registry: Dict[str, ModelInfo] = {}
        self._provider_health: Dict[str, bool] = {}
        self._latency_cache: Dict[str, float] = {}
        self._initialized = False
    
    def register_provider(self, provider: AIProvider) -> None:
        """Register an AI provider with the router."""
        self._providers[provider.name] = provider
        self._provider_health[provider.name] = False
    
    def unregister_provider(self, provider_name: str) -> None:
        """Unregister a provider from the router."""
        if provider_name in self._providers:
            del self._providers[provider_name]
        if provider_name in self._provider_health:
            del self._provider_health[provider_name]
    
    async def initialize(self) -> None:
        """Initialize all registered providers and build model registry."""
        for provider_name, provider in self._providers.items():
            try:
                success = await provider.initialize()
                self._provider_health[provider_name] = success
                
                if success:
                    models = await provider.get_available_models()
                    for model in models:
                        self._model_registry[model] = ModelInfo(
                            name=model,
                            provider=provider_name,
                            capabilities=provider.capabilities,
                            supports_vision=ProviderCapability.VISION in provider.capabilities,
                            supports_function_calling=ProviderCapability.FUNCTION_CALLING in provider.capabilities
                        )
                
            except Exception as e:
                print(f"Failed to initialize provider {provider_name}: {e}")
                self._provider_health[provider_name] = False
        
        self._initialized = True
    
    async def select_model(
        self,
        strategy: Optional[RoutingStrategy] = None,
        required_capabilities: Optional[List[ProviderCapability]] = None,
        messages: Optional[List[ChatMessage]] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> Optional[ModelInfo]:
        """
        Select the best model based on strategy and requirements.
        
        Args:
            strategy: Routing strategy (uses default if None)
            required_capabilities: Capabilities that must be supported
            messages: Chat messages to analyze for complexity
            tools: Tools that need function calling support
            **kwargs: Additional parameters
            
        Returns:
            ModelInfo for the selected model, or None if no suitable model found
        """
        if not self._initialized:
            await self.initialize()
        
        strategy = strategy or self.config.default_strategy
        required_caps = required_capabilities or []
        
        # Add function calling if tools are provided
        if tools and ProviderCapability.FUNCTION_CALLING not in required_caps:
            required_caps.append(ProviderCapability.FUNCTION_CALLING)
        
        # Filter models by capabilities
        candidate_models = self._filter_by_capabilities(required_caps)
        
        if not candidate_models:
            return None
        
        # Apply strategy-specific selection
        if strategy == RoutingStrategy.BEST_QUALITY:
            return self._select_best_quality(candidate_models)
        elif strategy == RoutingStrategy.FASTEST:
            return await self._select_fastest(candidate_models)
        elif strategy == RoutingStrategy.CHEAPEST:
            return self._select_cheapest(candidate_models)
        elif strategy == RoutingStrategy.LOCAL_ONLY:
            return self._select_local_only(candidate_models)
        elif strategy == RoutingStrategy.FREE_FIRST:
            return self._select_free_first(candidate_models)
        else:  # AUTO
            return await self._select_auto(candidate_models, messages, tools)
    
    def _filter_by_capabilities(
        self,
        required_capabilities: List[ProviderCapability]
    ) -> List[ModelInfo]:
        """Filter models by required capabilities."""
        candidates = []
        
        for model_info in self._model_registry.values():
            # Skip blocked models
            if model_info.name in self.config.blocked_models:
                continue
            
            # Skip unhealthy providers
            if not self._provider_health.get(model_info.provider, False):
                continue
            
            # Check capabilities
            has_all_caps = all(
                cap in model_info.capabilities
                for cap in required_capabilities
            )
            
            if has_all_caps:
                candidates.append(model_info)
        
        return candidates
    
    def _select_best_quality(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """Select model with highest quality (typically largest/most capable)."""
        # Priority order for quality
        quality_priority = [
            'gpt-4o', 'gpt-4-turbo', 'gpt-4',
            'claude-3-opus', 'claude-3-sonnet',
            'gemini-pro-1.5', 'gemini-pro'
        ]
        
        for priority_model in quality_priority:
            for model in models:
                if priority_model in model.name.lower():
                    return model
        
        # If no priority model found, return first available
        return models[0] if models else None
    
    async def _select_fastest(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """Select model with lowest latency."""
        # Update latency cache for models we haven't measured recently
        await self._update_latency_cache(models)
        
        # Sort by latency
        sorted_models = sorted(
            models,
            key=lambda m: self._latency_cache.get(m.name, float('inf'))
        )
        
        return sorted_models[0] if sorted_models else None
    
    def _select_cheapest(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """Select model with lowest cost."""
        # Sort by total cost (input + output)
        sorted_models = sorted(
            models,
            key=lambda m: m.input_cost_per_1k + m.output_cost_per_1k
        )
        
        return sorted_models[0] if sorted_models else None
    
    def _select_local_only(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """Select only local models."""
        local_models = [m for m in models if m.is_local]
        return local_models[0] if local_models else None
    
    def _select_free_first(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """Try free tier models first."""
        # Models with zero or very low cost
        free_models = [
            m for m in models
            if m.input_cost_per_1k == 0 and m.output_cost_per_1k == 0
        ]
        
        if free_models:
            return free_models[0]
        
        # If no completely free models, return cheapest
        return self._select_cheapest(models)
    
    async def _select_auto(
        self,
        models: List[ModelInfo],
        messages: Optional[List[ChatMessage]],
        tools: Optional[List[ToolDefinition]]
    ) -> Optional[ModelInfo]:
        """
        Intelligently select model based on task complexity.
        
        Simple tasks → faster/cheaper models
        Complex tasks → higher quality models
        """
        if not models:
            return None
        
        # Analyze task complexity
        complexity = self._analyze_task_complexity(messages, tools)
        
        if complexity == "simple":
            # Use fastest/cheapest for simple tasks
            return await self._select_fastest(models)
        elif complexity == "complex":
            # Use best quality for complex tasks
            return self._select_best_quality(models)
        else:  # medium
            # Balance between speed and quality
            return self._select_cheapest(models)
    
    def _analyze_task_complexity(
        self,
        messages: Optional[List[ChatMessage]],
        tools: Optional[List[ToolDefinition]]
    ) -> str:
        """Analyze task complexity based on messages and tools."""
        if not messages:
            return "medium"
        
        # Count tokens (rough estimate)
        total_length = sum(len(msg.content) for msg in messages)
        
        # Check for complex indicators
        has_tools = bool(tools)
        is_long = total_length > 2000
        has_code = any("```" in msg.content for msg in messages)
        has_multiple_turns = len(messages) > 4
        
        if has_tools or is_long or has_code or has_multiple_turns:
            return "complex"
        elif total_length < 200 and len(messages) <= 2:
            return "simple"
        else:
            return "medium"
    
    async def _update_latency_cache(self, models: List[ModelInfo]) -> None:
        """Update latency cache for models."""
        now = time.time()
        
        for model in models:
            # Only update if cache is stale (> 5 minutes old)
            if model.name not in self._latency_cache:
                # Estimate based on provider
                provider = model.provider
                if provider == "openai":
                    self._latency_cache[model.name] = 800
                elif provider == "anthropic":
                    self._latency_cache[model.name] = 1200
                elif provider == "google":
                    self._latency_cache[model.name] = 1000
                else:
                    self._latency_cache[model.name] = 1500
    
    async def execute_with_fallback(
        self,
        messages: List[ChatMessage],
        strategy: Optional[RoutingStrategy] = None,
        required_capabilities: Optional[List[ProviderCapability]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ProviderResponse:
        """
        Execute chat completion with automatic fallback on failure.
        
        Tries multiple models/providers until success or max retries reached.
        """
        retries = 0
        last_error = None
        attempted_models = set()
        
        while retries < self.config.max_retries:
            # Select model
            model_info = await self.select_model(
                strategy=strategy,
                required_capabilities=required_capabilities,
                messages=messages,
                tools=tools
            )
            
            if not model_info:
                raise RuntimeError("No suitable model available")
            
            # Skip already attempted models
            if model_info.name in attempted_models:
                retries += 1
                continue
            
            attempted_models.add(model_info.name)
            
            # Get provider
            provider = self._providers.get(model_info.provider)
            if not provider:
                retries += 1
                continue
            
            try:
                # Execute with timeout
                response = await asyncio.wait_for(
                    provider.chat_completion(
                        messages=messages,
                        model=model_info.name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tools=tools,
                        **kwargs
                    ),
                    timeout=self.config.timeout_seconds
                )
                
                # Update latency cache
                self._latency_cache[model_info.name] = (
                    response.usage.get("total_tokens", 0) * 0.5  # Rough estimate
                )
                
                return response
                
            except Exception as e:
                last_error = e
                print(f"Model {model_info.name} failed: {e}")
                self._provider_health[model_info.provider] = False
                retries += 1
        
        raise RuntimeError(
            f"All model attempts failed after {retries} retries. Last error: {last_error}"
        )
    
    async def get_provider_status(self) -> List[ProviderStatus]:
        """Get status of all registered providers."""
        statuses = []
        
        for provider_name, provider in self._providers.items():
            status = await provider.test_connection()
            statuses.append(status)
            self._provider_health[provider_name] = status.connected
        
        return statuses
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of all available models."""
        return list(self._model_registry.values())
    
    async def shutdown(self) -> None:
        """Shutdown all providers."""
        for provider in self._providers.values():
            await provider.shutdown()
        self._initialized = False
