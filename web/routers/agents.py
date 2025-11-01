"""
Real-time agent management API with REST endpoints and WebSocket support.

This module provides:
- REST API for agent management (list, detail, actions)
- WebSocket endpoint for real-time updates
- In-memory store for agent state (replaceable with Redis for production)
- ConnectionManager for handling multiple WebSocket clients
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Router instance
router = APIRouter(prefix="/api/agents", tags=["agents"])


# ============================================================================
# Data Models
# ============================================================================

class AgentState(BaseModel):
    """Model representing the state of an agent."""
    id: str
    name: str
    status: str = "idle"  # idle, running, paused, stopped, error
    current_task: Optional[str] = None
    tasks_pending: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    uptime_seconds: float = 0.0
    last_activity: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class AgentAction(BaseModel):
    """Model for agent actions."""
    action: str = Field(..., description="Action to perform: pause, resume, stop, restart, prioritize")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional parameters for the action")


class TaskInfo(BaseModel):
    """Model for task information."""
    task_id: str
    agent_id: str
    description: str
    status: str
    created_at: str


# ============================================================================
# In-Memory Store
# ============================================================================

class AgentStore:
    """
    In-memory store for agent state.
    
    Note: For production with multiple instances, replace with Redis or
    a distributed cache with pub/sub for synchronizing events.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentState] = {}
        self._lock = asyncio.Lock()
    
    async def ensure_agent(self, agent_id: str, name: str = None) -> AgentState:
        """Ensure agent exists in store, create if not present."""
        async with self._lock:
            if agent_id not in self._agents:
                self._agents[agent_id] = AgentState(
                    id=agent_id,
                    name=name or f"Agent {agent_id}",
                    last_activity=datetime.utcnow().isoformat()
                )
            return self._agents[agent_id]
    
    async def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """Get agent by ID."""
        async with self._lock:
            return self._agents.get(agent_id)
    
    async def list_agents(self) -> List[AgentState]:
        """List all agents."""
        async with self._lock:
            return list(self._agents.values())
    
    async def update_agent(self, agent_id: str, **kwargs) -> AgentState:
        """Update agent state."""
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not found")
            agent = self._agents[agent_id]
            for key, value in kwargs.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            agent.last_activity = datetime.utcnow().isoformat()
            return agent
    
    async def delete_agent(self, agent_id: str):
        """Remove agent from store."""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]


# Global store instance
agent_store = AgentStore()


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Features:
    - Non-blocking broadcast using asyncio.create_task
    - Automatic cleanup of disconnected clients
    - Safe concurrent access
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def _send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to a single client with error handling."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.
        
        Uses asyncio.create_task for non-blocking sends.
        """
        async with self._lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            asyncio.create_task(self._send_to_client(connection, message))
    
    async def send_snapshot(self, websocket: WebSocket):
        """Send current state snapshot to a newly connected client."""
        agents = await agent_store.list_agents()
        snapshot = {
            "type": "snapshot",
            "timestamp": datetime.utcnow().isoformat(),
            "agents": [agent.model_dump() for agent in agents]
        }
        await websocket.send_json(snapshot)


# Global connection manager
connection_manager = ConnectionManager()


# ============================================================================
# REST API Endpoints
# ============================================================================

@router.get("/", response_model=List[AgentState])
async def list_agents():
    """
    List all agents with their current state.
    
    Returns a list of all registered agents with their status, tasks, and metrics.
    """
    agents = await agent_store.list_agents()
    return agents


@router.get("/{agent_id}", response_model=AgentState)
async def get_agent_detail(agent_id: str):
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_id: Unique identifier for the agent
    
    Returns:
        Agent state with all details
    
    Raises:
        HTTPException: 404 if agent not found
    """
    agent = await agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent


@router.post("/{agent_id}/action")
async def execute_agent_action(agent_id: str, action: AgentAction):
    """
    Execute an action on a specific agent.
    
    Supported actions:
    - pause: Pause agent execution
    - resume: Resume paused agent
    - stop: Stop agent gracefully
    - restart: Restart agent
    - prioritize: Prioritize agent tasks (requires priority parameter)
    
    Args:
        agent_id: Unique identifier for the agent
        action: Action details including action type and parameters
    
    Returns:
        Confirmation message with new agent state
    
    Raises:
        HTTPException: 404 if agent not found, 400 if invalid action
    """
    # Validate agent exists
    agent = await agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    # Process action
    action_type = action.action.lower()
    
    if action_type == "pause":
        if agent.status != "running":
            raise HTTPException(status_code=400, detail="Can only pause running agents")
        updated_agent = await agent_store.update_agent(agent_id, status="paused")
        message = f"Agent {agent_id} paused"
    
    elif action_type == "resume":
        if agent.status != "paused":
            raise HTTPException(status_code=400, detail="Can only resume paused agents")
        updated_agent = await agent_store.update_agent(agent_id, status="running")
        message = f"Agent {agent_id} resumed"
    
    elif action_type == "stop":
        updated_agent = await agent_store.update_agent(agent_id, status="stopped", current_task=None)
        message = f"Agent {agent_id} stopped"
    
    elif action_type == "restart":
        updated_agent = await agent_store.update_agent(
            agent_id,
            status="running",
            current_task=None,
            tasks_pending=0,
            uptime_seconds=0.0
        )
        message = f"Agent {agent_id} restarted"
    
    elif action_type == "prioritize":
        priority = action.parameters.get("priority")
        if priority is None:
            raise HTTPException(status_code=400, detail="Priority parameter required")
        updated_agent = await agent_store.update_agent(agent_id)
        updated_agent.metrics["priority"] = priority
        message = f"Agent {agent_id} priority set to {priority}"
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action_type}")
    
    # Broadcast update to WebSocket clients
    asyncio.create_task(connection_manager.broadcast({
        "type": "agent_updated",
        "timestamp": datetime.utcnow().isoformat(),
        "agent": updated_agent.model_dump()
    }))
    
    return {
        "message": message,
        "agent": updated_agent
    }


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent updates.
    
    Protocol:
    1. Client connects
    2. Server sends snapshot of all agents
    3. Server broadcasts events:
       - agent_updated: Agent state changed
       - task_added: New task assigned to agent
       - task_completed: Task finished
       - log_line: Log message from agent
    
    Example messages:
    - Snapshot: {"type": "snapshot", "timestamp": "...", "agents": [...]}
    - Update: {"type": "agent_updated", "timestamp": "...", "agent": {...}}
    - Task: {"type": "task_added", "timestamp": "...", "task": {...}}
    """
    await connection_manager.connect(websocket)
    
    try:
        # Send initial snapshot
        await connection_manager.send_snapshot(websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client (e.g., ping/pong, subscriptions)
            data = await websocket.receive_text()
            
            # Echo back or handle client messages if needed
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(websocket)


# ============================================================================
# Helper Functions for Broadcasting Events
# ============================================================================

async def broadcast_task_added(agent_id: str, task_id: str, description: str):
    """
    Broadcast that a new task was added to an agent.
    
    Call this when assigning work to an agent.
    """
    await connection_manager.broadcast({
        "type": "task_added",
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "task": {
            "task_id": task_id,
            "description": description,
            "status": "pending"
        }
    })
    
    # Update agent's pending tasks count
    agent = await agent_store.get_agent(agent_id)
    if agent:
        await agent_store.update_agent(agent_id, tasks_pending=agent.tasks_pending + 1)


async def broadcast_task_completed(agent_id: str, task_id: str, success: bool = True):
    """
    Broadcast that an agent completed a task.
    
    Call this when an agent finishes work.
    """
    await connection_manager.broadcast({
        "type": "task_completed",
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "task_id": task_id,
        "success": success
    })
    
    # Update agent's task counts
    agent = await agent_store.get_agent(agent_id)
    if agent:
        await agent_store.update_agent(
            agent_id,
            tasks_pending=max(0, agent.tasks_pending - 1),
            tasks_completed=agent.tasks_completed + (1 if success else 0),
            tasks_failed=agent.tasks_failed + (0 if success else 1),
            current_task=None
        )


async def broadcast_log_line(agent_id: str, level: str, message: str):
    """
    Broadcast a log line from an agent.
    
    Call this to stream agent logs to the dashboard.
    """
    await connection_manager.broadcast({
        "type": "log_line",
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "level": level,
        "message": message
    })


# ============================================================================
# Initialization
# ============================================================================

async def initialize_demo_agents():
    """
    Initialize some demo agents for testing.
    
    This is called on startup to populate the store with example data.
    Remove or modify for production use.
    """
    demo_agents = [
        {"id": "planner", "name": "Planner Agent", "status": "idle"},
        {"id": "executor", "name": "Executor Agent", "status": "idle"},
        {"id": "reviewer", "name": "Reviewer Agent", "status": "idle"},
    ]
    
    for agent_data in demo_agents:
        await agent_store.ensure_agent(agent_data["id"], agent_data["name"])
        await agent_store.update_agent(agent_data["id"], status=agent_data["status"])
    
    logger.info(f"Initialized {len(demo_agents)} demo agents")


# Note: Integration points for model calls
# =========================================
# When integrating with Ollama, GitHub Models, or other model providers:
# 
# 1. If the SDK is synchronous (blocking), wrap calls with run_in_executor:
#    
#    loop = asyncio.get_event_loop()
#    result = await loop.run_in_executor(None, blocking_model_call, prompt)
#
# 2. If the SDK is async-native, call directly:
#    
#    result = await async_model_call(prompt)
#
# 3. For long-running model operations, update agent status and broadcast:
#    
#    await agent_store.update_agent(agent_id, status="running", current_task="Generating response")
#    await connection_manager.broadcast({...})
#    result = await model_call()
#    await agent_store.update_agent(agent_id, status="idle", current_task=None)
