"""
JARVIS AI - WebSocket Manager

Gerenciamento de conexões WebSocket para streaming de eventos em tempo real.
"""

import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerenciador de conexões WebSocket."""
    
    def __init__(self):
        # Conexões ativas: {websocket: client_id}
        self.active_connections: Dict[WebSocket, str] = {}
        # Assinaturas por cliente: {client_id: set of event_types}
        self.subscriptions: Dict[str, Set[str]] = {}
        # Lock para operações thread-safe
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """Aceitar conexão WebSocket."""
        try:
            await websocket.accept()
            async with self._lock:
                self.active_connections[websocket] = client_id
                self.subscriptions[client_id] = {"*"}  # Subscribe to all events by default
            
            logger.info(f"Client {client_id} connected")
            
            # Enviar mensagem de boas-vindas
            await self.send_personal_message(
                websocket,
                {
                    "type": "connection_established",
                    "client_id": client_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Connected to JARVIS Event Stream"
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect client {client_id}: {e}")
            return False
    
    def disconnect(self, websocket: WebSocket):
        """Remover conexão WebSocket."""
        client_id = self.active_connections.pop(websocket, None)
        if client_id:
            self.subscriptions.pop(client_id, None)
            logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Enviar mensagem para um cliente específico."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
    
    async def broadcast(self, message: dict, event_type: Optional[str] = None):
        """
        Broadcast para todos os clientes assinantes.
        
        Args:
            message: Dados da mensagem
            event_type: Tipo do evento (para filtrar assinantes)
        """
        if not self.active_connections:
            return
        
        # Adicionar metadados
        message["timestamp"] = datetime.utcnow().isoformat()
        if event_type:
            message["event_type"] = event_type
        
        async with self._lock:
            disconnected = []
            
            for websocket, client_id in list(self.active_connections.items()):
                # Verificar se o cliente está assinado para este tipo de evento
                subscribed_events = self.subscriptions.get(client_id, {"*"})
                
                if "*" in subscribed_events or (event_type and event_type in subscribed_events):
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        # Cliente desconectou
                        disconnected.append(websocket)
            
            # Limpar conexões desconectadas
            for ws in disconnected:
                self.disconnect(ws)
    
    async def subscribe(self, client_id: str, event_types: list):
        """Adicionar assinatura de eventos para um cliente."""
        async with self._lock:
            if client_id in self.subscriptions:
                self.subscriptions[client_id].update(event_types)
            else:
                self.subscriptions[client_id] = set(event_types)
        
        logger.info(f"Client {client_id} subscribed to: {event_types}")
    
    async def unsubscribe(self, client_id: str, event_types: list):
        """Remover assinatura de eventos de um cliente."""
        async with self._lock:
            if client_id in self.subscriptions:
                self.subscriptions[client_id] -= set(event_types)
        
        logger.info(f"Client {client_id} unsubscribed from: {event_types}")
    
    def get_active_connections_count(self) -> int:
        """Retornar número de conexões ativas."""
        return len(self.active_connections)
    
    async def send_heartbeat(self):
        """Enviar heartbeat para todas as conexões ativas."""
        heartbeat_message = {
            "type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": len(self.active_connections)
        }
        await self.broadcast(heartbeat_message, "heartbeat")


# Singleton instance
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Obter instância singleton do ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


async def websocket_endpoint(websocket: WebSocket, client_id: str = "anonymous"):
    """
    Endpoint WebSocket para streaming de eventos.
    
    Uso:
        ws://localhost:8000/ws/events?client_id=user123
    """
    manager = get_connection_manager()
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Aguardar mensagens do cliente (subscribe/unsubscribe)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    event_types = message.get("events", [])
                    await manager.subscribe(client_id, event_types)
                    await manager.send_personal_message(
                        websocket,
                        {
                            "type": "subscribed",
                            "events": event_types,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                elif action == "unsubscribe":
                    event_types = message.get("events", [])
                    await manager.unsubscribe(client_id, event_types)
                    await manager.send_personal_message(
                        websocket,
                        {
                            "type": "unsubscribed",
                            "events": event_types,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                elif action == "ping":
                    await manager.send_personal_message(
                        websocket,
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(websocket)
