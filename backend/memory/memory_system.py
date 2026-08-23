"""
JARVIS AI - Memory System

Implements the 5-layer memory architecture:
1. Working Memory - Short-term context for active tasks
2. Conversation Memory - Chat history and dialogue context
3. Agent Memory - Agent-specific knowledge and experiences
4. User Memory - User preferences, habits, and profile
5. Knowledge Memory - Long-term factual knowledge base
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
from uuid import uuid4
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Base memory entry structure"""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: Any = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if memory entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "tags": self.tags,
        }


class MemoryLayer(ABC):
    """Abstract base class for memory layers"""
    
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry, returns entry ID"""
        pass
    
    @abstractmethod
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memory entries by content/metadata"""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry"""
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """Clear all memories in this layer, returns count of deleted entries"""
        pass


class WorkingMemory(MemoryLayer):
    """
    Working Memory - Short-term context for active tasks
    
    Volatile memory that holds information needed for current operations.
    Automatically expires after task completion or timeout.
    """
    
    def __init__(self, max_entries: int = 100, ttl_minutes: int = 30):
        self._memories: Dict[str, MemoryEntry] = {}
        self.max_entries = max_entries
        self.ttl = timedelta(minutes=ttl_minutes)
        logger.info("WorkingMemory initialized")
    
    async def store(self, entry: MemoryEntry) -> str:
        # Set expiration
        if entry.expires_at is None:
            entry.expires_at = datetime.utcnow() + self.ttl
        
        # Enforce max entries (LRU eviction)
        if len(self._memories) >= self.max_entries:
            oldest = min(self._memories.items(), key=lambda x: x[1].created_at)
            await self.delete(oldest[0])
        
        self._memories[entry.id] = entry
        logger.debug(f"WorkingMemory stored: {entry.id}")
        return entry.id
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self._memories.get(entry_id)
        if entry and entry.is_expired():
            await self.delete(entry_id)
            return None
        return entry
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        # Simple text search in content and tags
        results = []
        query_lower = query.lower()
        
        for entry in self._memories.values():
            if entry.is_expired():
                continue
            
            content_str = str(entry.content).lower() if entry.content else ""
            tags_str = " ".join(entry.tags).lower()
            
            if query_lower in content_str or query_lower in tags_str:
                results.append(entry)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def delete(self, entry_id: str) -> bool:
        if entry_id in self._memories:
            del self._memories[entry_id]
            logger.debug(f"WorkingMemory deleted: {entry_id}")
            return True
        return False
    
    async def clear(self) -> int:
        count = len(self._memories)
        self._memories.clear()
        logger.info(f"WorkingMemory cleared: {count} entries")
        return count
    
    async def get_all(self) -> List[MemoryEntry]:
        """Get all non-expired memories"""
        return [e for e in self._memories.values() if not e.is_expired()]


class ConversationMemory(MemoryLayer):
    """
    Conversation Memory - Chat history and dialogue context
    
    Stores conversation turns between user and agents.
    Maintains context for multi-turn dialogues.
    """
    
    def __init__(self, max_turns_per_session: int = 100):
        self._sessions: Dict[str, List[MemoryEntry]] = {}
        self.max_turns = max_turns_per_session
        logger.info("ConversationMemory initialized")
    
    async def add_turn(
        self,
        session_id: str,
        role: Literal["user", "assistant", "system"],
        content: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Add a conversation turn"""
        entry = MemoryEntry(
            content={
                "role": role,
                "content": content,
            },
            metadata=metadata or {},
            tags=["conversation", role, session_id],
        )
        
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        session = self._sessions[session_id]
        session.append(entry)
        
        # Enforce max turns
        if len(session) > self.max_turns:
            session.pop(0)
        
        await self.store(entry)
        return entry.id
    
    async def get_session(self, session_id: str) -> List[MemoryEntry]:
        """Get all turns in a conversation session"""
        return self._sessions.get(session_id, [])
    
    async def store(self, entry: MemoryEntry) -> str:
        # Implementation for ABC compliance
        # Actual storage happens in add_turn
        return entry.id
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        for session in self._sessions.values():
            for entry in session:
                if entry.id == entry_id:
                    return entry
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()
        
        for session in self._sessions.values():
            for entry in session:
                content_str = str(entry.content).lower() if entry.content else ""
                if query_lower in content_str:
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        
        return results
    
    async def delete(self, entry_id: str) -> bool:
        for session in self._sessions.values():
            for i, entry in enumerate(session):
                if entry.id == entry_id:
                    session.pop(i)
                    return True
        return False
    
    async def clear(self) -> int:
        count = sum(len(s) for s in self._sessions.values())
        self._sessions.clear()
        logger.info(f"ConversationMemory cleared: {count} entries")
        return count
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete an entire conversation session"""
        if session_id in self._sessions:
            count = len(self._sessions[session_id])
            del self._sessions[session_id]
            logger.info(f"ConversationMemory session deleted: {session_id} ({count} turns)")
            return True
        return False


class AgentMemory(MemoryLayer):
    """
    Agent Memory - Agent-specific knowledge and experiences
    
    Each agent has its own private memory for learning from experiences.
    """
    
    def __init__(self):
        self._agent_memories: Dict[str, Dict[str, MemoryEntry]] = {}
        logger.info("AgentMemory initialized")
    
    async def store_for_agent(
        self,
        agent_id: str,
        content: Any,
        category: str = "general",
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store a memory for a specific agent"""
        entry = MemoryEntry(
            content=content,
            metadata={**metadata, "category": category} if metadata else {"category": category},
            tags=["agent", agent_id, category],
        )
        
        if agent_id not in self._agent_memories:
            self._agent_memories[agent_id] = {}
        
        self._agent_memories[agent_id][entry.id] = entry
        return entry.id
    
    async def get_agent_memories(
        self,
        agent_id: str,
        category: Optional[str] = None,
    ) -> List[MemoryEntry]:
        """Get all memories for an agent, optionally filtered by category"""
        agent_data = self._agent_memories.get(agent_id, {})
        memories = list(agent_data.values())
        
        if category:
            memories = [m for m in memories if m.metadata.get("category") == category]
        
        return memories
    
    async def store(self, entry: MemoryEntry) -> str:
        return entry.id
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        for agent_data in self._agent_memories.values():
            if entry_id in agent_data:
                return agent_data[entry_id]
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()
        
        for agent_data in self._agent_memories.values():
            for entry in agent_data.values():
                content_str = str(entry.content).lower() if entry.content else ""
                if query_lower in content_str:
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        
        return results
    
    async def delete(self, entry_id: str) -> bool:
        for agent_data in self._agent_memories.values():
            if entry_id in agent_data:
                del agent_data[entry_id]
                return True
        return False
    
    async def clear(self) -> int:
        count = sum(len(d) for d in self._agent_memories.values())
        self._agent_memories.clear()
        logger.info(f"AgentMemory cleared: {count} entries")
        return count
    
    async def clear_agent(self, agent_id: str) -> int:
        """Clear all memories for a specific agent"""
        if agent_id in self._agent_memories:
            count = len(self._agent_memories[agent_id])
            del self._agent_memories[agent_id]
            logger.info(f"AgentMemory cleared for agent {agent_id}: {count} entries")
            return count
        return 0


class UserMemory(MemoryLayer):
    """
    User Memory - User preferences, habits, and profile
    
    Stores long-term information about the user.
    """
    
    def __init__(self):
        self._user_memories: Dict[str, Dict[str, MemoryEntry]] = {}
        logger.info("UserMemory initialized")
    
    async def store_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        category: str = "general",
    ) -> str:
        """Store a user preference"""
        entry = MemoryEntry(
            content=value,
            metadata={"key": key, "category": category},
            tags=["user", user_id, "preference", category, key],
        )
        
        if user_id not in self._user_memories:
            self._user_memories[user_id] = {}
        
        # Override existing preference with same key
        for existing_id, existing in list(self._user_memories[user_id].items()):
            if existing.metadata.get("key") == key:
                del self._user_memories[user_id][existing_id]
        
        self._user_memories[user_id][entry.id] = entry
        return entry.id
    
    async def get_preferences(
        self,
        user_id: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all preferences for a user"""
        user_data = self._user_memories.get(user_id, {})
        preferences = {}
        
        for entry in user_data.values():
            if category and entry.metadata.get("category") != category:
                continue
            key = entry.metadata.get("key")
            if key:
                preferences[key] = entry.content
        
        return preferences
    
    async def store(self, entry: MemoryEntry) -> str:
        return entry.id
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        for user_data in self._user_memories.values():
            if entry_id in user_data:
                return user_data[entry_id]
        return None
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()
        
        for user_data in self._user_memories.values():
            for entry in user_data.values():
                content_str = str(entry.content).lower() if entry.content else ""
                if query_lower in content_str:
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        
        return results
    
    async def delete(self, entry_id: str) -> bool:
        for user_data in self._user_memories.values():
            if entry_id in user_data:
                del user_data[entry_id]
                return True
        return False
    
    async def clear(self) -> int:
        count = sum(len(d) for d in self._user_memories.values())
        self._user_memories.clear()
        logger.info(f"UserMemory cleared: {count} entries")
        return count


class KnowledgeMemory(MemoryLayer):
    """
    Knowledge Memory - Long-term factual knowledge base
    
    Shared knowledge accessible by all agents.
    Designed for facts, documentation, and reference material.
    """
    
    def __init__(self):
        self._knowledge: Dict[str, MemoryEntry] = {}
        self._indexes: Dict[str, List[str]] = {}  # Simple tag index
        logger.info("KnowledgeMemory initialized")
    
    async def store_knowledge(
        self,
        title: str,
        content: Any,
        category: str = "general",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store a piece of knowledge"""
        entry_tags = ["knowledge", category] + (tags or [])
        entry = MemoryEntry(
            content=content,
            metadata={
                **(metadata or {}),
                "title": title,
                "category": category,
            },
            tags=entry_tags,
        )
        
        self._knowledge[entry.id] = entry
        
        # Update indexes
        for tag in entry_tags:
            if tag not in self._indexes:
                self._indexes[tag] = []
            self._indexes[tag].append(entry.id)
        
        return entry.id
    
    async def search_by_category(self, category: str, limit: int = 20) -> List[MemoryEntry]:
        """Search knowledge by category"""
        results = []
        for entry in self._knowledge.values():
            if entry.metadata.get("category") == category:
                results.append(entry)
                if len(results) >= limit:
                    break
        return results
    
    async def search_by_tag(self, tag: str, limit: int = 20) -> List[MemoryEntry]:
        """Search knowledge by tag using index"""
        entry_ids = self._indexes.get(tag, [])
        results = []
        
        for entry_id in entry_ids[:limit]:
            entry = self._knowledge.get(entry_id)
            if entry:
                results.append(entry)
        
        return results
    
    async def store(self, entry: MemoryEntry) -> str:
        self._knowledge[entry.id] = entry
        for tag in entry.tags:
            if tag not in self._indexes:
                self._indexes[tag] = []
            self._indexes[tag].append(entry.id)
        return entry.id
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        return self._knowledge.get(entry_id)
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()
        
        for entry in self._knowledge.values():
            content_str = str(entry.content).lower() if entry.content else ""
            title = entry.metadata.get("title", "").lower()
            tags_str = " ".join(entry.tags).lower()
            
            if query_lower in content_str or query_lower in title or query_lower in tags_str:
                results.append(entry)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def delete(self, entry_id: str) -> bool:
        if entry_id not in self._knowledge:
            return False
        
        entry = self._knowledge[entry_id]
        
        # Remove from indexes
        for tag in entry.tags:
            if tag in self._indexes and entry_id in self._indexes[tag]:
                self._indexes[tag].remove(entry_id)
        
        del self._knowledge[entry_id]
        return True
    
    async def clear(self) -> int:
        count = len(self._knowledge)
        self._knowledge.clear()
        self._indexes.clear()
        logger.info(f"KnowledgeMemory cleared: {count} entries")
        return count


class MemorySystem:
    """
    Unified Memory System
    
    Provides access to all 5 memory layers with a unified interface.
    """
    
    _instance: Optional["MemorySystem"] = None
    
    def __new__(cls) -> "MemorySystem":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "MemorySystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Initialize all memory layers
        self.working = WorkingMemory()
        self.conversation = ConversationMemory()
        self.agent = AgentMemory()
        self.user = UserMemory()
        self.knowledge = KnowledgeMemory()
        
        self._initialized = True
        logger.info("MemorySystem initialized with 5 layers")
    
    def get_layer(self, layer_name: str) -> MemoryLayer:
        """Get a specific memory layer by name"""
        layers = {
            "working": self.working,
            "conversation": self.conversation,
            "agent": self.agent,
            "user": self.user,
            "knowledge": self.knowledge,
        }
        return layers.get(layer_name.lower())
    
    async def search_all(self, query: str, limit_per_layer: int = 5) -> Dict[str, List[MemoryEntry]]:
        """Search across all memory layers"""
        results = {}
        
        layers = [
            ("working", self.working),
            ("conversation", self.conversation),
            ("agent", self.agent),
            ("user", self.user),
            ("knowledge", self.knowledge),
        ]
        
        for name, layer in layers:
            results[name] = await layer.search(query, limit_per_layer)
        
        return results
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory layers"""
        return {
            "working": len(await self.working.get_all()),
            "conversation": sum(len(s) for s in self.conversation._sessions.values()),
            "agent": sum(len(d) for d in self.agent._agent_memories.values()),
            "user": sum(len(d) for d in self.user._user_memories.values()),
            "knowledge": len(self.knowledge._knowledge),
        }


# Global instance
memory_system = MemorySystem()


def get_memory_system() -> MemorySystem:
    """Dependency for FastAPI to get memory system"""
    return memory_system
