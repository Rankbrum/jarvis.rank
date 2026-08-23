# JARVIS AI — Sistema de Skills

## Visão Geral

Skills são competências modulares e reutilizáveis que podem ser atribuídas a agentes. Elas representam conhecimento especializado, metodologias ou capacidades específicas que um agente pode utilizar para executar tarefas.

## Princípios Fundamentais

1. **Modularidade**: Skills são independentes e intercambiáveis
2. **Reusabilidade**: Uma skill pode ser atribuída a múltiplos agentes
3. **Composabilidade**: Skills podem ter dependências entre si
4. **Validação**: Skills validam permissões e ferramentas necessárias
5. **Versionamento**: Skills possuem versão para controle de mudanças

## Estrutura de uma Skill

```python
class Skill:
    id: str                    # UUID único ou nome semântico
    name: str                  # Nome legível
    version: str               # Versão semântica (ex: "1.0.0")
    description: str           # Descrição detalhada
    
    # Conteúdo
    instructions: str          # Instruções para usar a skill
    system_prompt: str | None  # Prompt adicional para o modelo
    
    # Requisitos
    required_tools: list[str]  # IDs das tools necessárias
    required_permissions: list[str]  # Permissões necessárias
    compatible_modalities: list[str]  # ["text", "vision", "files"]
    
    # Dependências
    dependencies: list[str]    # IDs de skills dependentes
    
    # Metadados
    metadata: dict             # Informações adicionais
    tags: list[str]            # Tags para busca
    author: str                # Autor/criador
    license: str               # Licença de uso
    
    # Estado
    enabled: bool              # Skill habilitada?
    is_core: bool              # Skill central do sistema?
    created_at: datetime
    updated_at: datetime
```

## Exemplos de Skills

### 1. React Development

```yaml
id: react_development
name: React Development
version: 1.0.0
description: Expertise em desenvolvimento React, hooks, componentes e ecossistema

instructions: |
  You are an expert in React development. When using this skill:
  - Follow React best practices and conventions
  - Use functional components with hooks
  - Implement proper error handling
  - Consider performance optimizations
  - Write accessible components
  
system_prompt: |
  You are a React expert with deep knowledge of:
  - React 18+ features
  - Hooks (useState, useEffect, useContext, useReducer, custom hooks)
  - Component composition patterns
  - State management (Context, Zustand, Redux)
  - Next.js framework
  - Testing (Jest, React Testing Library)
  
required_tools:
  - filesystem
  - github
  - npm_registry

required_permissions:
  - READ_FILES
  - WRITE_FILES
  - GITHUB_READ

compatible_modalities:
  - text
  - files
  - vision

dependencies: []

metadata:
  category: programming
  difficulty: intermediate
  estimated_tokens: 500

tags:
  - frontend
  - javascript
  - typescript
  - web

author: JARVIS Core Team
license: MIT
enabled: true
is_core: true
```

### 2. Web Research

```yaml
id: web_research
name: Web Research
version: 1.2.0
description: Capacidade de pesquisar informações na web de forma eficaz

instructions: |
  You are skilled in web research. When using this skill:
  - Formulate effective search queries
  - Evaluate source credibility
  - Cross-reference information
  - Summarize findings concisely
  - Cite sources properly

required_tools:
  - web_search
  - browser

required_permissions:
  - WEB_ACCESS

compatible_modalities:
  - text

dependencies: []

metadata:
  category: research
  difficulty: beginner

tags:
  - research
  - internet
  - information

enabled: true
is_core: false
```

### 3. PDF Analysis

```yaml
id: pdf_analysis
name: PDF Analysis
version: 1.0.0
description: Análise e extração de informações de documentos PDF

instructions: |
  You are expert at analyzing PDF documents. When using this skill:
  - Extract text and structure from PDFs
  - Identify key information
  - Summarize content
  - Answer questions based on PDF content
  - Handle tables and figures

required_tools:
  - filesystem
  - pdf_parser

required_permissions:
  - READ_FILES

compatible_modalities:
  - text
  - files
  - vision

dependencies: []

metadata:
  category: document_analysis
  difficulty: intermediate

tags:
  - documents
  - pdf
  - analysis

enabled: true
is_core: false
```

## Skill Registry

O Skill Registry é responsável por:

1. **Registro**: Manter todas as skills registradas
2. **Discovery**: Permitir busca e filtragem de skills
3. **Validação**: Verificar dependências e requisitos
4. **Atribuição**: Associar skills a agentes
5. **Versionamento**: Gerenciar múltiplas versões
6. **Instalação**: Adicionar novas skills ao sistema

```python
class SkillRegistry:
    def register_skill(self, skill: Skill) -> str
    def get_skill(self, skill_id: str) -> Skill
    def get_skill_version(self, skill_id: str, version: str) -> Skill
    def list_skills(self, filters: dict = None) -> list[Skill]
    def search_skills(self, query: str, tags: list[str] = None) -> list[Skill]
    def validate_skill(self, skill: Skill) -> list[str]  # Retorna erros
    def check_dependencies(self, skill: Skill) -> list[str]  # Retorna dependências faltantes
    def assign_to_agent(self, skill_id: str, agent_id: str) -> bool
    def remove_from_agent(self, skill_id: str, agent_id: str) -> bool
    def install_skill(self, skill_config: dict) -> str
    def uninstall_skill(self, skill_id: str) -> bool
    def enable_skill(self, skill_id: str) -> bool
    def disable_skill(self, skill_id: str) -> bool
    def update_skill(self, skill_id: str, updates: dict) -> Skill
```

## Ciclo de Vida de uma Skill

### 1. Criação

```python
# Via código
skill = Skill(
    id="contract_analysis",
    name="Contract Analysis",
    version="1.0.0",
    description="Specialized in analyzing legal contracts",
    instructions="...",
    required_tools=["filesystem", "legal_database"],
    required_permissions=["READ_FILES"],
    compatible_modalities=["text", "files"],
    dependencies=[],
    metadata={"category": "legal"}
)

registry.register_skill(skill)
```

### 2. Instalação

```python
# Via API ou interface
skill_data = {
    "name": "SEO Optimization",
    "description": "Search engine optimization expertise",
    "instructions": "...",
    "required_tools": ["web_search", "analytics"],
    "required_permissions": ["WEB_ACCESS"],
    "version": "1.0.0"
}

skill_id = registry.install_skill(skill_data)
```

### 3. Atribuição a Agente

```python
# Atribuir skill a um agente
registry.assign_to_agent("react_development", "frontend_agent_id")

# Atribuir múltiplas skills
skills = ["react_development", "typescript", "testing"]
for skill_id in skills:
    registry.assign_to_agent(skill_id, "frontend_agent_id")
```

### 4. Validação

```python
# Validar skill antes de usar
errors = registry.validate_skill(skill)
if errors:
    raise InvalidSkill(f"Skill validation failed: {errors}")

# Verificar dependências
missing_deps = registry.check_dependencies(skill)
if missing_deps:
    # Instalar dependências ou alertar usuário
```

### 5. Atualização

```python
# Atualizar skill existente
updates = {
    "version": "2.0.0",
    "instructions": "Updated instructions...",
    "metadata": {"changelog": "Added support for React 19"}
}

updated_skill = registry.update_skill("react_development", updates)
```

### 6. Remoção

```python
# Desabilitar skill
registry.disable_skill("old_skill_id")

# Remover completamente (após verificar dependências)
if not registry.is_dependency("old_skill_id"):
    registry.uninstall_skill("old_skill_id")
```

## Validação de Skills

### Validação de Estrutura

```python
def validate_skill_structure(skill: Skill) -> list[str]:
    errors = []
    
    if not skill.id or not skill.name:
        errors.append("ID and name are required")
    
    if not re.match(r"^\d+\.\d+\.\d+$", skill.version):
        errors.append("Version must be semantic (X.Y.Z)")
    
    if not skill.instructions:
        errors.append("Instructions are required")
    
    return errors
```

### Validação de Dependências Circulares

```python
def detect_circular_dependencies(
    skill_id: str, 
    registry: SkillRegistry,
    visited: set[str] = None
) -> bool:
    if visited is None:
        visited = set()
    
    if skill_id in visited:
        return True  # Circular detected
    
    visited.add(skill_id)
    skill = registry.get_skill(skill_id)
    
    for dep_id in skill.dependencies:
        if detect_circular_dependencies(dep_id, registry, visited.copy()):
            return True
    
    return False
```

### Validação de Permissões

```python
def validate_permissions(
    skill: Skill, 
    agent: Agent
) -> list[str]:
    """Retorna lista de permissões faltantes no agente"""
    missing = []
    
    for perm in skill.required_permissions:
        if perm not in agent.permissions:
            missing.append(perm)
    
    return missing
```

### Validação de Tools

```python
def validate_tools(
    skill: Skill, 
    available_tools: list[str]
) -> list[str]:
    """Retorna lista de tools faltantes"""
    missing = []
    
    for tool in skill.required_tools:
        if tool not in available_tools:
            missing.append(tool)
    
    return missing
```

## Compatibilidade de Modalidades

```python
def check_modality_compatibility(
    skill: Skill,
    required_modality: str
) -> bool:
    """Verifica se a skill suporta a modalidade necessária"""
    return required_modality in skill.compatible_modalities

# Exemplo de uso
if not check_modality_compatibility(skill, "vision"):
    raise ModalityNotSupported(
        f"Skill {skill.name} does not support vision modality"
    )
```

## Skill Creator (Futuro)

O sistema permitirá criação automática de skills via IA:

```
Usuário: "Jarvis, crie uma skill especializada em análise de contratos."

JARVIS:
1. Analisa o pedido
2. Gera estrutura da skill
3. Define instruções apropriadas
4. Identifica tools necessárias
5. Determina permissões requeridas
6. Valida configuração
7. Apresenta ao usuário para aprovação
8. Instala após confirmação
```

```python
async def create_skill_from_prompt(
    prompt: str,
    creator_agent: str
) -> Skill:
    """Gera skill baseada em descrição natural"""
    
    # Usar LLM para gerar estrutura
    skill_config = await generate_skill_config(prompt)
    
    # Validar configuração
    skill = Skill(**skill_config)
    errors = registry.validate_skill(skill)
    
    if errors:
        return {"status": "invalid", "errors": errors}
    
    # Apresentar ao usuário
    return {
        "status": "pending_approval",
        "skill": skill,
        "message": "Review and approve before installation"
    }
```

## Marketplace de Skills (Futuro)

Sistema para compartilhar e descobrir skills:

```python
class SkillMarketplace:
    def browse_skills(self, category: str = None) -> list[Skill]
    def search_skills(self, query: str) -> list[Skill]
    def get_skill_details(self, skill_id: str) -> Skill
    def install_from_marketplace(self, skill_id: str) -> bool
    def publish_skill(self, skill: Skill) -> str
    def rate_skill(self, skill_id: str, rating: int) -> bool
    def get_popular_skills(self) -> list[Skill]
    def get_new_skills(self) -> list[Skill]
```

## Métricas e Observabilidade

```python
class SkillMetrics:
    def track_usage(self, skill_id: str, agent_id: str, duration_ms: int)
    def get_usage_stats(self, skill_id: str, period: str) -> dict
    def get_popular_skills(self, limit: int = 10) -> list[str]
    def get_success_rate(self, skill_id: str) -> float
    def get_average_duration(self, skill_id: str) -> float
```

## Segurança em Skills

### Princípio do Menor Privilégio

- Skills recebem apenas permissões estritamente necessárias
- Permissões sensíveis requerem aprovação explícita
- Tools destrutivas exigem confirmação

### Validação de Entrada

```python
def sanitize_skill_input(input_data: dict) -> dict:
    """Remove dados potencialmente perigosos"""
    allowed_keys = {"name", "description", "instructions", "version"}
    return {k: v for k, v in input_data.items() if k in allowed_keys}
```

### Auditoria

```python
def log_skill_action(
    action: str,  # CREATE, UPDATE, DELETE, ASSIGN
    skill_id: str,
    agent_id: str = None,
    user_id: str = None,
    metadata: dict = None
):
    """Registra ação para auditoria"""
    event_bus.publish("skill_audit", {
        "action": action,
        "skill_id": skill_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata
    })
```

## Próximos Passos

1. Implementar Skill Registry
2. Criar modelo de dados SQLAlchemy
3. Implementar validações de estrutura e dependências
4. Criar API REST para CRUD de skills
5. Desenvolver interface de Skill Manager
6. Implementar sistema de instalação/remoção
7. Criar skills core iniciais
8. Implementar Skill Creator (IA)
9. Desenvolver marketplace (futuro)
