# JARVIS AI — Sistema de Agentes

## Visão Geral

O sistema de agentes do JARVIS é dinâmico, recursivo e hierárquico. Um agente pode possuir múltiplos subagentes, que por sua vez podem possuir seus próprios subagentes, sem limite artificial de profundidade (protegido por limites configuráveis).

## Hierarquia de Agentes

```
USUÁRIO
   │
   ▼
JARVIS CORE (Orchestrator / Main Brain)
   │
   ├── Agent: Developer
   │     ├── Subagent: Frontend
   │     │      ├── Subagent: UI
   │     │      ├── Subagent: Accessibility
   │     │      └── Subagent: Testing
   │     │
   │     ├── Subagent: Backend
   │     ├── Subagent: QA
   │     └── Subagent: DevOps
   │
   ├── Agent: Research
   │
   ├── Agent: Business
   │   ├── Subagent: Finance
   │   ├── Subagent: Sales
   │   └── Subagent: CRM
   │
   └── Agent: Marketing
       ├── Subagent: SEO
       ├── Subagent: Copywriting
       └── Subagent: Social Media
```

## Estrutura de um Agente

Cada agente possui a seguinte estrutura:

```python
class Agent:
    id: str                    # UUID único
    name: str                  # Nome legível
    description: str           # Descrição da função
    instructions: str          # System prompt / instruções
    
    # Hierarquia
    parent_id: str | None      # ID do agente pai (None para JARVIS Core)
    child_agents: list[str]    # IDs dos agentes filhos
    
    # Modelo
    model_strategy: str        # AUTO, BEST_QUALITY, FASTEST, CHEAPEST, MANUAL
    preferred_provider: str    # Provider preferencial
    fallback_providers: list[str]  # Lista de fallback
    temperature: float | None  # Temperatura (se suportada)
    
    # Capabilities
    capabilities: dict[str, bool]
    # {
    #   "text": True,
    #   "vision": True,
    #   "files": True,
    #   "voice": False,
    #   "video": False
    # }
    
    # Skills e Tools
    skills: list[str]          # IDs das skills atribuídas
    tools: list[str]           # IDs das tools disponíveis
    
    # Permissões
    permissions: list[str]     # Permissões explícitas
    
    # Recursos
    memory_enabled: bool       # Memória habilitada?
    internet_access: bool      # Acesso à internet?
    file_access: bool          # Acesso a arquivos?
    terminal_access: bool      # Acesso ao terminal?
    
    # Capacidades de ação
    can_delegate: bool         # Pode delegar tarefas?
    can_create_agents: bool    # Pode criar novos agentes?
    can_call_agents: bool      # Pode chamar outros agentes?
    
    # Contexto
    context_window: int        # Tamanho do contexto
    metadata: dict             # Metadados adicionais
    
    # Estado
    enabled: bool              # Agente habilitado?
    created_at: datetime
    updated_at: datetime
```

## Agent Registry

O Agent Registry é responsável por:

1. **Registro**: Manter todos os agentes registrados
2. **Hierarquia**: Gerenciar relações pai-filho
3. **Busca**: Localizar agentes por ID, nome ou função
4. **Validação**: Prevenir loops e delegação circular
5. **Serialização**: Exportar/importar configurações

```python
class AgentRegistry:
    def register_agent(self, agent: Agent) -> str
    def get_agent(self, agent_id: str) -> Agent
    def get_children(self, agent_id: str) -> list[Agent]
    def get_parent(self, agent_id: str) -> Agent | None
    def get_hierarchy(self, agent_id: str) -> list[Agent]
    def validate_delegation(self, from_id: str, to_id: str) -> bool
    def detect_loop(self, agent_id: str, visited: set[str]) -> bool
    def export_config(self, agent_id: str) -> dict
    def import_config(self, config: dict) -> Agent
```

## Proteções contra Recursão Descontrolada

### 1. Limite de Profundidade

```python
MAX_DEPTH = 10  # Configurável

def check_depth(agent_id: str) -> int:
    depth = 0
    current = agent_id
    while current is not None:
        current = registry.get_parent(current)
        depth += 1
        if depth > MAX_DEPTH:
            raise MaxDepthExceeded(f"Maximum depth of {MAX_DEPTH} exceeded")
    return depth
```

### 2. Detecção de Loops

```python
def detect_circular_delegation(path: list[str]) -> bool:
    """Detecta se há repetição no caminho de delegação"""
    return len(path) != len(set(path))
```

### 3. Rate Limiting

```python
class RateLimiter:
    def __init__(self, max_calls: int = 100, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls = defaultdict(list)
    
    def can_call(self, agent_id: str) -> bool:
        # Implementação de rate limiting
```

### 4. Controle de Tokens

```python
class TokenBudget:
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
    
    def consume(self, tokens: int) -> bool:
        if self.used_tokens + tokens > self.max_tokens:
            raise TokenBudgetExceeded()
        self.used_tokens += tokens
        return True
```

## Configuração Declarativa

Agentes podem ser definidos via configuração YAML/JSON:

```yaml
# agents/developer.yaml
name: developer
description: Specialized software development agent
parent: jarvis

model:
  strategy: auto
  preferred_provider: openai
  fallback_providers: [anthropic, gemini]
  temperature: 0.7

capabilities:
  text: true
  vision: true
  files: true
  voice: false
  video: false

skills:
  - programming
  - debugging
  - testing
  - code_review

tools:
  - filesystem
  - github
  - terminal

permissions:
  - READ_FILES
  - WRITE_FILES
  - TERMINAL_READ
  - TERMINAL_EXECUTE
  - GITHUB_READ

resources:
  memory_enabled: true
  internet_access: false
  file_access: true
  terminal_access: true

actions:
  can_delegate: true
  can_create_agents: false
  can_call_agents: true

children:
  - frontend
  - backend
  - qa
  - devops
```

## Ciclo de Vida do Agente

1. **Criação**: Via Agent Builder ou configuração declarativa
2. **Registro**: Adicionado ao Agent Registry
3. **Ativação**: Habilitado para receber tarefas
4. **Execução**: Processa tarefas, delega, usa skills/tools
5. **Monitoramento**: Logs, métricas, auditoria
6. **Atualização**: Modificação de configuração
7. **Desativação**: Desabilitado sem remover histórico
8. **Remoção**: Exclusão completa (com validação de dependências)

## Estados do Agente

```python
class AgentState(Enum):
    IDLE = "idle"              # Aguardando tarefa
    BUSY = "busy"              # Executando tarefa
    DELEGATING = "delegating"  # Delegando para subagente
    WAITING = "waiting"        # Aguardando resposta
    ERROR = "error"            # Em erro
    DISABLED = "disabled"      # Desabilitado
```

## Comunicação entre Agentes

### 1. Delegação Direta

```python
async def delegate_task(
    from_agent: str,
    to_agent: str,
    task: Task,
    context: dict
) -> Result:
    # Valida permissões
    # Verifica loop
    # Executa delegação
    # Aguarda resultado
    # Retorna resultado
```

### 2. Chamada via Orchestrator

```python
async def call_agent_via_orchestrator(
    caller: str,
    target: str,
    request: str
) -> Response:
    # Orchestrator coordena
    # Gerencia contexto
    # Coleta resultado
```

### 3. Broadcast para Múltiplos Agentes

```python
async def broadcast_to_agents(
    agent_ids: list[str],
    message: Message,
    parallel: bool = True
) -> list[Result]:
    # Envia para múltiplos agentes
    # Coleta resultados
    # Consolida respostas
```

## Visualização no Frontend

O frontend representa agentes como nós em um grafo:

- **Nó Central**: JARVIS Core
- **Nós Secundários**: Agentes de primeiro nível
- **Nós Terciários**: Subagentes
- **Conexões**: Linhas animadas durante execução
- **Estados Visuais**: Cores indicam estado (idle, busy, error)
- **Navegação**: Clique em agente torna-o centro da visualização

## Exemplos de Uso

### Criar Agente Programaticamente

```python
from backend.agents import Agent, AgentRegistry

registry = AgentRegistry()

frontend_agent = Agent(
    name="Frontend Specialist",
    description="Expert in React, Next.js, UI/UX",
    instructions="You are a frontend expert...",
    parent_id="developer",
    model_strategy="AUTO",
    capabilities={"text": True, "vision": True, "files": True},
    skills=["react", "nextjs", "ui_ux"],
    tools=["filesystem", "github"],
    permissions=["READ_FILES", "WRITE_FILES", "GITHUB_READ"],
    can_delegate=True,
    can_create_agents=False
)

agent_id = registry.register_agent(frontend_agent)
```

### Validar Delegação

```python
if registry.validate_delegation("developer", "frontend"):
    result = await delegate_task("developer", "frontend", task)
else:
    raise InvalidDelegation("Circular delegation detected")
```

### Exportar Configuração

```python
config = registry.export_config("developer")
yaml_str = yaml.dump(config)
# Salvar em arquivo
```

## Próximos Passos

1. Implementar Agent Registry com NetworkX
2. Criar modelo de dados SQLAlchemy
3. Implementar validações de segurança
4. Criar API REST para CRUD de agentes
5. Implementar WebSocket para eventos em tempo real
6. Desenvolver interface de Agent Builder
7. Criar sistema de templates de agentes
8. Implementar sugestão automática de agentes (Agent Creator)
