"""
JARVIS AI - Main Application

Aplicação FastAPI completa com todas as rotas e configurações.
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

# Importar configurações
from backend.config.settings import settings

# Importar registries (inicialização lazy)
from backend.agents.agent_registry import AgentRegistry
from backend.skills.skill_registry import SkillRegistry
from backend.tools.tool_registry import ToolRegistry
from backend.core.orchestrator import Orchestrator
from backend.events.event_bus import EventBus

# Importar rotas
from backend.api.routes.jarvis import router as jarvis_router

# Importar WebSocket
from backend.api.websocket.manager import websocket_endpoint, get_connection_manager

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Gerenciador de ciclo de vida da aplicação.
    
    Executa inicialização e shutdown adequados.
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info("🚀 JARVIS AI - Starting up...")
    logger.info("=" * 60)
    
    try:
        # Inicializar registries (singleton)
        logger.info("📦 Initializing Agent Registry...")
        agent_registry = AgentRegistry.get_instance()
        
        logger.info("📦 Initializing Skill Registry...")
        skill_registry = SkillRegistry.get_instance()
        
        logger.info("📦 Initializing Tool Registry...")
        tool_registry = ToolRegistry.get_instance()
        
        logger.info("🧠 Initializing Orchestrator...")
        orchestrator = Orchestrator.get_instance()
        
        logger.info("📡 Initializing Event Bus...")
        event_bus = EventBus.get_instance()
        
        # Registrar eventos do sistema
        await event_bus.publish("system_startup", {
            "message": "JARVIS AI system started successfully",
            "components": [
                "Agent Registry",
                "Skill Registry", 
                "Tool Registry",
                "Orchestrator",
                "Event Bus"
            ]
        })
        
        logger.info("✅ All components initialized successfully")
        logger.info("=" * 60)
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    finally:
        # === SHUTDOWN ===
        logger.info("=" * 60)
        logger.info("🛑 JARVIS AI - Shutting down...")
        
        try:
            # Publicar evento de shutdown
            await event_bus.publish("system_shutdown", {
                "message": "JARVIS AI system shutting down"
            })
            
            logger.info("✅ Shutdown completed successfully")
        except Exception as e:
            logger.error(f"⚠️ Shutdown error: {e}")
        
        logger.info("=" * 60)


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="JARVIS AI - Personal AI Operating System",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global para exceções não tratadas."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
        }
    )


# ==================== ROUTES ====================

# Incluir routers
app.include_router(jarvis_router)

# WebSocket endpoint
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Endpoint WebSocket para streaming de eventos em tempo real."""
    client_id = "anonymous"
    
    # Extrair client_id dos query params se disponível
    if websocket.query_params.get("client_id"):
        client_id = websocket.query_params["client_id"]
    
    await websocket_endpoint(websocket, client_id)


# ==================== ROOT ENDPOINTS ====================

@app.get("/")
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "JARVIS AI - Personal AI Operating System",
        "docs": "/docs",
        "health": "/health",
        "stats": "/stats",
        "websocket": "/ws/events"
    }


@app.get("/ping")
async def ping():
    """Endpoint simples para verificar disponibilidade."""
    return {"status": "pong", "timestamp": __import__("datetime").datetime.utcnow().isoformat()}


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting JARVIS AI server on {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
