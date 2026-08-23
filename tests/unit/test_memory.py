"""
Tests for Memory System

Validates all 5 memory layers:
- Working Memory
- Conversation Memory
- Agent Memory
- User Memory
- Knowledge Memory
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from backend.memory.memory_system import (
    MemorySystem,
    WorkingMemory,
    ConversationMemory,
    AgentMemory,
    UserMemory,
    KnowledgeMemory,
    MemoryEntry,
)


class TestMemoryEntry:
    """Test MemoryEntry dataclass"""
    
    def test_entry_creation(self):
        """Test basic entry creation"""
        entry = MemoryEntry(content="test content")
        assert entry.content == "test content"
        assert entry.id is not None
        assert entry.created_at is not None
        assert entry.expires_at is None
        assert entry.metadata == {}
        assert entry.tags == []
    
    def test_entry_with_metadata(self):
        """Test entry with metadata and tags"""
        entry = MemoryEntry(
            content={"key": "value"},
            metadata={"category": "test"},
            tags=["tag1", "tag2"],
        )
        assert entry.content == {"key": "value"}
        assert entry.metadata["category"] == "test"
        assert entry.tags == ["tag1", "tag2"]
    
    def test_entry_expiration(self):
        """Test entry expiration check"""
        # Non-expiring entry
        entry1 = MemoryEntry(content="test")
        assert not entry1.is_expired()
        
        # Expired entry
        past = datetime.utcnow() - timedelta(hours=1)
        entry2 = MemoryEntry(content="test", expires_at=past)
        assert entry2.is_expired()
        
        # Future entry
        future = datetime.utcnow() + timedelta(hours=1)
        entry3 = MemoryEntry(content="test", expires_at=future)
        assert not entry3.is_expired()
    
    def test_entry_to_dict(self):
        """Test entry serialization"""
        entry = MemoryEntry(
            content="test",
            metadata={"key": "value"},
            tags=["tag1"],
        )
        d = entry.to_dict()
        assert d["content"] == "test"
        assert d["metadata"]["key"] == "value"
        assert d["tags"] == ["tag1"]
        assert "id" in d
        assert "created_at" in d


class TestWorkingMemory:
    """Test Working Memory layer"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """Test storing and retrieving memories"""
        wm = WorkingMemory()
        entry = MemoryEntry(content="test content")
        
        entry_id = await wm.store(entry)
        retrieved = await wm.retrieve(entry_id)
        
        assert retrieved is not None
        assert retrieved.content == "test content"
        assert retrieved.id == entry_id
    
    @pytest.mark.asyncio
    async def test_search(self):
        """Test searching memories"""
        wm = WorkingMemory()
        
        await wm.store(MemoryEntry(content="python programming", tags=["coding"]))
        await wm.store(MemoryEntry(content="javascript development", tags=["coding"]))
        await wm.store(MemoryEntry(content="data science", tags=["analytics"]))
        
        results = await wm.search("python", limit=10)
        assert len(results) == 1
        assert "python" in results[0].content.lower()
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting memories"""
        wm = WorkingMemory()
        entry = MemoryEntry(content="to delete")
        
        entry_id = await wm.store(entry)
        assert await wm.retrieve(entry_id) is not None
        
        success = await wm.delete(entry_id)
        assert success is True
        assert await wm.retrieve(entry_id) is None
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all memories"""
        wm = WorkingMemory()
        
        await wm.store(MemoryEntry(content="1"))
        await wm.store(MemoryEntry(content="2"))
        await wm.store(MemoryEntry(content="3"))
        
        count = await wm.clear()
        assert count == 3
        assert len(await wm.get_all()) == 0
    
    @pytest.mark.asyncio
    async def test_max_entries_eviction(self):
        """Test LRU eviction when max entries reached"""
        wm = WorkingMemory(max_entries=3)
        
        await wm.store(MemoryEntry(content="first"))
        await asyncio.sleep(0.01)
        await wm.store(MemoryEntry(content="second"))
        await asyncio.sleep(0.01)
        await wm.store(MemoryEntry(content="third"))
        await asyncio.sleep(0.01)
        await wm.store(MemoryEntry(content="fourth"))
        
        # Should have only 3 entries
        all_memories = await wm.get_all()
        assert len(all_memories) == 3
        
        # First should be evicted (oldest)
        contents = [m.content for m in all_memories]
        assert "first" not in contents


class TestConversationMemory:
    """Test Conversation Memory layer"""
    
    @pytest.mark.asyncio
    async def test_add_turn(self):
        """Test adding conversation turns"""
        cm = ConversationMemory()
        session_id = "test-session"
        
        entry_id = await cm.add_turn(session_id, "user", "Hello")
        assert entry_id is not None
        
        session = await cm.get_session(session_id)
        assert len(session) == 1
        assert session[0].content["role"] == "user"
        assert session[0].content["content"] == "Hello"
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """Test multi-turn conversation"""
        cm = ConversationMemory()
        session_id = "multi-turn"
        
        await cm.add_turn(session_id, "user", "What is AI?")
        await cm.add_turn(session_id, "assistant", "AI stands for Artificial Intelligence")
        await cm.add_turn(session_id, "user", "Thanks!")
        
        session = await cm.get_session(session_id)
        assert len(session) == 3
        assert session[0].content["role"] == "user"
        assert session[1].content["role"] == "assistant"
        assert session[2].content["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_max_turns_enforcement(self):
        """Test max turns per session"""
        cm = ConversationMemory(max_turns_per_session=5)
        session_id = "limited"
        
        for i in range(10):
            await cm.add_turn(session_id, "user", f"Message {i}")
        
        session = await cm.get_session(session_id)
        assert len(session) == 5
        # Should have the last 5 messages
        assert "Message 9" in session[-1].content["content"]
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting entire session"""
        cm = ConversationMemory()
        session_id = "to-delete"
        
        await cm.add_turn(session_id, "user", "Hello")
        await cm.add_turn(session_id, "assistant", "Hi")
        
        success = await cm.delete_session(session_id)
        assert success is True
        
        session = await cm.get_session(session_id)
        assert len(session) == 0
    
    @pytest.mark.asyncio
    async def test_search_conversations(self):
        """Test searching conversations"""
        cm = ConversationMemory()
        session_id = "search-test"
        
        await cm.add_turn(session_id, "user", "How to use Python?")
        await cm.add_turn(session_id, "assistant", "Python is great for scripting")
        
        results = await cm.search("Python", limit=10)
        assert len(results) >= 1


class TestAgentMemory:
    """Test Agent Memory layer"""
    
    @pytest.mark.asyncio
    async def test_store_for_agent(self):
        """Test storing memories for specific agent"""
        am = AgentMemory()
        agent_id = "agent-123"
        
        entry_id = await am.store_for_agent(
            agent_id,
            content="learned skill",
            category="skills",
        )
        
        memories = await am.get_agent_memories(agent_id)
        assert len(memories) == 1
        assert memories[0].content == "learned skill"
    
    @pytest.mark.asyncio
    async def test_category_filtering(self):
        """Test filtering by category"""
        am = AgentMemory()
        agent_id = "agent-456"
        
        await am.store_for_agent(agent_id, "coding tip", category="tips")
        await am.store_for_agent(agent_id, "debugging trick", category="tips")
        await am.store_for_agent(agent_id, "project info", category="projects")
        
        tips = await am.get_agent_memories(agent_id, category="tips")
        assert len(tips) == 2
        
        projects = await am.get_agent_memories(agent_id, category="projects")
        assert len(projects) == 1
    
    @pytest.mark.asyncio
    async def test_clear_agent(self):
        """Test clearing agent memories"""
        am = AgentMemory()
        agent_id = "agent-clear"
        
        await am.store_for_agent(agent_id, "memory 1")
        await am.store_for_agent(agent_id, "memory 2")
        
        count = await am.clear_agent(agent_id)
        assert count == 2
        
        memories = await am.get_agent_memories(agent_id)
        assert len(memories) == 0


class TestUserMemory:
    """Test User Memory layer"""
    
    @pytest.mark.asyncio
    async def test_store_preference(self):
        """Test storing user preferences"""
        um = UserMemory()
        user_id = "user-123"
        
        await um.store_preference(user_id, "theme", "dark", category="ui")
        await um.store_preference(user_id, "language", "en", category="ui")
        
        prefs = await um.get_preferences(user_id)
        assert prefs["theme"] == "dark"
        assert prefs["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_preference_override(self):
        """Test overriding existing preference"""
        um = UserMemory()
        user_id = "user-456"
        
        await um.store_preference(user_id, "theme", "light")
        await um.store_preference(user_id, "theme", "dark")
        
        prefs = await um.get_preferences(user_id)
        assert prefs["theme"] == "dark"
        # Should only have one entry
        assert len(prefs) == 1
    
    @pytest.mark.asyncio
    async def test_category_filtering(self):
        """Test filtering preferences by category"""
        um = UserMemory()
        user_id = "user-789"
        
        await um.store_preference(user_id, "theme", "dark", category="ui")
        await um.store_preference(user_id, "notifications", True, category="settings")
        
        ui_prefs = await um.get_preferences(user_id, category="ui")
        assert "theme" in ui_prefs
        assert "notifications" not in ui_prefs


class TestKnowledgeMemory:
    """Test Knowledge Memory layer"""
    
    @pytest.mark.asyncio
    async def test_store_knowledge(self):
        """Test storing knowledge entries"""
        km = KnowledgeMemory()
        
        entry_id = await km.store_knowledge(
            title="Python Basics",
            content="Python is a programming language",
            category="programming",
            tags=["python", "basics"],
        )
        
        retrieved = await km.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.metadata["title"] == "Python Basics"
    
    @pytest.mark.asyncio
    async def test_search_by_category(self):
        """Test searching by category"""
        km = KnowledgeMemory()
        
        await km.store_knowledge("Python Guide", "...", category="programming")
        await km.store_knowledge("React Guide", "...", category="programming")
        await km.store_knowledge("Marketing Tips", "...", category="business")
        
        prog知识 = await km.search_by_category("programming", limit=10)
        assert len(prog知识) == 2
    
    @pytest.mark.asyncio
    async def test_search_by_tag(self):
        """Test searching by tag"""
        km = KnowledgeMemory()
        
        await km.store_knowledge("Guide 1", "...", tags=["python", "beginner"])
        await km.store_knowledge("Guide 2", "...", tags=["python", "advanced"])
        await km.store_knowledge("Guide 3", "...", tags=["javascript"])
        
        python_guides = await km.search_by_tag("python", limit=10)
        assert len(python_guides) == 2
    
    @pytest.mark.asyncio
    async def test_search_content(self):
        """Test searching knowledge content"""
        km = KnowledgeMemory()
        
        await km.store_knowledge("Article 1", "machine learning algorithms", tags=["ai"])
        await km.store_knowledge("Article 2", "deep learning neural networks", tags=["ai"])
        await km.store_knowledge("Article 3", "web development", tags=["web"])
        
        results = await km.search("learning", limit=10)
        assert len(results) == 2


class TestMemorySystem:
    """Test unified Memory System"""
    
    def test_singleton_pattern(self):
        """Test memory system singleton"""
        ms1 = MemorySystem.get_instance()
        ms2 = MemorySystem.get_instance()
        assert ms1 is ms2
    
    def test_get_layer(self):
        """Test getting specific layers"""
        ms = MemorySystem.get_instance()
        
        working = ms.get_layer("working")
        assert isinstance(working, WorkingMemory)
        
        conversation = ms.get_layer("conversation")
        assert isinstance(conversation, ConversationMemory)
        
        agent = ms.get_layer("agent")
        assert isinstance(agent, AgentMemory)
        
        user = ms.get_layer("user")
        assert isinstance(user, UserMemory)
        
        knowledge = ms.get_layer("knowledge")
        assert isinstance(knowledge, KnowledgeMemory)
    
    @pytest.mark.asyncio
    async def test_stats(self):
        """Test getting memory statistics"""
        ms = MemorySystem.get_instance()
        
        # Add some data
        await ms.working.store(MemoryEntry(content="test"))
        await ms.conversation.add_turn("session", "user", "hello")
        await ms.agent.store_for_agent("agent1", "memory")
        await ms.user.store_preference("user1", "key", "value")
        await ms.knowledge.store_knowledge("title", "content")
        
        stats = await ms.get_stats()
        assert "working" in stats
        assert "conversation" in stats
        assert "agent" in stats
        assert "user" in stats
        assert "knowledge" in stats
        
        assert stats["working"] >= 1
        assert stats["conversation"] >= 1
        assert stats["agent"] >= 1
        assert stats["user"] >= 1
        assert stats["knowledge"] >= 1
    
    @pytest.mark.asyncio
    async def test_search_all(self):
        """Test searching across all layers"""
        ms = MemorySystem.get_instance()
        
        # Add searchable content
        await ms.working.store(MemoryEntry(content="python test", tags=["search"]))
        await ms.conversation.add_turn("s1", "user", "python question")
        await ms.knowledge.store_knowledge("Python Guide", "python content", tags=["python"])
        
        results = await ms.search_all("python", limit_per_layer=5)
        
        assert "working" in results
        assert "conversation" in results
        assert "knowledge" in results
        
        # At least one layer should have results
        total_results = sum(len(v) for v in results.values())
        assert total_results >= 1
