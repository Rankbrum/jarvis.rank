"""
JARVIS AI - API Routes

Endpoints REST para gerenciamento de agentes, missões, skills e tools.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

from backend.agents.agent_registry import AgentRegistry
from backend.skills.skill_registry import SkillRegistry
from backend.tools.tool_registry import ToolRegistry
from backend.core.orchestrator import Orchestrator
from backend.events.event_bus import EventBus
from backend.config.schemas import AgentCreate, AgentUpdate, MissionCreate, SkillAssignment

# Routers
router = APIRouter(prefix="/api", tags=["jarvis"])

# Dependencies (singleton instances)
def get_agent_registry() -> AgentRegistry:
    return AgentRegistry.get_instance()

def get_skill_registry() -> SkillRegistry:
    return SkillRegistry.get_instance()

def get_tool_registry() -> ToolRegistry:
    return ToolRegistry.get_instance()

def get_orchestrator() -> Orchestrator:
    return Orchestrator.get_instance()

def get_event_bus() -> EventBus:
    return EventBus.get_instance()


# ==================== AGENTS ====================

@router.post("/agents", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Criar um novo agente no sistema."""
    try:
        agent_id = registry.create_agent(
            name=agent_data.name,
            description=agent_data.description,
            parent_id=agent_data.parent_id,
            instructions=agent_data.instructions,
            model_strategy=agent_data.model_strategy,
            capabilities=agent_data.capabilities,
            skills=agent_data.skills,
            tools=agent_data.tools,
            permissions=agent_data.permissions,
            max_depth=agent_data.max_depth
        )
        
        return {
            "id": str(agent_id),
            "name": agent_data.name,
            "status": "created",
            "message": f"Agent '{agent_data.name}' created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents", response_model=List[dict])
async def list_agents(registry: AgentRegistry = Depends(get_agent_registry)):
    """Listar todos os agentes do sistema."""
    agents = registry.list_agents()
    return [
        {
            "id": str(agent["id"]),
            "name": agent["name"],
            "description": agent.get("description", ""),
            "parent_id": str(agent.get("parent_id")) if agent.get("parent_id") else None,
            "capabilities": agent.get("capabilities", []),
            "skills": agent.get("skills", []),
            "tools": agent.get("tools", []),
            "created_at": agent.get("created_at", "").isoformat() if isinstance(agent.get("created_at"), datetime) else agent.get("created_at")
        }
        for agent in agents
    ]


@router.get("/agents/{agent_id}", response_model=dict)
async def get_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Obter detalhes de um agente específico."""
    try:
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        
        return {
            "id": str(agent["id"]),
            "name": agent["name"],
            "description": agent.get("description", ""),
            "instructions": agent.get("instructions", ""),
            "parent_id": str(agent.get("parent_id")) if agent.get("parent_id") else None,
            "children": [str(c) for c in agent.get("children", [])],
            "model_strategy": agent.get("model_strategy", "AUTO"),
            "capabilities": agent.get("capabilities", []),
            "skills": agent.get("skills", []),
            "tools": agent.get("tools", []),
            "permissions": agent.get("permissions", []),
            "max_depth": agent.get("max_depth", 5),
            "enabled": agent.get("enabled", True),
            "created_at": agent.get("created_at", "").isoformat() if isinstance(agent.get("created_at"), datetime) else agent.get("created_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/agents/{agent_id}", response_model=dict)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Atualizar um agente existente."""
    try:
        updated = registry.update_agent(agent_id, agent_data.model_dump(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        
        return {
            "id": str(agent_id),
            "status": "updated",
            "message": f"Agent {agent_id} updated successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/agents/{agent_id}", response_model=dict)
async def delete_agent(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Remover um agente do sistema."""
    try:
        deleted = registry.delete_agent(agent_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        
        return {
            "id": str(agent_id),
            "status": "deleted",
            "message": f"Agent {agent_id} deleted successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents/graph", response_model=dict)
async def get_agent_graph(registry: AgentRegistry = Depends(get_agent_registry)):
    """Obter o grafo completo de agentes."""
    try:
        graph_data = registry.get_graph_structure()
        return {
            "nodes": [
                {
                    "id": str(node["id"]),
                    "name": node["name"],
                    "parent_id": str(node.get("parent_id")) if node.get("parent_id") else None,
                    "children": [str(c) for c in node.get("children", [])],
                    "capabilities": node.get("capabilities", []),
                    "skills": node.get("skills", []),
                    "level": node.get("level", 0)
                }
                for node in graph_data.get("nodes", [])
            ],
            "edges": [
                {
                    "source": str(edge["source"]),
                    "target": str(edge["target"])
                }
                for edge in graph_data.get("edges", [])
            ],
            "root_id": str(graph_data.get("root_id")) if graph_data.get("root_id") else None,
            "total_agents": graph_data.get("total_agents", 0),
            "max_depth": graph_data.get("max_depth", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents/{agent_id}/children", response_model=List[dict])
async def get_agent_children(
    agent_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Obter filhos diretos de um agente."""
    try:
        children = registry.get_children(agent_id)
        return [
            {
                "id": str(child["id"]),
                "name": child["name"],
                "description": child.get("description", ""),
                "capabilities": child.get("capabilities", []),
                "skills": child.get("skills", [])
            }
            for child in children
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/agents/{agent_id}/delegate", response_model=dict)
async def delegate_task(
    agent_id: UUID,
    task_data: dict,
    registry: AgentRegistry = Depends(get_agent_registry),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Delegar uma tarefa para um agente específico."""
    try:
        # Validar se o agente existe
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        
        # Criar missão para a tarefa delegada
        mission_id = await orchestrator.create_mission(
            objective=task_data.get("objective", "Task delegation"),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", "normal"),
            assigned_agent_id=agent_id
        )
        
        return {
            "mission_id": str(mission_id),
            "agent_id": str(agent_id),
            "status": "delegated",
            "message": f"Task delegated to agent {agent['name']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== MISSIONS ====================

@router.post("/missions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_mission(
    mission_data: MissionCreate,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Criar uma nova missão."""
    try:
        mission_id = await orchestrator.create_mission(
            objective=mission_data.objective,
            description=mission_data.description,
            priority=mission_data.priority,
            assigned_agent_id=mission_data.assigned_agent_id,
            context=mission_data.context,
            constraints=mission_data.constraints
        )
        
        return {
            "mission_id": str(mission_id),
            "objective": mission_data.objective,
            "status": "created",
            "message": f"Mission '{mission_data.objective}' created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/missions", response_model=List[dict])
async def list_missions(orchestrator: Orchestrator = Depends(get_orchestrator)):
    """Listar todas as missões."""
    missions = orchestrator.list_missions()
    return [
        {
            "id": str(mission["id"]),
            "objective": mission["objective"],
            "status": mission["status"],
            "priority": mission.get("priority", "normal"),
            "created_at": mission.get("created_at", "").isoformat() if isinstance(mission.get("created_at"), datetime) else mission.get("created_at"),
            "updated_at": mission.get("updated_at", "").isoformat() if isinstance(mission.get("updated_at"), datetime) else mission.get("updated_at")
        }
        for mission in missions
    ]


@router.get("/missions/{mission_id}", response_model=dict)
async def get_mission(
    mission_id: UUID,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Obter detalhes de uma missão específica."""
    try:
        mission = orchestrator.get_mission(mission_id)
        if not mission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission {mission_id} not found")
        
        return {
            "id": str(mission["id"]),
            "objective": mission["objective"],
            "description": mission.get("description", ""),
            "status": mission["status"],
            "priority": mission.get("priority", "normal"),
            "assigned_agent_id": str(mission.get("assigned_agent_id")) if mission.get("assigned_agent_id") else None,
            "tasks": mission.get("tasks", []),
            "results": mission.get("results", {}),
            "context": mission.get("context", {}),
            "constraints": mission.get("constraints", []),
            "created_at": mission.get("created_at", "").isoformat() if isinstance(mission.get("created_at"), datetime) else mission.get("created_at"),
            "updated_at": mission.get("updated_at", "").isoformat() if isinstance(mission.get("updated_at"), datetime) else mission.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/missions/{mission_id}/execute", response_model=dict)
async def execute_mission(
    mission_id: UUID,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Executar uma missão."""
    try:
        result = await orchestrator.execute_mission(mission_id)
        return {
            "mission_id": str(mission_id),
            "status": "executing" if result.get("success") else "failed",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/missions/{mission_id}/cancel", response_model=dict)
async def cancel_mission(
    mission_id: UUID,
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Cancelar uma missão em execução."""
    try:
        cancelled = orchestrator.cancel_mission(mission_id)
        if not cancelled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission {mission_id} not found or cannot be cancelled")
        
        return {
            "mission_id": str(mission_id),
            "status": "cancelled",
            "message": f"Mission {mission_id} cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== SKILLS ====================

@router.get("/skills", response_model=List[dict])
async def list_skills(registry: SkillRegistry = Depends(get_skill_registry)):
    """Listar todas as skills disponíveis."""
    skills = registry.list_skills()
    return [
        {
            "id": str(skill["id"]),
            "name": skill["name"],
            "version": skill.get("version", "1.0.0"),
            "description": skill.get("description", ""),
            "enabled": skill.get("enabled", True),
            "required_permissions": skill.get("required_permissions", []),
            "compatible_modalities": skill.get("compatible_modalities", []),
            "dependencies": skill.get("dependencies", [])
        }
        for skill in skills
    ]


@router.get("/skills/{skill_id}", response_model=dict)
async def get_skill(
    skill_id: UUID,
    registry: SkillRegistry = Depends(get_skill_registry)
):
    """Obter detalhes de uma skill específica."""
    try:
        skill = registry.get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill {skill_id} not found")
        
        return {
            "id": str(skill["id"]),
            "name": skill["name"],
            "version": skill.get("version", "1.0.0"),
            "description": skill.get("description", ""),
            "instructions": skill.get("instructions", ""),
            "enabled": skill.get("enabled", True),
            "required_permissions": skill.get("required_permissions", []),
            "compatible_modalities": skill.get("compatible_modalities", []),
            "dependencies": skill.get("dependencies", []),
            "metadata": skill.get("metadata", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/skills", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: dict,
    registry: SkillRegistry = Depends(get_skill_registry)
):
    """Registrar uma nova skill."""
    try:
        skill_id = registry.register_skill(
            name=skill_data["name"],
            description=skill_data.get("description", ""),
            version=skill_data.get("version", "1.0.0"),
            instructions=skill_data.get("instructions", ""),
            required_permissions=skill_data.get("required_permissions", []),
            compatible_modalities=skill_data.get("compatible_modalities", ["text"]),
            dependencies=skill_data.get("dependencies", []),
            metadata=skill_data.get("metadata", {})
        )
        
        return {
            "id": str(skill_id),
            "name": skill_data["name"],
            "status": "registered",
            "message": f"Skill '{skill_data['name']}' registered successfully"
        }
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required field: {e}")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/agents/{agent_id}/skills/assign", response_model=dict)
async def assign_skill_to_agent(
    agent_id: UUID,
    skill_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry),
    skill_registry: SkillRegistry = Depends(get_skill_registry)
):
    """Atribuir uma skill a um agente."""
    try:
        # Validar existência
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        
        skill = skill_registry.get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill {skill_id} not found")
        
        # Atribuir skill
        success = registry.assign_skill_to_agent(agent_id, skill_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to assign skill to agent")
        
        return {
            "agent_id": str(agent_id),
            "skill_id": str(skill_id),
            "status": "assigned",
            "message": f"Skill '{skill['name']}' assigned to agent '{agent['name']}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/agents/{agent_id}/skills/{skill_id}", response_model=dict)
async def remove_skill_from_agent(
    agent_id: UUID,
    skill_id: UUID,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """Remover uma skill de um agente."""
    try:
        success = registry.remove_skill_from_agent(agent_id, skill_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not assigned to agent or agent not found")
        
        return {
            "agent_id": str(agent_id),
            "skill_id": str(skill_id),
            "status": "removed",
            "message": f"Skill removed from agent {agent_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== TOOLS ====================

@router.get("/tools", response_model=List[dict])
async def list_tools(registry: ToolRegistry = Depends(get_tool_registry)):
    """Listar todas as tools disponíveis."""
    tools = registry.list_tools()
    return [
        {
            "id": str(tool["id"]),
            "name": tool["name"],
            "description": tool.get("description", ""),
            "enabled": tool.get("enabled", True),
            "required_permissions": tool.get("required_permissions", []),
            "parameters": tool.get("parameters", {})
        }
        for tool in tools
    ]


@router.get("/tools/{tool_id}", response_model=dict)
async def get_tool(
    tool_id: UUID,
    registry: ToolRegistry = Depends(get_tool_registry)
):
    """Obter detalhes de uma tool específica."""
    try:
        tool = registry.get_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool {tool_id} not found")
        
        return {
            "id": str(tool["id"]),
            "name": tool["name"],
            "description": tool.get("description", ""),
            "enabled": tool.get("enabled", True),
            "required_permissions": tool.get("required_permissions", []),
            "parameters": tool.get("parameters", {}),
            "metadata": tool.get("metadata", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/tools/execute", response_model=dict)
async def execute_tool(
    tool_execution: dict,
    registry: ToolRegistry = Depends(get_tool_registry),
    event_bus: EventBus = Depends(get_event_bus)
):
    """Executar uma tool com parâmetros específicos."""
    try:
        tool_id = UUID(tool_execution["tool_id"])
        parameters = tool_execution.get("parameters", {})
        agent_id = UUID(tool_execution["agent_id"]) if tool_execution.get("agent_id") else None
        
        # Executar tool
        result = await registry.execute_tool(tool_id, parameters, agent_id)
        
        # Publicar evento
        await event_bus.publish("tool_executed", {
            "tool_id": str(tool_id),
            "agent_id": str(agent_id) if agent_id else None,
            "success": result.success,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "tool_id": str(tool_id),
            "success": result.success,
            "result": result.data,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms
        }
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required field: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== SYSTEM ====================

@router.get("/health", response_model=dict)
async def health_check():
    """Verificar saúde do sistema."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.2.0",
        "components": {
            "api": "ok",
            "orchestrator": "ok",
            "agent_registry": "ok",
            "skill_registry": "ok",
            "tool_registry": "ok",
            "event_bus": "ok"
        }
    }


@router.get("/stats", response_model=dict)
async def get_system_stats(
    agent_registry: AgentRegistry = Depends(get_agent_registry),
    skill_registry: SkillRegistry = Depends(get_skill_registry),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Obter estatísticas do sistema."""
    agents = agent_registry.list_agents()
    skills = skill_registry.list_skills()
    tools = tool_registry.list_tools()
    missions = orchestrator.list_missions()
    
    return {
        "total_agents": len(agents),
        "total_skills": len(skills),
        "total_tools": len(tools),
        "total_missions": len(missions),
        "missions_by_status": {
            "pending": len([m for m in missions if m["status"] == "PENDING"]),
            "running": len([m for m in missions if m["status"] == "RUNNING"]),
            "completed": len([m for m in missions if m["status"] == "COMPLETED"]),
            "failed": len([m for m in missions if m["status"] == "FAILED"])
        },
        "timestamp": datetime.utcnow().isoformat()
    }
