"""
Router REST + WebSocket for real-time agent management.

This module provides:
- REST API endpoints for agent listing, details, and actions
- WebSocket endpoint for real-time updates
- In-memory store (ready to be replaced with Redis in production)
- Thread-safe operations with asyncio.Lock
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# --- Data Models ---

class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class AgentAction(str, Enum):
    """Available agent actions."""
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    RESTART = "restart"
    PRIORITIZE = "prioritize"


class Agent(BaseModel):
    """Agent data model."""
    id: str
    name: str
    type: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_pending: int = 0
    last_update: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionRequest(BaseModel):
    """Request model for agent actions."""
    action: AgentAction
    parameters: Dict[str, Any] = Field(default_factory=dict)


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # "snapshot", "agent_updated", "task_added", "task_completed", "log_line"
    data: Any
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- In-Memory Store ---
# This is designed to be easily replaced with Redis in production.
# Extension points:
# 1. Replace _agents dict with Redis hash: HSET agents:{agent_id} field value
# 2. Replace _lock with Redis distributed lock (redlock pattern)
# 3. Use Redis pub/sub for broadcasting instead of ConnectionManager
# 4. Store logs in Redis list: LPUSH agent:{agent_id}:logs message

class AgentStore:
    """In-memory agent store with thread-safe operations.
    
    Production replacement notes:
    - Use Redis HSET for agents: redis.hset(f"agent:{agent_id}", mapping=agent.dict())
    - Use Redis pub/sub for events: redis.publish("agent_events", json.dumps(event))
    - Use Redis sorted sets for task queues
    """
    
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._lock = asyncio.Lock()
        self._initialize_sample_agents()
    
    def _initialize_sample_agents(self):
        """Initialize with sample agents for demonstration."""
        sample_agents = [
            Agent(
                id="planner-001",
                name="Planner Agent",
                type="planner",
                status=AgentStatus.IDLE,
                tasks_completed=5,
                tasks_pending=2,
                metadata={"model": "gpt-4", "priority": "high"}
            ),
            Agent(
                id="executor-001",
                name="Executor Agent",
                type="executor",
                status=AgentStatus.RUNNING,
                current_task="Implement feature X",
                tasks_completed=12,
                tasks_pending=3,
                metadata={"model": "gpt-3.5-turbo", "priority": "medium"}
            ),
            Agent(
                id="reviewer-001",
                name="Reviewer Agent",
                type="reviewer",
                status=AgentStatus.IDLE,
                tasks_completed=8,
                tasks_pending=1,
                metadata={"model": "gpt-4", "priority": "high"}
            ),
        ]
        for agent in sample_agents:
            self._agents[agent.id] = agent
    
    async def get_all(self) -> List[Agent]:
        """Get all agents."""
        async with self._lock:
            return list(self._agents.values())
    
    async def get(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        async with self._lock:
            return self._agents.get(agent_id)
    
    async def ensure_agent(self, agent: Agent) -> Agent:
        """Ensure agent exists (create if not present)."""
        async with self._lock:
            if agent.id not in self._agents:
                self._agents[agent.id] = agent
            return self._agents[agent.id]
    
    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Optional[Agent]:
        """Update agent fields."""
        async with self._lock:
            if agent_id not in self._agents:
                return None
            agent = self._agents[agent_id]
            for key, value in updates.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            agent.last_update = datetime.utcnow().isoformat()
            return agent
    
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from store."""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False


# --- WebSocket Connection Manager ---

class ConnectionManager:
    """Manages WebSocket connections with concurrent broadcast support.
    
    Production replacement notes:
    - Replace with Redis pub/sub for scalability
    - Use WebSocket gateway (e.g., Socket.IO with Redis adapter)
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
    
    async def broadcast(self, message: WebSocketMessage):
        """Broadcast message to all connected clients (non-blocking).
        
        Failed sends are handled gracefully without blocking other clients.
        """
        message_json = message.model_dump_json()
        
        # Create tasks for all connections
        async with self._lock:
            connections = list(self.active_connections)
        
        # Send to all connections concurrently
        send_tasks = [self._send_message(ws, message_json) for ws in connections]
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    async def _send_message(self, websocket: WebSocket, message: str):
        """Send message to a single WebSocket (with error handling)."""
        try:
            await websocket.send_text(message)
        except Exception:
            # Connection likely closed; will be cleaned up on next disconnect
            pass


# --- Global Instances ---

store = AgentStore()
manager = ConnectionManager()
router = APIRouter(prefix="/api/agents", tags=["agents"])


# --- REST Endpoints ---

@router.get("", response_model=List[Agent])
async def list_agents():
    """List all agents."""
    agents = await store.get_all()
    return agents


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get details of a specific agent."""
    agent = await store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/action")
async def execute_action(agent_id: str, action_request: ActionRequest):
    """Execute an action on an agent (pause/resume/stop/restart/prioritize)."""
    agent = await store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Validate and execute action
    action = action_request.action
    updates: Dict[str, Any] = {}
    
    if action == AgentAction.PAUSE:
        if agent.status != AgentStatus.RUNNING:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot pause agent in {agent.status} state"
            )
        updates["status"] = AgentStatus.PAUSED
    
    elif action == AgentAction.RESUME:
        if agent.status != AgentStatus.PAUSED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume agent in {agent.status} state"
            )
        updates["status"] = AgentStatus.RUNNING
    
    elif action == AgentAction.STOP:
        if agent.status == AgentStatus.STOPPED:
            raise HTTPException(
                status_code=400,
                detail="Agent is already stopped"
            )
        updates["status"] = AgentStatus.STOPPED
        updates["current_task"] = None
    
    elif action == AgentAction.RESTART:
        updates["status"] = AgentStatus.RUNNING
        updates["tasks_completed"] = 0
        updates["tasks_pending"] = agent.tasks_pending
    
    elif action == AgentAction.PRIORITIZE:
        priority = action_request.parameters.get("priority", "high")
        if "metadata" not in agent.metadata:
            updates["metadata"] = {}
        agent.metadata["priority"] = priority
        updates["metadata"] = agent.metadata
    
    # Apply updates
    updated_agent = await store.update_agent(agent_id, updates)
    
    # Broadcast update via WebSocket
    await manager.broadcast(
        WebSocketMessage(
            type="agent_updated",
            data=updated_agent.model_dump() if updated_agent else {}
        )
    )
    
    return {
        "message": f"Action {action} executed successfully",
        "agent": updated_agent
    }


# --- WebSocket Endpoint ---

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.
    
    On connect: Sends complete snapshot of all agents
    Then: Broadcasts events (agent_updated, task_added, task_completed, log_line)
    """
    await manager.connect(websocket)
    
    try:
        # Send initial snapshot
        agents = await store.get_all()
        snapshot = WebSocketMessage(
            type="snapshot",
            data=[agent.model_dump() for agent in agents]
        )
        await websocket.send_text(snapshot.model_dump_json())
        
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client (e.g., ping/pong for keepalive)
            data = await websocket.receive_text()
            
            # Echo back for keepalive (optional: handle client commands)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


# --- Helper functions for external use ---

async def broadcast_task_added(agent_id: str, task_description: str):
    """Broadcast that a task was added to an agent."""
    await manager.broadcast(
        WebSocketMessage(
            type="task_added",
            data={"agent_id": agent_id, "task": task_description}
        )
    )


async def broadcast_task_completed(agent_id: str, task_description: str):
    """Broadcast that a task was completed by an agent."""
    agent = await store.get(agent_id)
    if agent:
        await store.update_agent(agent_id, {"tasks_completed": agent.tasks_completed + 1})
    
    await manager.broadcast(
        WebSocketMessage(
            type="task_completed",
            data={"agent_id": agent_id, "task": task_description}
        )
    )


async def broadcast_log_line(agent_id: str, log_message: str, level: str = "info"):
    """Broadcast a log line from an agent."""
    await manager.broadcast(
        WebSocketMessage(
            type="log_line",
            data={"agent_id": agent_id, "message": log_message, "level": level}
        )
    )
