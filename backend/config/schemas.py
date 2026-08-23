"""
JARVIS AI - Pydantic Schemas

Schema definitions for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class ModelStrategy(str, Enum):
    """Model selection strategies"""
    AUTO = "auto"
    BEST_QUALITY = "best_quality"
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    FREE_FIRST = "free_first"
    LOCAL_ONLY = "local_only"
    MANUAL = "manual"


class MissionPriority(str, Enum):
    """Mission priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Capability(str, Enum):
    """Agent capabilities"""
    TEXT = "text"
    VISION = "vision"
    FILES = "files"
    VOICE = "voice"
    VIDEO = "video"
    AUDIO = "audio"


# ==================== AGENT SCHEMAS ====================

class AgentCreate(BaseModel):
    """Schema for creating an agent"""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: Optional[str] = Field(None, max_length=1000, description="Agent description")
    parent_id: Optional[UUID] = Field(None, description="Parent agent ID for hierarchy")
    instructions: Optional[str] = Field(None, description="System prompt/instructions")
    model_strategy: ModelStrategy = Field(ModelStrategy.AUTO, description="Model selection strategy")
    capabilities: List[Capability] = Field(default_factory=list, description="Agent capabilities")
    skills: List[str] = Field(default_factory=list, description="Skill IDs")
    tools: List[str] = Field(default_factory=list, description="Tool IDs")
    permissions: List[str] = Field(default_factory=list, description="Permission list")
    max_depth: int = Field(5, ge=1, le=10, description="Max delegation depth")


class AgentUpdate(BaseModel):
    """Schema for updating an agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    instructions: Optional[str] = Field(None)
    model_strategy: Optional[ModelStrategy] = None
    capabilities: Optional[List[Capability]] = None
    skills: Optional[List[str]] = None
    tools: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    max_depth: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    """Schema for agent response"""
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    model_strategy: str
    capabilities: List[str]
    skills: List[str]
    tools: List[str]
    permissions: List[str]
    max_depth: int
    enabled: bool
    created_at: Optional[datetime] = None


# ==================== MISSION SCHEMAS ====================

class MissionCreate(BaseModel):
    """Schema for creating a mission"""
    objective: str = Field(..., min_length=1, max_length=255, description="Mission objective")
    description: Optional[str] = Field(None, description="Mission description")
    priority: MissionPriority = Field(MissionPriority.NORMAL, description="Mission priority")
    assigned_agent_id: Optional[UUID] = Field(None, description="Agent to execute mission")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Context data")
    constraints: List[str] = Field(default_factory=list, description="Execution constraints")


class MissionResponse(BaseModel):
    """Schema for mission response"""
    id: str
    objective: str
    description: Optional[str] = None
    status: str
    priority: str
    assigned_agent_id: Optional[str] = None
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== SKILL SCHEMAS ====================

class SkillAssignment(BaseModel):
    """Schema for assigning a skill to an agent"""
    skill_id: UUID
    agent_id: UUID
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SkillCreate(BaseModel):
    """Schema for creating a skill"""
    name: str = Field(..., min_length=1, max_length=100)
    version: Optional[str] = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = Field(None, max_length=1000)
    instructions: Optional[str] = None
    required_permissions: List[str] = Field(default_factory=list)
    compatible_modalities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ==================== TOOL SCHEMAS ====================

class ToolExecute(BaseModel):
    """Schema for executing a tool"""
    tool_id: str
    agent_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


# ==================== EVENT SCHEMAS ====================

class EventMessage(BaseModel):
    """Schema for WebSocket event messages"""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None
    event_type: Optional[str] = None


class SubscribeRequest(BaseModel):
    """Schema for subscribing to events"""
    action: str = "subscribe"
    events: List[str] = Field(default_factory=list)


class UnsubscribeRequest(BaseModel):
    """Schema for unsubscribing from events"""
    action: str = "unsubscribe"
    events: List[str] = Field(default_factory=list)


# ==================== SYSTEM SCHEMAS ====================

class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    timestamp: datetime
    version: str
    components: Dict[str, str]


class StatsResponse(BaseModel):
    """Schema for system stats response"""
    total_agents: int
    total_skills: int
    total_tools: int
    total_missions: int
    missions_by_status: Dict[str, int]
    timestamp: datetime


# ==================== GRAPH SCHEMAS ====================

class GraphNode(BaseModel):
    """Schema for graph node"""
    id: str
    name: str
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    level: int = 0


class GraphEdge(BaseModel):
    """Schema for graph edge"""
    source: str
    target: str


class GraphResponse(BaseModel):
    """Schema for agent graph response"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    root_id: Optional[str] = None
    total_agents: int
    max_depth: int
