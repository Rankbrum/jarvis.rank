"""
JARVIS AI - Orchestrator

Main brain of the JARVIS system.
Receives user requests, interprets intent, creates plans, and orchestrates agents.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.models import (
    Mission, MissionStatus, Task, TaskStatus,
    Agent, ExecutionLog, User
)
from events.event_bus import event_bus, EventType
from agents.agent_registry import agent_registry, AgentNode
from skills.skill_registry import skill_registry
from tools.tool_registry import tool_registry

logger = logging.getLogger(__name__)


class MissionPlan:
    """Represents a plan for executing a mission"""
    
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.steps: List[Dict[str, Any]] = []
        self.assigned_agents: Dict[str, str] = {}  # task_id -> agent_id
        self.status = "planning"
        self.created_at = datetime.utcnow()
    
    def add_step(
        self,
        step_type: str,
        description: str,
        agent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a step to the plan"""
        step = {
            "id": f"step_{uuid4().hex[:8]}",
            "type": step_type,
            "description": description,
            "agent_id": agent_id,
            "dependencies": dependencies or [],
            "metadata": metadata or {},
            "status": "pending",
            "created_at": datetime.utcnow(),
        }
        self.steps.append(step)
        return step
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "mission_id": self.mission_id,
            "steps": self.steps,
            "assigned_agents": self.assigned_agents,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class Orchestrator:
    """
    Main orchestrator for the JARVIS system.
    Handles mission lifecycle, planning, and agent coordination.
    """
    
    _instance: Optional["Orchestrator"] = None
    
    def __new__(cls) -> "Orchestrator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    
    def __init__(self):
        if self._initialized:
            return
        
        # Active missions
        self._active_missions: Dict[str, MissionPlan] = {}
        
        # Execution limits
        self.max_concurrent_missions = 10
        self.max_tasks_per_mission = 200
        self.max_recursion_depth = 10
        
        self._initialized = True
        logger.info("Orchestrator initialized")
    
    async def create_mission(
        self,
        db: AsyncSession,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        root_agent_id: Optional[str] = None,
    ) -> Mission:
        """Create a new mission"""
        # Check concurrent missions limit
        active_count = len([
            m for m in self._active_missions.values()
            if m.status == "running"
        ])
        
        if active_count >= self.max_concurrent_missions:
            raise ValueError(
                f"Maximum concurrent missions ({self.max_concurrent_missions}) reached"
            )
        
        # Create mission record
        mission = Mission(
            user_id=user_id,
            title=title,
            description=description,
            status=MissionStatus.WAITING,
            root_agent_id=root_agent_id,
        )
        
        db.add(mission)
        await db.commit()
        await db.refresh(mission)
        
        # Emit event
        await event_bus.emit(
            EventType.MISSION_CREATED,
            data={
                "mission_id": mission.id,
                "title": title,
                "user_id": user_id,
            },
            mission_id=mission.id,
        )
        
        logger.info(f"Created mission: {title} ({mission.id})")
        return mission
    
    async def plan_mission(
        self,
        db: AsyncSession,
        mission_id: str,
        request: str,
        root_agent_id: Optional[str] = None,
    ) -> MissionPlan:
        """
        Create a plan for executing a mission.
        This is where intent analysis and task breakdown happen.
        """
        mission = await db.get(Mission, mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")
        
        # Update status
        mission.status = MissionStatus.PLANNING
        mission.started_at = datetime.utcnow()
        await db.commit()
        
        # Create plan
        plan = MissionPlan(mission_id)
        plan.status = "planning"
        
        # Determine root agent
        if not root_agent_id:
            # Find best agent for the request
            root_agent_id = await self._select_best_agent(db, request)
        
        if root_agent_id:
            agent_node = agent_registry.get_agent(root_agent_id)
            if agent_node:
                # Add initial task
                plan.add_step(
                    step_type="agent_execution",
                    description=f"Execute with {agent_node.name}",
                    agent_id=root_agent_id,
                    metadata={"request": request},
                )
                plan.assigned_agents[f"task_{uuid4().hex[:8]}"] = root_agent_id
        
        # Store plan
        self._active_missions[mission_id] = plan
        mission.plan = plan.to_dict()["steps"]
        await db.commit()
        
        # Emit event
        await event_bus.emit(
            EventType.MISSION_STARTED,
            data={
                "mission_id": mission_id,
                "plan_steps": len(plan.steps),
            },
            mission_id=mission_id,
        )
        
        logger.info(f"Planned mission {mission_id} with {len(plan.steps)} steps")
        return plan
    
    async def execute_mission(
        self,
        db: AsyncSession,
        mission_id: str,
    ):
        """Execute a mission plan"""
        mission = await db.get(Mission, mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")
        
        plan = self._active_missions.get(mission_id)
        if not plan:
            raise ValueError(f"No plan found for mission {mission_id}")
        
        # Update status
        mission.status = MissionStatus.RUNNING
        plan.status = "running"
        await db.commit()
        
        try:
            # Execute each step
            for step in plan.steps:
                if step["type"] == "agent_execution":
                    await self._execute_agent_task(
                        db,
                        mission_id,
                        step,
                    )
            
            # Mark as completed
            mission.status = MissionStatus.COMPLETED
            mission.completed_at = datetime.utcnow()
            await db.commit()
            
            # Emit event
            await event_bus.emit(
                EventType.MISSION_COMPLETED,
                data={"mission_id": mission_id},
                mission_id=mission_id,
            )
            
            logger.info(f"Mission {mission_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Mission {mission_id} failed: {e}")
            
            mission.status = MissionStatus.FAILED
            await db.commit()
            
            # Emit event
            await event_bus.emit(
                EventType.MISSION_FAILED,
                data={
                    "mission_id": mission_id,
                    "error": str(e),
                },
                mission_id=mission_id,
            )
            
            raise
    
    async def _execute_agent_task(
        self,
        db: AsyncSession,
        mission_id: str,
        step: Dict[str, Any],
    ):
        """Execute a task with an agent"""
        agent_id = step.get("agent_id")
        if not agent_id:
            raise ValueError("No agent assigned to step")
        
        agent_node = agent_registry.get_agent(agent_id)
        if not agent_node:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Create task record
        task = Task(
            mission_id=mission_id,
            agent_id=agent_id,
            title=step["description"],
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Emit event
        await event_bus.emit(
            EventType.TASK_STARTED,
            data={
                "task_id": task.id,
                "agent_id": agent_id,
                "title": task.title,
            },
            task_id=task.id,
            agent_id=agent_id,
        )
        
        try:
            # Here we would call the AI provider
            # For now, simulate execution
            await asyncio.sleep(0.1)
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = "Task executed successfully"
            await db.commit()
            
            # Log execution
            log = ExecutionLog(
                mission_id=mission_id,
                task_id=task.id,
                agent_id=agent_id,
                event_type="task_completed",
                event_data={"result": task.result},
                success=True,
            )
            db.add(log)
            await db.commit()
            
            # Emit event
            await event_bus.emit(
                EventType.TASK_COMPLETED,
                data={
                    "task_id": task.id,
                    "result": task.result,
                },
                task_id=task.id,
            )
            
            logger.info(f"Task {task.id} completed")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            await db.commit()
            
            # Log error
            log = ExecutionLog(
                mission_id=mission_id,
                task_id=task.id,
                agent_id=agent_id,
                event_type="task_failed",
                event_data={"error": str(e)},
                success=False,
                error_message=str(e),
            )
            db.add(log)
            await db.commit()
            
            raise
    
    async def _select_best_agent(
        self,
        db: AsyncSession,
        request: str,
    ) -> Optional[str]:
        """Select the best agent for a given request"""
        # Get all root agents
        roots = agent_registry.get_root_agents()
        
        if not roots:
            # No agents configured, return None
            logger.warning("No agents configured in the system")
            return None
        
        # For MVP, just return the first root agent
        # In production, this would use AI to analyze the request
        # and match against agent capabilities/skills
        return roots[0].id if roots else None
    
    async def delegate_task(
        self,
        db: AsyncSession,
        mission_id: str,
        parent_task_id: str,
        agent_id: str,
        description: str,
    ) -> Task:
        """Delegate a subtask to another agent"""
        # Validate delegation
        parent_task = await db.get(Task, parent_task_id)
        if not parent_task:
            raise ValueError(f"Parent task {parent_task_id} not found")
        
        # Check recursion depth
        depth = await self._get_task_depth(db, parent_task_id)
        if depth >= self.max_recursion_depth:
            raise ValueError(
                f"Maximum recursion depth ({self.max_recursion_depth}) reached"
            )
        
        # Validate agent can receive delegation
        is_valid, error_msg = agent_registry.validate_delegation(
            parent_task.agent_id,
            agent_id,
        )
        
        if not is_valid:
            raise ValueError(f"Invalid delegation: {error_msg}")
        
        # Create subtask
        task = Task(
            mission_id=mission_id,
            parent_task_id=parent_task_id,
            agent_id=agent_id,
            title=description,
            status=TaskStatus.WAITING,
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Emit event
        await event_bus.emit(
            EventType.TASK_DELEGATED,
            data={
                "task_id": task.id,
                "parent_task_id": parent_task_id,
                "agent_id": agent_id,
            },
            task_id=task.id,
            agent_id=agent_id,
        )
        
        logger.info(f"Delegated task {task.id} to agent {agent_id}")
        return task
    
    async def _get_task_depth(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> int:
        """Get the depth of a task in the hierarchy"""
        depth = 0
        current = await db.get(Task, task_id)
        
        while current and current.parent_task_id:
            depth += 1
            current = await db.get(Task, current.parent_task_id)
        
        return depth
    
    def get_mission_plan(self, mission_id: str) -> Optional[MissionPlan]:
        """Get the plan for a mission"""
        return self._active_missions.get(mission_id)
    
    async def cancel_mission(
        self,
        db: AsyncSession,
        mission_id: str,
    ):
        """Cancel a running mission"""
        mission = await db.get(Mission, mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission.status = MissionStatus.CANCELLED
        await db.commit()
        
        # Remove from active missions
        if mission_id in self._active_missions:
            del self._active_missions[mission_id]
        
        # Emit event
        await event_bus.emit(
            EventType.MISSION_CANCELLED,
            data={"mission_id": mission_id},
            mission_id=mission_id,
        )
        
        logger.info(f"Cancelled mission {mission_id}")


# Global orchestrator instance
orchestrator = Orchestrator()


def get_orchestrator() -> Orchestrator:
    """Dependency for FastAPI to get orchestrator"""
    return orchestrator
