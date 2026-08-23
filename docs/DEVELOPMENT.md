# JARVIS AI — Guia de Desenvolvimento

## Visão Geral

Este documento fornece diretrizes para desenvolvedores que desejam contribuir com o JARVIS AI.

## Configuração do Ambiente

### Pré-requisitos

- Python 3.11+
- Node.js 18+ (para frontend)
- Git
- PostgreSQL (opcional para desenvolvimento, SQLite funciona)

### Instalação

```bash
# Clonar repositório
git clone <repository-url>
cd jarvis.rank

# Criar ambiente virtual Python
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Frontend (quando disponível)
cd frontend
npm install
cd ..

# Copiar configuração de ambiente
cp .env.example .env

# Editar .env conforme necessário
```

## Estrutura do Projeto

```
jarvis.rank/
├── backend/              # Backend FastAPI
│   ├── core/            # Jarvis Core (Orchestrator, Mission Manager)
│   ├── agents/          # Agent Registry, Agent Nodes
│   ├── skills/          # Skill Registry, Skills
│   ├── tools/           # Tool Registry, Tools
│   ├── providers/       # AI Providers, Model Router
│   ├── memory/          # Memory System
│   ├── permissions/     # Permission System
│   ├── events/          # Event Bus
│   ├── api/             # API Routes, WebSocket
│   └── config/          # Configuração
│
├── frontend/            # Frontend (React/Vue)
├── docs/                # Documentação
├── tests/               # Testes
│   ├── unit/           # Testes unitários
│   └── integration/    # Testes de integração
└── scripts/            # Scripts utilitários
```

## Padrões de Código

### Python

- Seguir PEP 8
- Usar type hints
- Docstrings em funções públicas
- Nomear variáveis em snake_case
- Classes em PascalCase

```python
from typing import Optional
from pydantic import BaseModel

class Agent(BaseModel):
    """Representa um agente no sistema JARVIS."""
    
    id: str
    name: str
    description: str
    parent_id: Optional[str] = None
    
    async def execute(self, task: str) -> str:
        """Executa uma tarefa.
        
        Args:
            task: Descrição da tarefa
            
        Returns:
            Resultado da execução
        """
        pass
```

### Commits

Seguir Conventional Commits:

```
feat: adicionar novo provider
fix: corrigir bug no agent registry
docs: atualizar documentação
test: adicionar testes unitários
refactor: refatorar orchestrator
chore: atualizar dependências
```

## Testes

```bash
# Rodar testes unitários
pytest tests/unit/ -v

# Rodar testes de integração
pytest tests/integration/ -v

# Com coverage
pytest --cov=backend --cov-report=html

# Abrir relatório
open htmlcov/index.html
```

## Executando o Servidor

```bash
# Backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (quando disponível)
cd frontend
npm run dev
```

## API Documentation

Com o servidor rodando, acesse:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Adicionando um Novo Provider

1. Criar adapter em `backend/providers/adapters/`
2. Implementar interface comum
3. Registrar no provider registry
4. Adicionar testes

```python
# backend/providers/adapters/new_provider.py
from backend.providers.base import BaseProvider

class NewProviderAdapter(BaseProvider):
    async def generate(self, prompt: str, **kwargs) -> str:
        # Implementação
        pass
```

## Adicionando uma Nova Skill

1. Criar definição da skill
2. Registrar no skill registry
3. Adicionar instruções
4. Definir permissões necessárias
5. Adicionar testes

## Adicionando uma Nova Tool

1. Criar tool em `backend/tools/`
2. Implementar interface
3. Definir permissões
4. Registrar no tool registry
5. Adicionar testes

## Debugging

```bash
# Usar pdb para debug
import pdb; pdb.set_trace()

# Log estruturado
import structlog
log = structlog.get_logger()
log.info("evento", extra={"dados": "valores"})
```

## Variáveis de Ambiente

Principais variáveis em `.env`:

```env
# Aplicação
JARVIS_ENV=development
JARVIS_DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/jarvis.db

# Security
SECRET_KEY=change-me-in-production

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Features
ENABLE_VOICE=false
ENABLE_FILE_ACCESS=true
```

## Troubleshooting

### Erro: ModuleNotFoundError

```bash
pip install -r requirements.txt
```

### Erro: Database locked

```bash
# SQLite pode estar travado
rm data/jarvis.db
alembic upgrade head
```

### Erro: Port already in use

```bash
# Matar processo na porta 8000
lsof -ti:8000 | xargs kill -9
```

## Contribuindo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova feature'`)
4. Push (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Recursos

- [Documentação de Arquitetura](ARCHITECTURE.md)
- [Sistema de Agentes](AGENTS.md)
- [Sistema de Skills](SKILLS.md)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)

---

**JARVIS** - Just A Rather Very Intelligent System
