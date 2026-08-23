# JARVIS AI — Arquitetura do Sistema

## Visão Geral

JARVIS é uma plataforma de inteligência artificial multiagente, multimodal e extensível, projetada para funcionar como um sistema operacional pessoal de IA.

## Princípios Fundamentais

1. **Hierarquia Recursiva**: Usuário → JARVIS Core → Agents → Subagents → Skills → Tools
2. **Dinamismo**: Agentes podem criar agentes filhos sem limite artificial de profundidade
3. **Modularidade**: Providers, Skills e Tools funcionam como plugins
4. **Segurança**: Princípio do menor privilégio, validação rigorosa, proteção contra recursão infinita
5. **Observabilidade**: Todo evento é registrado e rastreável

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Visual Core │  │ Agent Graph  │  │ Activity Panel          │ │
│  │ (Animated)  │  │ (Canvas/SVG) │  │ (Real-time Events)      │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Chat UI     │  │ Voice UI     │  │ Settings/Config         │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓ WebSocket / REST API
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    JARVIS CORE                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Orchestrator │  │ Mission Mgr  │  │ Execution Engine│  │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Agent Reg    │  │ Skill Reg    │  │ Tool Registry  │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   AI LAYER                                │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Model Router │  │ Provider Adp │  │ AI Providers   │  │  │
│  │  │ (Auto/Fast)  │  │ (Abstract)   │  │ (OpenAI, etc.) │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  DATA LAYER                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Memory Mgr   │  │ Event Bus    │  │ Database       │  │  │
│  │  │ (5 Layers)   │  │ (Internal)   │  │ (PostgreSQL)   │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Componentes Principais

### 1. JARVIS Core

**Orchestrator**: Cérebro principal que recebe solicitações, analisa intenção, cria planos e coordena execução.

**Mission Manager**: Gerencia missões do início ao fim, com estados: WAITING, PLANNING, RUNNING, DELEGATED, COMPLETED, FAILED, CANCELLED.

**Execution Engine**: Executa tarefas, delega para subagentes, coleta resultados e valida saídas.

### 2. Agent System

**Agent Registry**: Registro dinâmico de agentes com suporte a hierarquia recursiva.

**Agent Node**: Cada agente possui:
- Instructions (system prompt)
- Model configuration (strategy, fallbacks)
- Capabilities (text, vision, files, voice, video)
- Skills atribuídas
- Tools disponíveis
- Permissions explícitas
- Context/Memory privada
- Child agents (lista de filhos)

**Proteções**:
- Limite de profundidade configurável (default: 10)
- Detecção de loops e delegação circular
- Rate limiting por agente
- Controle de consumo de tokens

### 3. Skill System

**Skill Registry**: Sistema modular de competências reutilizáveis.

**Skill Structure**:
```python
{
    "id": "unique_id",
    "name": "Skill Name",
    "version": "1.0.0",
    "description": "...",
    "instructions": "...",
    "required_tools": ["tool1", "tool2"],
    "required_permissions": ["READ_FILES"],
    "compatible_modalities": ["text", "vision"],
    "dependencies": ["skill_id_1"],
    "metadata": {},
    "enabled": true
}
```

### 4. Tool System

**Tool Registry**: Camada independente para ferramentas externas.

**Tools Exemplos**: Web Search, Browser, Filesystem, Terminal, GitHub, Email, Calendar, Database, Image Generation, Code Execution.

**Permissions**: Cada tool requer permissões explícitas.

### 5. Provider Layer

**Model Router**: Estratégias AUTO, BEST_QUALITY, FASTEST, CHEAPEST, FREE_FIRST, LOCAL_ONLY, MANUAL.

**Provider Adapter**: Interface comum para todos providers.

**Providers Suportados**: OpenAI, Anthropic, Google Gemini, Groq, OpenRouter, Ollama.

**Fallback**: Cadeia configurável com circuit breaker.

### 6. Memory System

Cinco camadas de memória:
1. **Working Memory**: Contexto imediato da tarefa
2. **Conversation Memory**: Histórico de conversas
3. **Agent Memory**: Memória privada por agente
4. **User Memory**: Preferências e dados do usuário
5. **Knowledge Memory**: Base de conhecimento global

### 7. Permission System

Permissões explícitas:
- READ_FILES, WRITE_FILES
- WEB_ACCESS
- TERMINAL_READ, TERMINAL_EXECUTE
- GITHUB_READ, GITHUB_WRITE
- EMAIL_READ, EMAIL_SEND
- CALENDAR_READ, CALENDAR_WRITE

Operações sensíveis requerem confirmação.

### 8. Event System

**Event Bus**: Comunicação interna entre componentes.

**Event Types**: mission_created, task_started, agent_delegated, tool_called, result_collected, error_occurred.

**Observability**: Logs estruturados, tracing de execuções, métricas de uso.

## Fluxo de Execução

```
USER REQUEST
      ↓
INTENT ANALYSIS (Orchestrator)
      ↓
PLANNING (Mission Manager)
      ↓
TASK BREAKDOWN
      ↓
AGENT SELECTION (from Agent Registry)
      ↓
MODEL SELECTION (via Model Router)
      ↓
SKILL SELECTION (from Skill Registry)
      ↓
TOOL EXECUTION (from Tool Registry)
      ↓
SUBAGENT DELEGATION (recursive)
      ↓
RESULT COLLECTION
      ↓
VALIDATION
      ↓
FINAL RESPONSE → USER
```

## Segurança

- API keys exclusivamente no backend
- Validação rigorosa de inputs
- Rate limiting e quotas
- Proteção contra recursão infinita
- Auditoria de operações sensíveis
- Princípio do menor privilégio
- Segredos em secret store (.env, vault)

## Escalabilidade

- Arquitetura baseada em plugins
- Adição de providers sem modificar Core
- Adição de skills sem alterar Orchestrator
- Adição de tools sem mudar agentes
- Suporte a 5→50→500 agentes
- Suporte a 20→100→1000 skills

## Modelo de Dados

Entidades principais:
- users, agents, agent_relationships
- skills, agent_skills
- tools, agent_tools
- providers, models
- missions, tasks, executions
- messages, memories
- permissions, usage, events

## Próximos Passos

1. Implementar Fundação (bootstrap, config, database)
2. Implementar Jarvis Core (orchestrator, registries)
3. Implementar AI Layer (providers, router)
4. Implementar Frontend (visual core, graph, chat)
5. Implementar Agent Builder
6. Implementar Skills Manager
7. Implementar Segurança e Observabilidade
