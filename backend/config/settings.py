"""
JARVIS AI - Configuration Module

Centralized configuration management using Pydantic Settings.
All environment variables and application settings are managed here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from enum import Enum
import os


class ModelStrategy(str, Enum):
    """Model routing strategies"""
    AUTO = "auto"
    BEST_QUALITY = "best_quality"
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    FREE_FIRST = "free_first"
    LOCAL_ONLY = "local_only"
    MANUAL = "manual"


class DatabaseType(str, Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="JARVIS_"
    )
    
    # Application
    APP_NAME: str = "JARVIS AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # Database
    DATABASE_TYPE: DatabaseType = DatabaseType.SQLITE
    DATABASE_URL: Optional[str] = None
    SQLITE_PATH: str = "./data/local/jarvis.db"
    ECHO_SQL: bool = False
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: os.urandom(32).hex())
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Agent Limits
    MAX_AGENT_DEPTH: int = 10
    MAX_AGENTS_PER_MISSION: int = 50
    MAX_TASKS_PER_MISSION: int = 200
    MAX_RECURSION_CALLS: int = 100
    MAX_TOKENS_PER_REQUEST: int = 128000
    MAX_COST_PER_MISSION: float = 10.0  # USD
    
    # AI Providers - API Keys (never expose to frontend)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Provider Settings
    DEFAULT_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    MODEL_STRATEGY: ModelStrategy = ModelStrategy.AUTO
    ENABLE_FALLBACK: bool = True
    FALLBACK_CHAIN: List[str] = ["openai", "anthropic", "google", "groq"]
    
    # Memory Settings
    MEMORY_ENABLED: bool = True
    MAX_CONVERSATION_HISTORY: int = 50
    MEMORY_RETENTION_DAYS: int = 30
    
    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_EXTENSIONS: List[str] = [
        ".txt", ".md", ".pdf", ".doc", ".docx",
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".mp3", ".wav", ".ogg",
        ".mp4", ".avi", ".mov",
        ".json", ".yaml", ".yml", ".csv",
        ".py", ".js", ".ts", ".html", ".css"
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = "./data/logs/jarvis.log"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    @model_validator(mode='before')
    @classmethod
    def build_database_url(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Build database URL if not provided"""
        if values.get("DATABASE_URL"):
            return values
        
        db_type = values.get("DATABASE_TYPE", DatabaseType.SQLITE.value if isinstance(DatabaseType.SQLITE, Enum) else "sqlite")
        
        if db_type == "sqlite" or (isinstance(db_type, DatabaseType) and db_type == DatabaseType.SQLITE):
            sqlite_path = values.get("SQLITE_PATH", "./data/local/jarvis.db")
            # Ensure directory exists
            db_dir = os.path.dirname(sqlite_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            values["DATABASE_URL"] = f"sqlite+aiosqlite:///{sqlite_path}"
        
        return values
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @property
    def enabled_providers(self) -> List[str]:
        """Return list of enabled AI providers based on available keys"""
        providers = []
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if self.GOOGLE_API_KEY:
            providers.append("google")
        if self.GROQ_API_KEY:
            providers.append("groq")
        if self.OPENROUTER_API_KEY:
            providers.append("openrouter")
        # Ollama is local, always available
        providers.append("ollama")
        return providers


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency for FastAPI to get settings"""
    return settings
