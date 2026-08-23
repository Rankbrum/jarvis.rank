"""
JARVIS AI - Unit Tests

Unit tests for core components.
Run with: pytest tests/unit/ -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Test EventBus
class TestEventBus:
    """Tests for EventBus component"""
    
    def test_event_creation(self):
        """Test event creation and serialization"""
        from backend.events.event_bus import Event, EventType
        
        event = Event(
            event_type=EventType.MISSION_CREATED,
            data={"mission_id": "test-123"},
            source="test",
        )
        
        assert event.event_type == EventType.MISSION_CREATED
        assert event.data["mission_id"] == "test-123"
        assert event.source == "test"
        
        # Test serialization
        event_dict = event.to_dict()
        assert "id" in event_dict
        assert event_dict["event_type"] == "mission_created"
        assert event_dict["data"]["mission_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_event_publish(self):
        """Test event publishing to subscribers"""
        from backend.events.event_bus import EventBus, EventType, Event
        
        bus = EventBus()
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        # Subscribe
        bus.subscribe(EventType.MISSION_CREATED, handler)
        
        # Publish
        event = Event(
            event_type=EventType.MISSION_CREATED,
            data={"test": "data"},
        )
        await bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0].data["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_event_history(self):
        """Test event history retrieval"""
        from backend.events.event_bus import EventBus, EventType
        
        bus = EventBus()
        bus.clear_history()
        
        # Publish multiple events
        for i in range(5):
            await bus.emit(
                EventType.MISSION_CREATED,
                data={"index": i},
            )
        
        # Get history
        history = bus.get_history(limit=3)
        assert len(history) == 3
        assert history[0].data["index"] == 4  # Most recent first


# Test AgentRegistry
class TestAgentRegistry:
    """Tests for AgentRegistry component"""
    
    def test_registry_singleton(self):
        """Test registry is a singleton"""
        from backend.agents.agent_registry import agent_registry, AgentRegistry
        
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        
        assert registry1 is registry2
        assert registry1 is agent_registry
    
    def test_hierarchy_validation(self):
        """Test hierarchy validation logic"""
        from backend.agents.agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Test cycle detection (mock graph)
        registry.graph.add_node("A")
        registry.graph.add_node("B")
        registry.graph.add_edge("A", "B")
        
        # B -> A would create a cycle
        assert registry._would_create_cycle("B", "A") == True
        
        # C -> B would not create a cycle
        assert registry._would_create_cycle("B", "C") == False


# Test SkillRegistry
class TestSkillRegistry:
    """Tests for SkillRegistry component"""
    
    def test_registry_singleton(self):
        """Test registry is a singleton"""
        from backend.skills.skill_registry import skill_registry, SkillRegistry
        
        registry1 = SkillRegistry()
        registry2 = SkillRegistry()
        
        assert registry1 is registry2
        assert registry1 is skill_registry
    
    def test_skill_definition(self):
        """Test skill definition creation"""
        from backend.skills.skill_registry import SkillDefinition
        
        skill = SkillDefinition(
            id="skill-123",
            name="Test Skill",
            version="1.0.0",
            description="A test skill",
            instructions="Do something",
            required_tools=["tool-1"],
            required_permissions=["READ_FILES"],
            compatible_modalities=["text"],
            dependencies=[],
            metadata={},
        )
        
        assert skill.name == "Test Skill"
        assert skill.version == "1.0.0"
        assert "READ_FILES" in skill.required_permissions
    
    def test_compatibility_validation(self):
        """Test agent-skill compatibility validation"""
        from backend.skills.skill_registry import SkillRegistry
        
        registry = SkillRegistry()
        
        # Mock skill
        mock_skill = MagicMock()
        mock_skill.enabled = True
        mock_skill.compatible_modalities = ["text", "vision"]
        mock_skill.required_permissions = ["READ_FILES"]
        mock_skill.required_tools = ["browser"]
        
        registry._skills["skill-123"] = mock_skill
        
        # Compatible agent
        is_valid, msg = registry.validate_agent_compatibility(
            "skill-123",
            ["text", "vision", "files"],
            ["READ_FILES", "WRITE_FILES"],
            ["browser", "filesystem"],
        )
        assert is_valid == True
    
    def test_incompatible_agent(self):
        """Test incompatible agent validation"""
        from backend.skills.skill_registry import SkillRegistry
        
        registry = SkillRegistry()
        
        mock_skill = MagicMock()
        mock_skill.enabled = True
        mock_skill.compatible_modalities = ["vision"]
        mock_skill.required_permissions = ["TERMINAL_EXECUTE"]
        mock_skill.required_tools = ["terminal"]
        
        registry._skills["skill-123"] = mock_skill
        
        # Incompatible agent (missing vision modality)
        is_valid, msg = registry.validate_agent_compatibility(
            "skill-123",
            ["text"],  # Missing vision
            ["READ_FILES"],  # Missing TERMINAL_EXECUTE
            ["browser"],  # Missing terminal
        )
        assert is_valid == False
        assert "modalities" in msg or "permissions" in msg or "tools" in msg


# Test ToolRegistry
class TestToolRegistry:
    """Tests for ToolRegistry component"""
    
    def test_registry_singleton(self):
        """Test registry is a singleton"""
        from backend.tools.tool_registry import tool_registry, ToolRegistry
        
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()
        
        assert registry1 is registry2
        assert registry1 is tool_registry
    
    def test_tool_result(self):
        """Test tool result creation"""
        from backend.tools.tool_registry import ToolResult
        
        result = ToolResult(
            success=True,
            data={"output": "success"},
            metadata={"latency_ms": 100},
        )
        
        assert result.success == True
        assert result.data["output"] == "success"
        assert result.metadata["latency_ms"] == 100
        
        result_dict = result.to_dict()
        assert "timestamp" in result_dict
    
    @pytest.mark.asyncio
    async def test_tool_execution_without_executor(self):
        """Test tool execution when no executor is defined"""
        from backend.tools.tool_registry import ToolRegistry, ToolDefinition
        
        registry = ToolRegistry()
        
        # Register mock tool without executor
        tool = ToolDefinition(
            id="tool-123",
            name="Test Tool",
            description="A test tool",
            tool_type="api",
            config_schema={},
            config={"key": "value"},
            required_permissions=[],
            enabled=True,
        )
        
        registry._tools["tool-123"] = tool
        
        # Execute
        result = await registry.execute_tool(
            "tool-123",
            "agent-456",
            {"input": "data"},
            [],
        )
        
        assert result.success == True
        assert "config" in result.data


# Test Orchestrator
class TestOrchestrator:
    """Tests for Orchestrator component"""
    
    def test_orchestrator_singleton(self):
        """Test orchestrator is a singleton"""
        from backend.core.orchestrator import orchestrator, Orchestrator
        
        orch1 = Orchestrator()
        orch2 = Orchestrator()
        
        assert orch1 is orch2
        assert orch1 is orchestrator
    
    def test_mission_plan_creation(self):
        """Test mission plan creation"""
        from backend.core.orchestrator import MissionPlan
        
        plan = MissionPlan("mission-123")
        
        step = plan.add_step(
            step_type="agent_execution",
            description="Test step",
            agent_id="agent-456",
            metadata={"key": "value"},
        )
        
        assert len(plan.steps) == 1
        assert step["type"] == "agent_execution"
        assert step["agent_id"] == "agent-456"
        
        plan_dict = plan.to_dict()
        assert plan_dict["mission_id"] == "mission-123"
        assert plan_dict["status"] == "planning"
    
    def test_limits_enforcement(self):
        """Test execution limits are enforced"""
        from backend.core.orchestrator import Orchestrator
        
        orch = Orchestrator()
        
        assert orch.max_concurrent_missions > 0
        assert orch.max_tasks_per_mission > 0
        assert orch.max_recursion_depth > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
