# JARVIS AI - Provider Layer Documentation

## Overview

The Provider Layer is a critical component of JARVIS AI that abstracts AI model providers, enabling seamless integration with multiple AI services while maintaining a unified interface.

## Architecture

```
┌─────────────────┐
│  Jarvis Core    │
│  (Orchestrator) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Model Router   │
│  (Intelligent   │
│   Selection)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Provider Adapter│
│   (Interface)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────┐
    ▼         ▼          ▼         ▼
┌────────┐ ┌────────┐ ┌──────┐ ┌────────┐
│ OpenAI │ │Anthropic│ │Google│ │ Ollama │
│  GPT   │ │ Claude  │ │Gemini│ │ Local  │
└────────┘ └────────┘ └──────┘ └────────┘
```

## Components

### 1. Base Classes (`base.py`)

#### `AIProvider` (Abstract Base Class)
All AI providers must implement this interface:

```python
class AIProvider(ABC):
    @property
    def name(self) -> str: ...
    
    @property
    def capabilities(self) -> List[ProviderCapability]: ...
    
    async def initialize(self) -> bool: ...
    async def get_available_models(self) -> List[str]: ...
    async def chat_completion(...) -> ProviderResponse: ...
    async def chat_completion_stream(...) -> AsyncIterator[str]: ...
    async def test_connection(self) -> ProviderStatus: ...
```

#### Key Data Models

- **`ChatMessage`**: Standardized message format
- **`ToolDefinition`**: Function/tool schema
- **`ProviderResponse`**: Unified response format
- **`ProviderStatus`**: Connection health status
- **`ProviderCapability`**: Supported features (TEXT, VISION, AUDIO, etc.)

### 2. Model Router (`router.py`)

Intelligent routing system that selects the best model based on:

#### Routing Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `AUTO` | Intelligent selection based on task complexity | Default |
| `BEST_QUALITY` | Highest quality regardless of cost | Complex tasks |
| `FASTEST` | Lowest latency | Real-time interactions |
| `CHEAPEST` | Lowest cost | High-volume tasks |
| `FREE_FIRST` | Try free tiers first | Cost-conscious usage |
| `LOCAL_ONLY` | Only local models | Privacy/offline |
| `MANUAL` | User-specified | Explicit control |

#### Features

- **Automatic Fallback**: Tries alternative models on failure
- **Capability Matching**: Ensures selected model supports required features
- **Health Monitoring**: Tracks provider availability
- **Latency Caching**: Optimizes for speed
- **Cost Optimization**: Minimizes expenses when appropriate

### 3. Provider Implementations

#### OpenAI Provider (`openai_provider.py`)

```python
provider = OpenAIProvider(api_key="...")
await provider.initialize()

# Supported capabilities:
- TEXT ✓
- VISION ✓ (GPT-4 Vision)
- FUNCTION_CALLING ✓
- STREAMING ✓
- JSON_MODE ✓

# Available models:
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo
- gpt-4
- gpt-3.5-turbo
```

#### Future Providers (To Implement)

- **Anthropic Provider**: Claude 3 Opus/Sonnet/Haiku
- **Google Provider**: Gemini Pro/Ultra
- **Groq Provider**: LPU inference
- **OpenRouter Provider**: Multi-model gateway
- **Ollama Provider**: Local models

## Usage Examples

### Basic Usage

```python
from backend.providers import ModelRouter, RouterConfig, RoutingStrategy
from backend.providers.base import ChatMessage, MessageRole

# Create router
config = RouterConfig(default_strategy=RoutingStrategy.AUTO)
router = ModelRouter(config)

# Register provider
from backend.providers.openai_provider import OpenAIProvider
provider = OpenAIProvider(api_key="sk-...")
router.register_provider(provider)

# Initialize
await router.initialize()

# Send message
messages = [
    ChatMessage(role=MessageRole.USER, content="Hello, Jarvis!")
]

response = await router.execute_with_fallback(
    messages=messages,
    temperature=0.7
)

print(response.content)
```

### Advanced: Tool Usage

```python
from backend.providers.base import ToolDefinition

tools = [
    ToolDefinition(
        name="web_search",
        description="Search the web",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    )
]

response = await router.execute_with_fallback(
    messages=messages,
    tools=tools,
    strategy=RoutingStrategy.BEST_QUALITY
)

if response.tool_calls:
    # Execute tool calls
    ...
```

### Streaming Response

```python
async for chunk in provider.chat_completion_stream(
    messages=messages,
    model="gpt-4o"
):
    print(chunk, end="", flush=True)
```

### Provider Health Check

```python
statuses = await router.get_provider_status()

for status in statuses:
    print(f"{status.name}: {'✓' if status.connected else '✗'}")
    if status.error:
        print(f"  Error: {status.error}")
```

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_API_KEY=...
GOOGLE_PROJECT_ID=...

# Groq
GROQ_API_KEY=gsk_...

# OpenRouter
OPENROUTER_API_KEY=...

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

### Router Configuration

```python
RouterConfig(
    default_strategy=RoutingStrategy.AUTO,
    fallback_enabled=True,
    max_retries=3,
    timeout_seconds=60,
    preferred_providers=["openai", "anthropic"],
    blocked_models=["gpt-3.5-turbo"],  # Disable specific models
    cost_limit_per_request=1.0,  # Max $1 per request
    cache_enabled=True,
    cache_ttl_seconds=300
)
```

## Adding New Providers

### Step 1: Create Provider Class

```python
# backend/providers/anthropic_provider.py

from .base import AIProvider, ProviderCapability, ...

class AnthropicProvider(AIProvider):
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.TEXT,
            ProviderCapability.VISION,
            ProviderCapability.STREAMING
        ]
    
    async def initialize(self) -> bool:
        # Implementation
        ...
    
    async def chat_completion(...) -> ProviderResponse:
        # Implementation
        ...
```

### Step 2: Register Provider

```python
# In your application initialization
from backend.providers.anthropic_provider import AnthropicProvider

provider = AnthropicProvider(api_key="...")
router.register_provider(provider)
```

### Step 3: Update Package Exports

```python
# backend/providers/__init__.py
from .anthropic_provider import AnthropicProvider

__all__ = [
    ...,
    "AnthropicProvider"
]
```

## Error Handling

The Provider Layer includes robust error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Rate Limits**: Respect rate limits and queue requests
- **Timeout**: Configurable timeout per request
- **Fallback**: Switch to alternative providers on failure
- **Health Tracking**: Mark unhealthy providers temporarily unavailable

## Security

- **API Keys**: Never exposed to frontend
- **Environment Variables**: Loaded from secure storage
- **No Logging**: Sensitive data excluded from logs
- **Validation**: All inputs validated before use

## Performance Considerations

- **Lazy Initialization**: Providers initialized on first use
- **Model Caching**: Available models cached for 5 minutes
- **Latency Tracking**: Historical latency used for routing
- **Connection Pooling**: Reuse HTTP connections
- **Async Operations**: Non-blocking I/O throughout

## Testing

```python
import pytest
from backend.providers import ModelRouter, OpenAIProvider

@pytest.mark.asyncio
async def test_openai_provider():
    provider = OpenAIProvider(api_key="test-key")
    assert provider.name == "openai"
    assert ProviderCapability.TEXT in provider.capabilities

@pytest.mark.asyncio
async def test_router_selection():
    router = ModelRouter()
    model = await router.select_model(
        required_capabilities=[ProviderCapability.TEXT]
    )
    assert model is not None
```

## Roadmap

### Phase 4 (Current)
- ✓ Base provider interface
- ✓ Model Router with strategies
- ✓ OpenAI provider implementation
- ✓ Automatic fallback
- ✓ Capability matching

### Phase 5 (Next)
- [ ] Anthropic provider
- [ ] Google Gemini provider
- [ ] Ollama (local) provider
- [ ] OpenRouter integration
- [ ] Cost tracking dashboard

### Future
- [ ] Custom model fine-tuning support
- [ ] Multi-provider load balancing
- [ ] Advanced caching strategies
- [ ] Real-time cost monitoring
- [ ] A/B testing framework

## Troubleshooting

### Common Issues

**Provider Not Initializing**
```
Problem: API key missing or invalid
Solution: Check environment variables and credentials
```

**No Models Available**
```
Problem: Provider not registered or unhealthy
Solution: Call router.initialize() and check provider status
```

**Timeout Errors**
```
Problem: Request taking too long
Solution: Increase timeout_seconds in RouterConfig
```

**Fallback Not Working**
```
Problem: No alternative providers available
Solution: Register multiple providers for redundancy
```

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [AGENTS.md](../AGENTS.md) - Agent system
- [SKILLS.md](../SKILLS.md) - Skills system
- [SECURITY.md](../SECURITY.md) - Security practices
