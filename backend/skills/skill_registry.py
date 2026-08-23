"""
JARVIS AI - Skill Registry

Manages skill lifecycle, discovery, and validation.
Skills are modular competencies that can be assigned to agents.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import logging
from uuid import uuid4
import importlib
import os
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config.models import Skill, AgentSkill
from backend.events.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)


class SkillDefinition:
    """Represents a skill definition"""
    
    def __init__(
        self,
        id: str,
        name: str,
        version: str,
        description: str,
        instructions: str,
        required_tools: List[str],
        required_permissions: List[str],
        compatible_modalities: List[str],
        dependencies: List[str],
        metadata: Dict[str, Any],
        enabled: bool = True,
        author: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.version = version
        self.description = description
        self.instructions = instructions
        self.required_tools = required_tools
        self.required_permissions = required_permissions
        self.compatible_modalities = compatible_modalities
        self.dependencies = dependencies
        self.metadata = metadata
        self.enabled = enabled
        self.author = author
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "instructions": self.instructions,
            "required_tools": self.required_tools,
            "required_permissions": self.required_permissions,
            "compatible_modalities": self.compatible_modalities,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "enabled": self.enabled,
            "author": self.author,
        }
    
    @classmethod
    def from_model(cls, model: Skill) -> "SkillDefinition":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            name=model.name,
            version=model.version,
            description=model.description or "",
            instructions=model.instructions or "",
            required_tools=model.required_tools or [],
            required_permissions=model.required_permissions or [],
            compatible_modalities=model.compatible_modalities or [],
            dependencies=model.dependencies or [],
            metadata=model.skill_metadata or {},
            enabled=model.is_enabled,
            author=model.author,
        )


class SkillRegistry:
    """
    Central registry for all skills in the system.
    Supports dynamic loading of skills from directories.
    """
    
    _instance: Optional["SkillRegistry"] = None
    
    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """Get singleton instance of SkillRegistry"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # In-memory cache of skills
        self._skills: Dict[str, SkillDefinition] = {}
        
        # Skills directory path
        self.skills_dir = "./backend/skills"
        
        # Ensure skills directory exists
        os.makedirs(self.skills_dir, exist_ok=True)
        
        self._initialized = True
        logger.info("SkillRegistry initialized")
    
    async def load_from_db(self, db: AsyncSession):
        """Load all skills from database into registry"""
        try:
            result = await db.execute(select(Skill))
            skills = result.scalars().all()
            
            for skill in skills:
                definition = SkillDefinition.from_model(skill)
                self._skills[skill.id] = definition
            
            logger.info(f"Loaded {len(skills)} skills from database")
            
        except Exception as e:
            logger.error(f"Failed to load skills from database: {e}")
            raise
    
    async def register_skill(
        self,
        db: AsyncSession,
        skill: SkillDefinition,
    ) -> SkillDefinition:
        """Register a new skill in the system"""
        # Check if skill already exists
        existing = await db.execute(
            select(Skill).where(Skill.name == skill.name)
        )
        existing_skill = existing.scalar_one_or_none()
        
        if existing_skill:
            raise ValueError(f"Skill with name '{skill.name}' already exists")
        
        # Validate dependencies exist
        for dep_id in skill.dependencies:
            if dep_id not in self._skills:
                # Try to find in DB
                dep_result = await db.execute(
                    select(Skill).where(Skill.id == dep_id)
                )
                if not dep_result.scalar_one_or_none():
                    raise ValueError(
                        f"Dependency skill {dep_id} not found"
                    )
        
        # Create database record
        db_skill = Skill(
            id=skill.id,
            name=skill.name,
            version=skill.version,
            description=skill.description,
            instructions=skill.instructions,
            required_tools=skill.required_tools,
            required_permissions=skill.required_permissions,
            compatible_modalities=skill.compatible_modalities,
            dependencies=skill.dependencies,
            skill_metadata=skill.metadata,
            is_enabled=skill.enabled,
            author=skill.author,
        )
        
        db.add(db_skill)
        await db.commit()
        await db.refresh(db_skill)
        
        # Add to registry
        self._skills[db_skill.id] = SkillDefinition.from_model(db_skill)
        
        # Emit event
        await event_bus.emit(
            EventType.SKILL_ACTIVATED,
            data={"skill_id": db_skill.id, "name": db_skill.name},
        )
        
        logger.info(f"Registered skill: {skill.name} ({skill.id})")
        return skill
    
    async def unregister_skill(self, db: AsyncSession, skill_id: str):
        """Remove a skill from the system"""
        if skill_id not in self._skills:
            raise ValueError(f"Skill {skill_id} not found")
        
        # Check if any agents are using this skill
        result = await db.execute(
            select(AgentSkill).where(AgentSkill.skill_id == skill_id)
        )
        usages = result.scalars().all()
        
        if usages:
            raise ValueError(
                f"Cannot remove skill: {len(usages)} agents are using it"
            )
        
        # Remove from database
        skill = await db.get(Skill, skill_id)
        if skill:
            await db.delete(skill)
            await db.commit()
        
        # Remove from registry
        del self._skills[skill_id]
        
        logger.info(f"Unregistered skill: {skill_id}")
    
    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill by ID"""
        return self._skills.get(skill_id)
    
    def get_skill_by_name(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by name"""
        for skill in self._skills.values():
            if skill.name == name:
                return skill
        return None
    
    def get_all_skills(self) -> List[SkillDefinition]:
        """Get all registered skills"""
        return list(self._skills.values())
    
    def get_enabled_skills(self) -> List[SkillDefinition]:
        """Get all enabled skills"""
        return [s for s in self._skills.values() if s.enabled]
    
    def validate_agent_compatibility(
        self,
        skill_id: str,
        agent_capabilities: List[str],
        agent_permissions: List[str],
        agent_tools: List[str],
    ) -> tuple[bool, str]:
        """
        Validate if an agent can use a specific skill.
        Returns (is_compatible, error_message)
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return False, f"Skill {skill_id} not found"
        
        if not skill.enabled:
            return False, f"Skill {skill.name} is disabled"
        
        # Check modalities
        if skill.compatible_modalities:
            missing_modalities = set(skill.compatible_modalities) - set(agent_capabilities)
            if missing_modalities:
                return False, f"Agent lacks required modalities: {missing_modalities}"
        
        # Check permissions
        if skill.required_permissions:
            missing_permissions = set(skill.required_permissions) - set(agent_permissions)
            if missing_permissions:
                return False, f"Agent lacks required permissions: {missing_permissions}"
        
        # Check tools
        if skill.required_tools:
            missing_tools = set(skill.required_tools) - set(agent_tools)
            if missing_tools:
                return False, f"Agent lacks required tools: {missing_tools}"
        
        return True, ""
    
    def get_skill_dependencies(self, skill_id: str) -> List[SkillDefinition]:
        """Get all dependencies for a skill (recursive)"""
        skill = self.get_skill(skill_id)
        if not skill:
            return []
        
        deps = []
        visited = set()
        
        def collect_deps(sid: str):
            if sid in visited:
                return
            visited.add(sid)
            
            s = self.get_skill(sid)
            if s:
                deps.append(s)
                for dep_id in s.dependencies:
                    collect_deps(dep_id)
        
        for dep_id in skill.dependencies:
            collect_deps(dep_id)
        
        return deps
    
    def discover_skills_from_directory(self) -> List[SkillDefinition]:
        """Discover and load skills from the skills directory"""
        discovered = []
        
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return discovered
        
        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.skills_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    skill_def = SkillDefinition(
                        id=data.get("id", str(uuid4())),
                        name=data["name"],
                        version=data.get("version", "1.0.0"),
                        description=data.get("description", ""),
                        instructions=data.get("instructions", ""),
                        required_tools=data.get("required_tools", []),
                        required_permissions=data.get("required_permissions", []),
                        compatible_modalities=data.get("compatible_modalities", []),
                        dependencies=data.get("dependencies", []),
                        metadata=data.get("metadata", {}),
                        enabled=data.get("enabled", True),
                        author=data.get("author"),
                    )
                    
                    discovered.append(skill_def)
                    logger.info(f"Discovered skill: {skill_def.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load skill from {filename}: {e}")
        
        return discovered


# Global registry instance
skill_registry = SkillRegistry()


def get_skill_registry() -> SkillRegistry:
    """Dependency for FastAPI to get skill registry"""
    return skill_registry
