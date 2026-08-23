"""
JARVIS AI - Agent Registry

Manages agent lifecycle, hierarchy, and graph operations.
Uses NetworkX for efficient graph manipulation.
"""

import networkx as nx
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.config.models import Agent, AgentSkill, AgentTool
from backend.events.event_bus import event_bus, EventType, Event

logger = logging.getLogger(__name__)


class AgentNode:
    """Represents an agent node in the graph"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.id = agent.id
        self.name = agent.name
        self.parent_id = agent.parent_id
        self.children: List[str] = []
        self.skills: List[str] = []
        self.tools: List[str] = []
        self.is_active = agent.is_active
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.agent.description,
            "parent_id": self.parent_id,
            "children": self.children,
            "skills": self.skills,
            "tools": self.tools,
            "capabilities": self.agent.capabilities,
            "permissions": self.agent.permissions,
            "model": self.agent.model,
            "provider": self.agent.provider,
            "is_active": self.is_active,
        }


class AgentRegistry:
    """
    Central registry for all agents in the system.
    Maintains agent hierarchy as a directed graph.
    """
    
    _instance: Optional["AgentRegistry"] = None
    
    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """Get singleton instance of AgentRegistry"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Graph to store agent relationships
        self.graph: nx.DiGraph = nx.DiGraph()
        
        # In-memory cache of agents
        self._agents: Dict[str, AgentNode] = {}
        
        # Hierarchy limits
        self.max_depth = 10
        self.max_agents = 50
        
        self._initialized = True
        logger.info("AgentRegistry initialized")
    
    async def load_from_db(self, db: AsyncSession):
        """Load all agents from database into registry"""
        try:
            result = await db.execute(select(Agent))
            agents = result.scalars().all()
            
            for agent in agents:
                node = AgentNode(agent)
                self._agents[agent.id] = node
                
                # Load skills and tools
                skills_result = await db.execute(
                    select(AgentSkill).where(AgentSkill.agent_id == agent.id)
                )
                node.skills = [sk.skill_id for sk in skills_result.scalars().all()]
                
                tools_result = await db.execute(
                    select(AgentTool).where(AgentTool.agent_id == agent.id)
                )
                node.tools = [tl.tool_id for tl in tools_result.scalars().all()]
                
                # Add to graph
                self.graph.add_node(agent.id, data=node)
                
                # Add edge if has parent
                if agent.parent_id:
                    self.graph.add_edge(agent.parent_id, agent.id)
            
            # Update children lists
            self._update_children_lists()
            
            logger.info(f"Loaded {len(agents)} agents from database")
            
        except Exception as e:
            logger.error(f"Failed to load agents from database: {e}")
            raise
    
    def _update_children_lists(self):
        """Update children lists for all nodes"""
        for node_id, node in self._agents.items():
            node.children = list(self.graph.successors(node_id))
    
    async def add_agent(
        self,
        db: AsyncSession,
        agent: Agent,
        parent_id: Optional[str] = None,
    ) -> AgentNode:
        """
        Add a new agent to the registry.
        Validates hierarchy constraints before adding.
        """
        # Check total agents limit
        if len(self._agents) >= self.max_agents:
            raise ValueError(f"Maximum number of agents ({self.max_agents}) reached")
        
        # Validate parent exists if specified
        if parent_id:
            if parent_id not in self._agents:
                raise ValueError(f"Parent agent {parent_id} not found")
            
            # Check depth
            depth = self._get_depth(parent_id)
            if depth + 1 > self.max_depth:
                raise ValueError(
                    f"Adding this agent would exceed maximum depth ({self.max_depth})"
                )
            
            # Check for circular dependency
            if self._would_create_cycle(parent_id, agent.id):
                raise ValueError("Cannot create circular agent dependency")
            
            agent.parent_id = parent_id
        
        # Create node
        node = AgentNode(agent)
        self._agents[agent.id] = node
        
        # Add to graph
        self.graph.add_node(agent.id, data=node)
        
        if parent_id:
            self.graph.add_edge(parent_id, agent.id)
            self._update_children_lists()
        
        # Emit event
        await event_bus.emit(
            EventType.AGENT_CREATED,
            data={"agent_id": agent.id, "name": agent.name},
            agent_id=agent.id,
        )
        
        logger.info(f"Added agent: {agent.name} ({agent.id})")
        return node
    
    async def remove_agent(self, db: AsyncSession, agent_id: str):
        """Remove an agent and all its descendants"""
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Get all descendants
        descendants = list(nx.descendants(self.graph, agent_id))
        
        # Remove from graph
        self.graph.remove_node(agent_id)
        
        # Remove from cache
        del self._agents[agent_id]
        for desc_id in descendants:
            if desc_id in self._agents:
                del self._agents[desc_id]
        
        # Update children lists
        self._update_children_lists()
        
        # Emit event
        await event_bus.emit(
            EventType.AGENT_DEACTIVATED,
            data={"agent_id": agent_id, "removed_descendants": descendants},
            agent_id=agent_id,
        )
        
        logger.info(f"Removed agent {agent_id} and {len(descendants)} descendants")
    
    def get_agent(self, agent_id: str) -> Optional[AgentNode]:
        """Get an agent by ID"""
        return self._agents.get(agent_id)
    
    def get_all_agents(self) -> List[AgentNode]:
        """Get all registered agents"""
        return list(self._agents.values())
    
    def get_children(self, agent_id: str) -> List[AgentNode]:
        """Get direct children of an agent"""
        if agent_id not in self._agents:
            return []
        
        children_ids = list(self.graph.successors(agent_id))
        return [self._agents[cid] for cid in children_ids if cid in self._agents]
    
    def get_parent(self, agent_id: str) -> Optional[AgentNode]:
        """Get parent of an agent"""
        if agent_id not in self._agents:
            return None
        
        parent_id = self._agents[agent_id].parent_id
        if parent_id:
            return self._agents.get(parent_id)
        return None
    
    def get_ancestors(self, agent_id: str) -> List[AgentNode]:
        """Get all ancestors of an agent (parent, grandparent, etc.)"""
        if agent_id not in self._agents:
            return []
        
        ancestors_ids = list(nx.ancestors(self.graph, agent_id))
        return [self._agents[a] for a in ancestors_ids if a in self._agents]
    
    def get_descendants(self, agent_id: str) -> List[AgentNode]:
        """Get all descendants of an agent"""
        if agent_id not in self._agents:
            return []
        
        descendants_ids = list(nx.descendants(self.graph, agent_id))
        return [self._agents[d] for d in descendants_ids if d in self._agents]
    
    def get_subtree(self, agent_id: str) -> nx.DiGraph:
        """Get the subtree rooted at an agent"""
        if agent_id not in self._agents:
            return nx.DiGraph()
        
        # Get all nodes in subtree
        subtree_nodes = {agent_id} | set(nx.descendants(self.graph, agent_id))
        return self.graph.subgraph(subtree_nodes)
    
    def _get_depth(self, agent_id: str) -> int:
        """Get depth of an agent in the hierarchy"""
        if agent_id not in self._agents:
            return 0
        
        ancestors = list(nx.ancestors(self.graph, agent_id))
        return len(ancestors)
    
    def _would_create_cycle(self, parent_id: str, child_id: str) -> bool:
        """Check if adding an edge would create a cycle"""
        # If child is already an ancestor of parent, it would create a cycle
        ancestors = set(nx.ancestors(self.graph, parent_id))
        ancestors.add(parent_id)
        return child_id in ancestors
    
    def get_root_agents(self) -> List[AgentNode]:
        """Get all root agents (no parent)"""
        roots = [node for node in self._agents.values() if node.parent_id is None]
        return roots
    
    def get_hierarchy_tree(self) -> Dict[str, Any]:
        """Get complete hierarchy as a tree structure"""
        roots = self.get_root_agents()
        
        def build_tree(node: AgentNode) -> Dict[str, Any]:
            tree = node.to_dict()
            children = self.get_children(node.id)
            tree["children"] = [build_tree(child) for child in children]
            return tree
        
        return {
            "roots": [build_tree(root) for root in roots],
            "total_agents": len(self._agents),
        }
    
    def validate_delegation(
        self,
        from_agent_id: str,
        to_agent_id: str,
    ) -> Tuple[bool, str]:
        """
        Validate if delegation from one agent to another is allowed.
        Returns (is_valid, error_message)
        """
        if from_agent_id not in self._agents:
            return False, f"Source agent {from_agent_id} not found"
        
        if to_agent_id not in self._agents:
            return False, f"Target agent {to_agent_id} not found"
        
        source = self._agents[from_agent_id]
        target = self._agents[to_agent_id]
        
        # Check if source can delegate
        if not source.agent.can_delegate:
            return False, f"Agent {source.name} cannot delegate tasks"
        
        # Check depth
        depth = self._get_depth(to_agent_id)
        if depth >= self.max_depth:
            return False, f"Maximum delegation depth ({self.max_depth}) reached"
        
        # Check for circular delegation
        if self._would_create_cycle(from_agent_id, to_agent_id):
            return False, "Circular delegation detected"
        
        return True, ""
    
    def find_agents_by_capability(
        self,
        capability: str,
    ) -> List[AgentNode]:
        """Find all agents with a specific capability"""
        matching = []
        for node in self._agents.values():
            if capability in node.agent.capabilities:
                matching.append(node)
        return matching
    
    def find_agents_by_skill(
        self,
        skill_id: str,
    ) -> List[AgentNode]:
        """Find all agents with a specific skill"""
        matching = []
        for node in self._agents.values():
            if skill_id in node.skills:
                matching.append(node)
        return matching


# Global registry instance
agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Dependency for FastAPI to get agent registry"""
    return agent_registry
