"""
JARVIS AI - Event System

Event bus for internal communication between components.
Supports synchronous and asynchronous event handling.
"""

from .event_bus import (
    EventType,
    Event,
    EventBus,
    event_bus,
    get_event_bus,
)

__all__ = [
    "EventType",
    "Event",
    "EventBus",
    "event_bus",
    "get_event_bus",
]