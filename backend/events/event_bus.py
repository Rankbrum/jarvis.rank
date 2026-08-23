"""
JARVIS AI - Event System

Event bus for internal communication between components.
Supports synchronous and asynchronous event handling.
"""

import asyncio
from typing import Callable, Dict, List, Any, Optional, Coroutine
from datetime import datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events in the system"""
    
    # Mission Events
    MISSION_CREATED = "mission_created"
    MISSION_STARTED = "mission_started"
    MISSION_UPDATED = "mission_updated"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_CANCELLED = "mission_cancelled"
    
    # Task Events
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_DELEGATED = "task_delegated"
    
    # Agent Events
    AGENT_CREATED = "agent_created"
    AGENT_ACTIVATED = "agent_activated"
    AGENT_DEACTIVATED = "agent_deactivated"
    AGENT_DELEGATED = "agent_delegated"
    
    # Model/Provider Events
    MODEL_SELECTED = "model_selected"
    PROVIDER_CALLED = "provider_called"
    PROVIDER_FAILED = "provider_failed"
    FALLBACK_TRIGGERED = "fallback_triggered"
    
    # Skill/Tool Events
    SKILL_ACTIVATED = "skill_activated"
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    
    # Memory Events
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    
    # Permission Events
    PERMISSION_REQUESTED = "permission_requested"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    
    # Error Events
    ERROR_OCCURRED = "error_occurred"
    WARNING_OCCURRED = "warning_occurred"
    
    # User Events
    USER_MESSAGE = "user_message"
    ASSISTANT_RESPONSE = "assistant_response"
    
    # System Events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


class Event:
    """Represents an event in the system"""
    
    def __init__(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: Optional[str] = None,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        self.id = f"evt_{datetime.utcnow().timestamp()}_{id(self)}"
        self.event_type = event_type
        self.data = data
        self.source = source
        self.mission_id = mission_id
        self.task_id = task_id
        self.agent_id = agent_id
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "data": self.data,
            "source": self.source,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        event = cls(
            event_type=EventType(data["event_type"]),
            data=data.get("data", {}),
            source=data.get("source"),
            mission_id=data.get("mission_id"),
            task_id=data.get("task_id"),
            agent_id=data.get("agent_id"),
        )
        event.id = data["id"]
        event.timestamp = datetime.fromisoformat(data["timestamp"])
        return event


class EventBus:
    """
    Central event bus for publishing and subscribing to events.
    Thread-safe and supports async handlers.
    """
    
    _instance: Optional["EventBus"] = None
    
    def __new__(cls) -> "EventBus":
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
        
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._async_subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000  # Keep last 1000 events
        self._lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("EventBus initialized")
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
    ):
        """Subscribe a synchronous handler to an event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed sync handler to {event_type.value}")
    
    def subscribe_async(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
    ):
        """Subscribe an asynchronous handler to an event type"""
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
        self._async_subscribers[event_type].append(handler)
        logger.debug(f"Subscribed async handler to {event_type.value}")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable,
    ):
        """Unsubscribe a handler from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
        if event_type in self._async_subscribers:
            self._async_subscribers[event_type].remove(handler)
    
    async def publish(self, event: Event):
        """
        Publish an event to all subscribers.
        Async handlers are awaited, sync handlers are called normally.
        """
        # Store in history
        async with self._lock:
            self._event_history.append(event)
            # Trim history if too long
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
        
        logger.debug(f"Publishing event: {event.event_type.value}")
        
        # Call sync handlers
        sync_handlers = self._subscribers.get(event.event_type, [])
        for handler in sync_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Sync handler error for {event.event_type.value}: {e}")
        
        # Call async handlers
        async_handlers = self._async_subscribers.get(event.event_type, [])
        if async_handlers:
            tasks = [handler(event) for handler in async_handlers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Async handler error for {event.event_type.value}: {result}"
                    )
    
    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: Optional[str] = None,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        """
        Convenience method to create and publish an event in one call.
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
            mission_id=mission_id,
            task_id=task_id,
            agent_id=agent_id,
        )
        await self.publish(event)
        return event
    
    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        mission_id: Optional[str] = None,
    ) -> List[Event]:
        """
        Get event history with optional filtering.
        """
        history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        if mission_id:
            history = [e for e in history if e.mission_id == mission_id]
        
        # Return most recent first, limited
        return list(reversed(history))[:limit]
    
    def clear_history(self):
        """Clear event history"""
        self._event_history.clear()
        logger.info("Event history cleared")


# Global event bus instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Dependency for FastAPI to get event bus"""
    return event_bus
