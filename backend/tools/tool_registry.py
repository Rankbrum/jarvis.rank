"""
JARVIS AI - Tool Registry

Manages tool lifecycle, discovery, and execution.
Tools are external integrations that agents can use.
"""

from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime
import logging
from uuid import uuid4
import os
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config.models import Tool, AgentTool
from backend.events.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)


class ToolDefinition:
    """Represents a tool definition"""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        tool_type: str,
        config_schema: Dict[str, Any],
        config: Dict[str, Any],
        required_permissions: List[str],
        enabled: bool = True,
        executor: Optional[Callable] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.tool_type = tool_type
        self.config_schema = config_schema
        self.config = config
        self.required_permissions = required_permissions
        self.enabled = enabled
        self.executor = executor  # Async function to execute the tool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "config_schema": self.config_schema,
            "config": self.config,
            "required_permissions": self.required_permissions,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_model(cls, model: Tool) -> "ToolDefinition":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            name=model.name,
            description=model.description or "",
            tool_type=model.tool_type,
            config_schema=model.config_schema or {},
            config=model.config or {},
            required_permissions=model.required_permissions or [],
            enabled=model.is_enabled,
        )


class ToolResult:
    """Represents the result of a tool execution"""
    
    def __init__(
        self,
        success: bool,
        data: Any,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.data = data
        self.error_message = error_message
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class ToolRegistry:
    """
    Central registry for all tools in the system.
    Supports dynamic loading and execution of tools.
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # In-memory cache of tools
        self._tools: Dict[str, ToolDefinition] = {}
        
        # Tools directory path
        self.tools_dir = "./backend/tools"
        
        # Ensure tools directory exists
        os.makedirs(self.tools_dir, exist_ok=True)
        
        self._initialized = True
        logger.info("ToolRegistry initialized")
    
    async def load_from_db(self, db: AsyncSession):
        """Load all tools from database into registry"""
        try:
            result = await db.execute(select(Tool))
            tools = result.scalars().all()
            
            for tool in tools:
                definition = ToolDefinition.from_model(tool)
                self._tools[tool.id] = definition
            
            logger.info(f"Loaded {len(tools)} tools from database")
            
        except Exception as e:
            logger.error(f"Failed to load tools from database: {e}")
            raise
    
    async def register_tool(
        self,
        db: AsyncSession,
        tool: ToolDefinition,
    ) -> ToolDefinition:
        """Register a new tool in the system"""
        # Check if tool already exists
        existing = await db.execute(
            select(Tool).where(Tool.name == tool.name)
        )
        existing_tool = existing.scalar_one_or_none()
        
        if existing_tool:
            raise ValueError(f"Tool with name '{tool.name}' already exists")
        
        # Create database record
        db_tool = Tool(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            tool_type=tool.tool_type,
            config_schema=tool.config_schema,
            config=tool.config,
            required_permissions=tool.required_permissions,
            is_enabled=tool.enabled,
        )
        
        db.add(db_tool)
        await db.commit()
        await db.refresh(db_tool)
        
        # Add to registry
        self._tools[db_tool.id] = ToolDefinition.from_model(db_tool)
        
        logger.info(f"Registered tool: {tool.name} ({tool.id})")
        return tool
    
    async def unregister_tool(self, db: AsyncSession, tool_id: str):
        """Remove a tool from the system"""
        if tool_id not in self._tools:
            raise ValueError(f"Tool {tool_id} not found")
        
        # Check if any agents are using this tool
        result = await db.execute(
            select(AgentTool).where(AgentTool.tool_id == tool_id)
        )
        usages = result.scalars().all()
        
        if usages:
            raise ValueError(
                f"Cannot remove tool: {len(usages)} agents are using it"
            )
        
        # Remove from database
        tool = await db.get(Tool, tool_id)
        if tool:
            await db.delete(tool)
            await db.commit()
        
        # Remove from registry
        del self._tools[tool_id]
        
        logger.info(f"Unregistered tool: {tool_id}")
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool by ID"""
        return self._tools.get(tool_id)
    
    def get_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name"""
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all registered tools"""
        return list(self._tools.values())
    
    def get_enabled_tools(self) -> List[ToolDefinition]:
        """Get all enabled tools"""
        return [t for t in self._tools.values() if t.enabled]
    
    async def execute_tool(
        self,
        tool_id: str,
        agent_id: str,
        input_data: Dict[str, Any],
        permissions: List[str],
    ) -> ToolResult:
        """
        Execute a tool with the given input.
        Validates permissions before execution.
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Tool {tool_id} not found",
            )
        
        if not tool.enabled:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Tool {tool.name} is disabled",
            )
        
        # Validate permissions
        missing_permissions = set(tool.required_permissions) - set(permissions)
        if missing_permissions:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Missing permissions: {missing_permissions}",
            )
        
        # Emit event
        await event_bus.emit(
            EventType.TOOL_CALLED,
            data={
                "tool_id": tool_id,
                "tool_name": tool.name,
                "agent_id": agent_id,
                "input": input_data,
            },
            agent_id=agent_id,
        )
        
        # Execute tool
        start_time = datetime.utcnow()
        try:
            if tool.executor:
                result_data = await tool.executor(input_data, tool.config)
            else:
                # Default executor - just return config
                result_data = {"message": f"Tool {tool.name} executed", "config": tool.config}
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            result = ToolResult(
                success=True,
                data=result_data,
                metadata={"latency_ms": latency_ms},
            )
            
            # Emit completion event
            await event_bus.emit(
                EventType.TOOL_COMPLETED,
                data={
                    "tool_id": tool_id,
                    "tool_name": tool.name,
                    "agent_id": agent_id,
                    "latency_ms": latency_ms,
                },
                agent_id=agent_id,
            )
            
            logger.info(f"Tool {tool.name} executed successfully in {latency_ms}ms")
            return result
            
        except Exception as e:
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.error(f"Tool {tool.name} execution failed: {e}")
            
            # Emit failure event
            await event_bus.emit(
                EventType.TOOL_FAILED,
                data={
                    "tool_id": tool_id,
                    "tool_name": tool.name,
                    "agent_id": agent_id,
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
                agent_id=agent_id,
            )
            
            return ToolResult(
                success=False,
                data=None,
                error_message=str(e),
                metadata={"latency_ms": latency_ms},
            )
    
    def validate_agent_compatibility(
        self,
        tool_id: str,
        agent_permissions: List[str],
    ) -> tuple[bool, str]:
        """
        Validate if an agent can use a specific tool.
        Returns (is_compatible, error_message)
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return False, f"Tool {tool_id} not found"
        
        if not tool.enabled:
            return False, f"Tool {tool.name} is disabled"
        
        # Check permissions
        missing_permissions = set(tool.required_permissions) - set(agent_permissions)
        if missing_permissions:
            return False, f"Agent lacks required permissions: {missing_permissions}"
        
        return True, ""
    
    def discover_tools_from_directory(self) -> List[ToolDefinition]:
        """Discover and load tools from the tools directory"""
        discovered = []
        
        if not os.path.exists(self.tools_dir):
            logger.warning(f"Tools directory not found: {self.tools_dir}")
            return discovered
        
        for filename in os.listdir(self.tools_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.tools_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    tool_def = ToolDefinition(
                        id=data.get("id", str(uuid4())),
                        name=data["name"],
                        description=data.get("description", ""),
                        tool_type=data.get("tool_type", "api"),
                        config_schema=data.get("config_schema", {}),
                        config=data.get("config", {}),
                        required_permissions=data.get("required_permissions", []),
                        enabled=data.get("enabled", True),
                    )
                    
                    discovered.append(tool_def)
                    logger.info(f"Discovered tool: {tool_def.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load tool from {filename}: {e}")
        
        return discovered


# Global registry instance
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Dependency for FastAPI to get tool registry"""
    return tool_registry
