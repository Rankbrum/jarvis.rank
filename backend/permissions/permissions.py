"""
JARVIS AI - Permission System

Granular permission system for controlling agent capabilities and tool access.
Implements principle of least privilege.
"""

from enum import Enum
from typing import Set, Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """
    Explicit permissions in the system.
    Each permission represents a specific capability.
    """
    
    # File System Permissions
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    
    # Web Access
    WEB_ACCESS = "web_access"
    WEB_SEARCH = "web_search"
    
    # Terminal Permissions
    TERMINAL_READ = "terminal_read"
    TERMINAL_EXECUTE = "terminal_execute"
    
    # GitHub Permissions
    GITHUB_READ = "github_read"
    GITHUB_WRITE = "github_write"
    GITHUB_EXECUTE = "github_execute"
    
    # Email Permissions
    EMAIL_READ = "email_read"
    EMAIL_SEND = "email_send"
    
    # Calendar Permissions
    CALENDAR_READ = "calendar_read"
    CALENDAR_WRITE = "calendar_write"
    
    # Database Permissions
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"
    DATABASE_EXECUTE = "database_execute"
    
    # Code Execution
    CODE_EXECUTE = "code_execute"
    CODE_SANDBOX = "code_sandbox"
    
    # Image/Media Generation
    IMAGE_GENERATE = "image_generate"
    AUDIO_GENERATE = "audio_generate"
    VIDEO_GENERATE = "video_generate"
    
    # External APIs
    API_CALL = "api_call"
    
    # Agent Management
    CREATE_AGENT = "create_agent"
    DELETE_AGENT = "delete_agent"
    MODIFY_AGENT = "modify_agent"
    
    # Skill Management
    INSTALL_SKILL = "install_skill"
    REMOVE_SKILL = "remove_skill"
    
    # Tool Management
    INSTALL_TOOL = "install_tool"
    REMOVE_TOOL = "remove_tool"
    
    # Memory Access
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    MEMORY_DELETE = "memory_delete"
    
    # User Data
    USER_DATA_READ = "user_data_read"
    USER_DATA_WRITE = "user_data_write"
    
    # Admin Permissions
    ADMIN = "admin"
    SYSTEM_CONFIG = "system_config"


# Permission groups for easier management
PERMISSION_GROUPS: Dict[str, Set[Permission]] = {
    "basic": {
        Permission.READ_FILES,
        Permission.WEB_ACCESS,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
    },
    "developer": {
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.GITHUB_READ,
        Permission.CODE_EXECUTE,
        Permission.CODE_SANDBOX,
        Permission.TERMINAL_READ,
        Permission.DATABASE_READ,
    },
    "researcher": {
        Permission.WEB_ACCESS,
        Permission.WEB_SEARCH,
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
    },
    "assistant": {
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.EMAIL_READ,
        Permission.EMAIL_SEND,
        Permission.CALENDAR_READ,
        Permission.CALENDAR_WRITE,
    },
    "admin": {
        Permission.ADMIN,
        Permission.SYSTEM_CONFIG,
        Permission.CREATE_AGENT,
        Permission.DELETE_AGENT,
        Permission.MODIFY_AGENT,
        Permission.INSTALL_SKILL,
        Permission.REMOVE_SKILL,
        Permission.INSTALL_TOOL,
        Permission.REMOVE_TOOL,
    },
}


@dataclass
class PermissionGrant:
    """Represents a granted permission with metadata"""
    permission: Permission
    granted_at: str
    granted_by: str
    scope: Optional[str] = None  # Optional scope limitation
    expires_at: Optional[str] = None  # Optional expiration
    
    def is_valid(self) -> bool:
        """Check if grant is still valid (not expired)"""
        from datetime import datetime
        if not self.expires_at:
            return True
        return datetime.fromisoformat(self.expires_at) > datetime.utcnow()


@dataclass
class PermissionSet:
    """
    A set of permissions assigned to an agent or user.
    Supports hierarchical permission checking.
    """
    permissions: Set[Permission] = field(default_factory=set)
    grants: Dict[Permission, PermissionGrant] = field(default_factory=dict)
    
    def add(self, permission: Permission, grant: Optional[PermissionGrant] = None):
        """Add a permission to the set"""
        self.permissions.add(permission)
        if grant:
            self.grants[permission] = grant
        logger.debug(f"Added permission: {permission.value}")
    
    def remove(self, permission: Permission):
        """Remove a permission from the set"""
        self.permissions.discard(permission)
        self.grants.pop(permission, None)
        logger.debug(f"Removed permission: {permission.value}")
    
    def has(self, permission: Permission) -> bool:
        """Check if permission is granted"""
        if permission not in self.permissions:
            return False
        
        # Check if grant is still valid
        if permission in self.grants:
            if not self.grants[permission].is_valid():
                self.remove(permission)
                return False
        
        return True
    
    def has_all(self, permissions: List[Permission]) -> bool:
        """Check if all permissions are granted"""
        return all(self.has(p) for p in permissions)
    
    def has_any(self, permissions: List[Permission]) -> bool:
        """Check if any of the permissions is granted"""
        return any(self.has(p) for p in permissions)
    
    def add_group(self, group_name: str):
        """Add all permissions from a predefined group"""
        if group_name not in PERMISSION_GROUPS:
            raise ValueError(f"Unknown permission group: {group_name}")
        
        for permission in PERMISSION_GROUPS[group_name]:
            self.add(permission)
        
        logger.info(f"Added permission group: {group_name}")
    
    def to_list(self) -> List[str]:
        """Convert permissions to list of strings"""
        return [p.value for p in self.permissions]
    
    @classmethod
    def from_list(cls, permissions: List[str]) -> "PermissionSet":
        """Create PermissionSet from list of permission strings"""
        perm_set = cls()
        for perm_str in permissions:
            try:
                permission = Permission(perm_str)
                perm_set.add(permission)
            except ValueError:
                logger.warning(f"Unknown permission: {perm_str}")
        return perm_set


class PermissionManager:
    """
    Central manager for permission validation and enforcement.
    """
    
    _instance: Optional["PermissionManager"] = None
    
    def __new__(cls) -> "PermissionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._agent_permissions: Dict[str, PermissionSet] = {}
        self._user_permissions: Dict[str, PermissionSet] = {}
        self._tool_required_permissions: Dict[str, Set[Permission]] = {}
        self._skill_required_permissions: Dict[str, Set[Permission]] = {}
        self._initialized = True
        
        logger.info("PermissionManager initialized")
    
    def set_agent_permissions(self, agent_id: str, permissions: PermissionSet):
        """Set permissions for an agent"""
        self._agent_permissions[agent_id] = permissions
        logger.info(f"Set permissions for agent: {agent_id}")
    
    def get_agent_permissions(self, agent_id: str) -> PermissionSet:
        """Get permissions for an agent"""
        return self._agent_permissions.get(agent_id, PermissionSet())
    
    def check_agent_permission(
        self,
        agent_id: str,
        permission: Permission,
    ) -> bool:
        """Check if an agent has a specific permission"""
        perm_set = self.get_agent_permissions(agent_id)
        has_perm = perm_set.has(permission)
        
        if not has_perm:
            logger.warning(
                f"Agent {agent_id} lacks permission: {permission.value}"
            )
        
        return has_perm
    
    def require_agent_permission(
        self,
        agent_id: str,
        permission: Permission,
        action: str,
    ) -> bool:
        """
        Require a permission for an agent to perform an action.
        Raises PermissionError if not granted.
        """
        if not self.check_agent_permission(agent_id, permission):
            error_msg = (
                f"Agent {agent_id} requires permission '{permission.value}' "
                f"to perform action: {action}"
            )
            logger.error(error_msg)
            raise PermissionError(error_msg)
        
        return True
    
    def set_tool_required_permissions(
        self,
        tool_id: str,
        permissions: Set[Permission],
    ):
        """Set required permissions for a tool"""
        self._tool_required_permissions[tool_id] = permissions
        logger.debug(f"Tool {tool_id} requires permissions: {permissions}")
    
    def get_tool_required_permissions(self, tool_id: str) -> Set[Permission]:
        """Get required permissions for a tool"""
        return self._tool_required_permissions.get(tool_id, set())
    
    def check_agent_can_use_tool(
        self,
        agent_id: str,
        tool_id: str,
    ) -> bool:
        """Check if an agent has all permissions required to use a tool"""
        required = self.get_tool_required_permissions(tool_id)
        perm_set = self.get_agent_permissions(agent_id)
        
        missing = [p for p in required if not perm_set.has(p)]
        
        if missing:
            logger.warning(
                f"Agent {agent_id} lacks permissions for tool {tool_id}: {missing}"
            )
            return False
        
        return True
    
    def set_skill_required_permissions(
        self,
        skill_id: str,
        permissions: Set[Permission],
    ):
        """Set required permissions for a skill"""
        self._skill_required_permissions[skill_id] = permissions
        logger.debug(f"Skill {skill_id} requires permissions: {permissions}")
    
    def get_skill_required_permissions(self, skill_id: str) -> Set[Permission]:
        """Get required permissions for a skill"""
        return self._skill_required_permissions.get(skill_id, set())
    
    def check_agent_can_use_skill(
        self,
        agent_id: str,
        skill_id: str,
    ) -> bool:
        """Check if an agent has all permissions required to use a skill"""
        required = self.get_skill_required_permissions(skill_id)
        perm_set = self.get_agent_permissions(agent_id)
        
        missing = [p for p in required if not perm_set.has(p)]
        
        if missing:
            logger.warning(
                f"Agent {agent_id} lacks permissions for skill {skill_id}: {missing}"
            )
            return False
        
        return True
    
    def get_sensitive_permissions(self) -> List[Permission]:
        """Return list of sensitive permissions that require confirmation"""
        return [
            Permission.TERMINAL_EXECUTE,
            Permission.CODE_EXECUTE,
            Permission.DELETE_FILES,
            Permission.GITHUB_WRITE,
            Permission.EMAIL_SEND,
            Permission.DATABASE_WRITE,
            Permission.ADMIN,
            Permission.SYSTEM_CONFIG,
        ]
    
    def is_sensitive(self, permission: Permission) -> bool:
        """Check if a permission is considered sensitive"""
        return permission in self.get_sensitive_permissions()


# Global permission manager instance
permission_manager = PermissionManager()


def get_permission_manager() -> PermissionManager:
    """Dependency for FastAPI to get permission manager"""
    return permission_manager
