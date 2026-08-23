# JARVIS AI

## Sistema Operacional Pessoal de Inteligência Artificial

JARVIS é uma plataforma multiagente, multimodal e extensível de IA, projetada para funcionar como um sistema operacional pessoal de inteligência artificial.

## 🎯 Visão Geral

Inspirado conceitualmente em interfaces futuristas de assistentes de IA, o JARVIS não é apenas um chatbot. Ele é um **sistema operacional pessoal de IA**, extensível, multimodal, multiagente e orientado a skills, capaz de conectar diferentes modelos de IA, APIs, ferramentas e agentes especializados.

## ✨ Características Principais

- **Arquitetura Multiagente Recursiva**: Agentes podem possuir subagentes sem limite artificial de profundidade
- **Sistema de Skills Modular**: Competências reutilizáveis que podem ser atribuídas a agentes
- **Model Provider Layer**: Abstração para múltiplos providers (OpenAI, Anthropic, Google, Groq, etc.)
- **Model Router Inteligente**: Estratégias AUTO, BEST_QUALITY, FASTEST, CHEAPEST, FREE_FIRST, LOCAL_ONLY
- **Multimodalidade**: Suporte para texto, voz, áudio, visão, imagens, arquivos, PDF, vídeo
- **Sistema de Permissões Granular**: Controle explícito de acesso a recursos
- **Memória em 5 Camadas**: Working, Conversation, Agent, User, Knowledge
- **Interface Visual Futurista**: Representação gráfica do cérebro JARVIS e rede de agentes
- **Observabilidade Completa**: Logs, métricas, tracing de execuções

## 🏗️ Arquitetura

```
USUÁRIO
   │
   ▼
JARVIS CORE (Orchestrator)
   │
   ├── Agents → Subagents → Skills → Tools
   ├── Model Router → Providers
   ├── Memory System (5 layers)
   └── Event Bus → Observability
```

Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para detalhes completos.

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Node.js 18+ (para frontend)
- PostgreSQL (opcional, SQLite para desenvolvimento)

### Instalação

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/jarvis.rank.git
cd jarvis.rank

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências backend
pip install -r requirements.txt

# Instalar dependências frontend
cd frontend
npm install
cd ..

# Copiar arquivo de ambiente
cp .env.example .env

# Editar .env com suas configurações

# Rodar migrações do banco
alembic upgrade head

# Iniciar servidor backend
uvicorn backend.main:app --reload

# Em outro terminal, iniciar frontend
cd frontend
npm run dev
```

### Acesso

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Estrutura do Projeto

```
jarvis.rank/
├── backend/                 # Backend Python/FastAPI
│   ├── core/               # Jarvis Core (Orchestrator, Mission Manager)
│   ├── agents/             # Agent Registry, Agent Nodes
│   ├── skills/             # Skill Registry, Skills
│   ├── tools/              # Tool Registry, Tools
│   ├── providers/          # AI Providers, Model Router
│   ├── memory/             # Memory System
│   ├── permissions/        # Permission System
│   ├── events/             # Event Bus
│   ├── api/                # API Routes, WebSocket
│   └── config/             # Configuração
│
├── frontend/               # Frontend React/Vue
│   ├── src/
│   │   ├── components/     # Componentes UI
│   │   ├── hooks/          # React Hooks
│   │   ├── services/       # API Services
│   │   ├── store/          # State Management
│   │   ├── types/          # TypeScript Types
│   │   └── utils/          # Utilitários
│   └── public/             # Assets estáticos
│
├── docs/                   # Documentação
│   ├── ARCHITECTURE.md     # Arquitetura do sistema
│   ├── AGENTS.md           # Sistema de agentes
│   ├── SKILLS.md           # Sistema de skills
│   ├── TOOLS.md            # Sistema de tools
│   ├── PROVIDERS.md        # Providers de IA
│   ├── MULTIMODAL.md       # Multimodalidade
│   ├── SECURITY.md         # Segurança
│   └── DEVELOPMENT.md      # Guia de desenvolvimento
│
├── data/                   # Dados
│   ├── demo/               # Dados de demonstração
│   └── local/              # Dados locais (ignorados no git)
│
├── memory/                 # Arquivos de memória
├── tests/                  # Testes
│   ├── unit/               # Testes unitários
│   └── integration/        # Testes de integração
│
├── scripts/                # Scripts utilitários
├── requirements.txt        # Dependências Python
├── package.json           # Dependências frontend
└── README.md              # Este arquivo
```

## 📚 Documentação

- [Arquitetura](docs/ARCHITECTURE.md) - Visão geral da arquitetura
- [Agentes](docs/AGENTS.md) - Sistema de agentes multi-nível
- [Skills](docs/SKILLS.md) - Sistema de competências modulares
- [Tools](docs/TOOLS.md) - Ferramentas e integrações
- [Providers](docs/PROVIDERS.md) - Integração com modelos de IA
- [Segurança](docs/SECURITY.md) - Segurança e permissões
- [Desenvolvimento](docs/DEVELOPMENT.md) - Guia para desenvolvedores

## 🔧 Funcionalidades

### Core
- [x] Estrutura do projeto
- [x] Configuração de ambiente
- [x] Documentação de arquitetura
- [ ] Orchestrator principal
- [ ] Agent Registry dinâmico
- [ ] Skill Registry modular
- [ ] Tool Registry extensível
- [ ] Model Router inteligente
- [ ] Mission Manager
- [ ] Execution Engine

### Agents
- [x] Hierarquia recursiva documentada
- [x] Validação contra loops documentada
- [ ] Implementar Agent Registry
- [ ] Limite de profundidade configurável
- [ ] Agent Builder (UI)
- [ ] Agent Creator (IA)

### AI Providers
- [ ] Interface comum
- [ ] OpenAI adapter
- [ ] Anthropic adapter
- [ ] Google Gemini adapter
- [ ] Groq adapter
- [ ] OpenRouter adapter
- [ ] Ollama adapter
- [ ] Model Router com fallback

### Interface
- [ ] Visual Core animado
- [ ] Agent Graph (Canvas/SVG)
- [ ] Activity Panel em tempo real
- [ ] Chat UI
- [ ] Voice UI
- [ ] Settings Panel

## 🔒 Segurança

- API keys exclusivamente no backend
- Validação rigorosa de inputs
- Rate limiting e quotas configuráveis
- Proteção contra recursão infinita
- Auditoria de operações sensíveis
- Princípio do menor privilégio
- Segredos em secret store (.env)

Veja [docs/SECURITY.md](docs/SECURITY.md) para detalhes.

## 🧪 Testes

```bash
# Rodar testes unitários
pytest tests/unit/ -v

# Rodar testes de integração
pytest tests/integration/ -v

# Rodar todos os testes com coverage
pytest --cov=backend --cov-report=html
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) para diretrizes de desenvolvimento.

## 📄 Licença

MIT License - veja LICENSE para detalhes.

## 🎯 Roadmap

### Fase 1 — Fundação (✅ Concluída)
- [x] Estrutura do projeto
- [x] Configuração de ambiente
- [x] Documentação de arquitetura
- [x] Modelo de dados
- [x] .gitignore e .env.example

### Fase 2 — Jarvis Core (Próxima)
- [ ] Implementar Orchestrator
- [ ] Implementar Agent Registry
- [ ] Implementar Skill Registry
- [ ] Implementar Tool Registry
- [ ] Implementar Event Bus

### Fase 3 — AI Providers
- [ ] Implementar interface comum
- [ ] Integrar primeiros providers
- [ ] Implementar Model Router

### Fase 4 — Interface Visual
- [ ] Visual Core animado
- [ ] Agent Graph
- [ ] Activity Panel
- [ ] Chat UI

### Fase 5 — Agent Builder
- [ ] CRUD de agentes via UI
- [ ] Configuração visual de agentes
- [ ] Templates de agentes

### Fase 6 — Segurança e Observabilidade
- [ ] Revisão completa de segurança
- [ ] Sistema de logs estruturados
- [ ] Dashboard de métricas

---

**JARVIS** - Just A Rather Very Intelligent System
