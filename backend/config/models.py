"""
JARVIS AI - SQLAlchemy Models

Database models for all entities in the system.
Uses SQLAlchemy 2.0+ async patterns.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from backend.config import Base


# Helper to generate UUID v7
def generate_uuid() -> str:
    """Generate a UUID v4 string"""
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(Base, TimestampMixin):
    """User entity"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    preferences = Column(JSON, default=dict)
    
    # Relationships
    agents = relationship("Agent", back_populates="owner", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
    )


class Agent(Base, TimestampMixin):
    """Agent entity with hierarchical support"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    
    # Hierarchy
    parent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Model configuration
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    model_strategy = Column(String(50), default="auto")
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    
    # Capabilities
    capabilities = Column(JSON, default=list)  # [text, vision, files, voice, video]
    
    # Configuration
    permissions = Column(JSON, default=list)
    tools = Column(JSON, default=list)
    skills = Column(JSON, default=list)
    memory_enabled = Column(Boolean, default=True)
    web_access = Column(Boolean, default=False)
    file_access = Column(Boolean, default=False)
    terminal_access = Column(Boolean, default=False)
    can_create_agents = Column(Boolean, default=False)
    can_delegate = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owner = relationship("User", back_populates="agents")
    parent = relationship("Agent", remote_side=[id], backref="children")
    skills_assigned = relationship("AgentSkill", back_populates="agent", cascade="all, delete-orphan")
    tools_assigned = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_agents_name", "name"),
        Index("ix_agents_parent", "parent_id"),
    )


class Skill(Base, TimestampMixin):
    """Skill entity - reusable competencies"""
    __tablename__ = "skills"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    version = Column(String(20), default="1.0.0")
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    
    # Requirements
    required_tools = Column(JSON, default=list)
    required_permissions = Column(JSON, default=list)
    compatible_modalities = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)  # Other skill IDs
    
    # Metadata
    skill_metadata = Column("metadata", JSON, default=dict)
    is_enabled = Column(Boolean, default=True)
    author = Column(String(100), nullable=True)
    
    # Relationships
    agents_using = relationship("AgentSkill", back_populates="skill", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_skills_name", "name"),
        UniqueConstraint("name", "version", name="uq_skills_name_version"),
    )


class Tool(Base, TimestampMixin):
    """Tool entity - external integrations"""
    __tablename__ = "tools"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    tool_type = Column(String(50), nullable=False)  # api, filesystem, terminal, etc.
    config_schema = Column(JSON, nullable=True)  # JSON Schema for config
    config = Column(JSON, default=dict)
    
    # Requirements
    required_permissions = Column(JSON, default=list)
    
    # Status
    is_enabled = Column(Boolean, default=True)
    
    # Relationships
    agents_using = relationship("AgentTool", back_populates="tool", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_tools_name", "name"),
    )


class AgentSkill(Base, TimestampMixin):
    """Association table between Agents and Skills"""
    __tablename__ = "agent_skills"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False, index=True)
    config = Column(JSON, default=dict)  # Skill-specific config
    is_active = Column(Boolean, default=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="skills_assigned")
    skill = relationship("Skill", back_populates="agents_using")
    
    __table_args__ = (
        UniqueConstraint("agent_id", "skill_id", name="uq_agent_skill"),
    )


class AgentTool(Base, TimestampMixin):
    """Association table between Agents and Tools"""
    __tablename__ = "agent_tools"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    tool_id = Column(String, ForeignKey("tools.id"), nullable=False, index=True)
    config = Column(JSON, default=dict)  # Tool-specific config
    is_active = Column(Boolean, default=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tools_assigned")
    tool = relationship("Tool", back_populates="agents_using")
    
    __table_args__ = (
        UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool"),
    )


class Provider(Base, TimestampMixin):
    """AI Provider entity"""
    __tablename__ = "providers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False)
    provider_type = Column(String(50), nullable=False)  # openai, anthropic, etc.
    
    # Configuration (encrypted in production)
    config = Column(JSON, default=dict)
    is_enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher = more priority
    
    # Limits
    rate_limit = Column(Integer, nullable=True)  # Requests per minute
    cost_limit = Column(Float, nullable=True)  # USD per day
    
    # Relationships
    models = relationship("Model", back_populates="provider", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_providers_name", "name"),
    )


class Model(Base, TimestampMixin):
    """AI Model entity"""
    __tablename__ = "models"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    
    # Capabilities
    modalities = Column(JSON, default=["text"])  # [text, vision, audio, etc.]
    max_context_length = Column(Integer, nullable=True)
    supports_streaming = Column(Boolean, default=True)
    supports_tools = Column(Boolean, default=False)
    supports_vision = Column(Boolean, default=False)
    
    # Cost (per 1M tokens)
    input_cost = Column(Float, default=0.0)
    output_cost = Column(Float, default=0.0)
    
    # Status
    is_enabled = Column(Boolean, default=True)
    is_fallback = Column(Boolean, default=False)
    
    # Relationships
    provider = relationship("Provider", back_populates="models")
    
    __table_args__ = (
        Index("ix_models_name", "name"),
        Index("ix_models_provider", "provider_id"),
        UniqueConstraint("provider_id", "name", name="uq_provider_model"),
    )


class MissionStatus(str, PyEnum):
    """Mission status enumeration"""
    WAITING = "waiting"
    PLANNING = "planning"
    RUNNING = "running"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Mission(Base, TimestampMixin):
    """Mission entity - top-level task"""
    __tablename__ = "missions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(Enum(MissionStatus), default=MissionStatus.WAITING)
    progress = Column(Integer, default=0)  # 0-100
    
    # Execution
    root_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    plan = Column(JSON, default=list)
    
    # Metrics
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="missions")
    tasks = relationship("Task", back_populates="mission", cascade="all, delete-orphan")
    executions = relationship("ExecutionLog", back_populates="mission", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_missions_status", "status"),
        Index("ix_missions_user", "user_id"),
    )


class TaskStatus(str, PyEnum):
    """Task status enumeration"""
    WAITING = "waiting"
    RUNNING = "running"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base, TimestampMixin):
    """Task entity - sub-task within a mission"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False, index=True)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True, index=True)
    
    # Assignment
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    
    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    
    # Status
    status = Column(Enum(TaskStatus), default=TaskStatus.WAITING)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metrics
    tokens_used = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    mission = relationship("Mission", back_populates="tasks")
    parent = relationship("Task", remote_side=[id], backref="subtasks")
    executions = relationship("ExecutionLog", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_mission", "mission_id"),
    )


class ExecutionLog(Base):
    """Execution log entity - detailed execution tracking"""
    __tablename__ = "execution_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # Event
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, default=dict)
    
    # Metrics
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    
    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    mission = relationship("Mission", back_populates="executions")
    task = relationship("Task", back_populates="executions")


class MemoryType(str, PyEnum):
    """Memory type enumeration"""
    WORKING = "working"
    CONVERSATION = "conversation"
    AGENT = "agent"
    USER = "user"
    KNOWLEDGE = "knowledge"


class Memory(Base, TimestampMixin):
    """Memory entity - multi-layer memory system"""
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    
    # Type
    memory_type = Column(Enum(MemoryType), nullable=False)
    
    # Content
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=False)
    memory_metadata = Column("metadata", JSON, default=dict)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    __table_args__ = (
        Index("ix_memories_type", "memory_type"),
        Index("ix_memories_key", "key"),
        UniqueConstraint("user_id", "agent_id", "key", name="uq_memory_unique"),
    )


class Event(Base):
    """Event entity - persisted events for audit/analysis"""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, default=dict)
    
    # Context
    source = Column(String(100), nullable=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_events_timestamp", "timestamp"),
        Index("ix_events_type", "event_type"),
    )


class Usage(Base):
    """Usage tracking entity"""
    __tablename__ = "usage"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=True)
    
    # Metrics
    requests_count = Column(Integer, default=0)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Period
    date = Column(DateTime, default=func.date('now'), index=True)
    
    __table_args__ = (
        Index("ix_usage_date", "date"),
        Index("ix_usage_user", "user_id"),
    )
