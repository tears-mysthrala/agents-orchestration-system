# Web Module - Real-time Agent Management

This module provides a web-based interface for managing and monitoring agents in real-time using WebSocket and REST APIs.

## Features

- **REST API** for agent management (list, detail, actions)
- **WebSocket** endpoint for real-time updates
- **Dashboard UI** with live agent status monitoring
- **Action Controls** to pause, resume, stop, and restart agents
- **Live Logs** streaming from agents to the dashboard
- **Metrics Dashboard** showing agent activity and task completion

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Web Server

From the repository root:

```bash
# Using uvicorn directly
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000

# Or using the provided script
python scripts/run_web.py
```

### 3. Access the Dashboard

Open your browser and navigate to:

- **Main Interface**: http://localhost:8000/
- **Agent Dashboard**: http://localhost:8000/static/dashboard.html
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Health & Metrics

- `GET /health` - Health check endpoint
- `GET /metrics` - Basic application metrics

### Agent Management (REST API)

- `GET /api/agents` - List all agents
- `GET /api/agents/{agent_id}` - Get agent details
- `POST /api/agents/{agent_id}/action` - Execute action on agent

#### Supported Actions

```json
// Pause a running agent
{
  "action": "pause"
}

// Resume a paused agent
{
  "action": "resume"
}

// Stop an agent
{
  "action": "stop"
}

// Restart an agent
{
  "action": "restart"
}

// Prioritize an agent (requires priority parameter)
{
  "action": "prioritize",
  "parameters": {
    "priority": 10
  }
}
```

### WebSocket (Real-time Updates)

Connect to: `ws://localhost:8000/api/agents/ws`

#### Message Types (Server → Client)

**Snapshot** (sent on connection):
```json
{
  "type": "snapshot",
  "timestamp": "2024-11-01T12:00:00",
  "agents": [...]
}
```

**Agent Updated**:
```json
{
  "type": "agent_updated",
  "timestamp": "2024-11-01T12:00:01",
  "agent": {...}
}
```

**Task Added**:
```json
{
  "type": "task_added",
  "timestamp": "2024-11-01T12:00:02",
  "agent_id": "planner",
  "task": {
    "task_id": "task-123",
    "description": "Generate project plan",
    "status": "pending"
  }
}
```

**Task Completed**:
```json
{
  "type": "task_completed",
  "timestamp": "2024-11-01T12:00:03",
  "agent_id": "executor",
  "task_id": "task-123",
  "success": true
}
```

**Log Line**:
```json
{
  "type": "log_line",
  "timestamp": "2024-11-01T12:00:04",
  "agent_id": "reviewer",
  "level": "info",
  "message": "Starting review process..."
}
```

#### Message Types (Client → Server)

**Ping** (keep-alive):
```json
{
  "type": "ping"
}
```

Server responds with:
```json
{
  "type": "pong",
  "timestamp": "2024-11-01T12:00:05"
}
```

## Testing the WebSocket

### Using wscat (Command Line)

Install wscat:
```bash
npm install -g wscat
```

Connect and test:
```bash
# Connect to WebSocket
wscat -c ws://localhost:8000/api/agents/ws

# You'll receive a snapshot
# Send a ping
> {"type": "ping"}

# You'll receive a pong
< {"type": "pong", "timestamp": "..."}
```

### Using the Dashboard

1. Open http://localhost:8000/static/dashboard.html
2. The dashboard automatically connects to the WebSocket
3. You'll see the connection status in the top-right corner
4. Agent list updates in real-time
5. Use action buttons to control agents
6. Watch logs in the live log panel

### Using Python

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/api/agents/ws"
    async with websockets.connect(uri) as websocket:
        # Receive snapshot
        snapshot = await websocket.recv()
        print(f"Snapshot: {snapshot}")
        
        # Send ping
        await websocket.send(json.dumps({"type": "ping"}))
        
        # Receive pong
        pong = await websocket.recv()
        print(f"Pong: {pong}")

asyncio.run(test_websocket())
```

## Testing the REST API

### Using curl

```bash
# List all agents
curl http://localhost:8000/api/agents

# Get specific agent
curl http://localhost:8000/api/agents/planner

# Execute action
curl -X POST http://localhost:8000/api/agents/planner/action \
  -H "Content-Type: application/json" \
  -d '{"action": "restart"}'

# Prioritize agent
curl -X POST http://localhost:8000/api/agents/executor/action \
  -H "Content-Type: application/json" \
  -d '{"action": "prioritize", "parameters": {"priority": 10}}'
```

### Using httpie

```bash
# List agents
http GET http://localhost:8000/api/agents

# Execute action
http POST http://localhost:8000/api/agents/planner/action action=restart
```

## Running Tests

```bash
# Run all tests
pytest tests/test_agents_api.py -v

# Run specific test class
pytest tests/test_agents_api.py::TestAgentRestAPI -v

# Run with coverage
pytest tests/test_agents_api.py --cov=web.routers.agents --cov-report=html
```

## Architecture

### Components

1. **web/app.py** - FastAPI application with endpoints and router registration
2. **web/routers/agents.py** - Agent management REST API and WebSocket handler
3. **web/static/dashboard.html** - Dashboard UI
4. **web/static/app.js** - WebSocket client and UI logic

### Data Flow

```
┌─────────────┐      WebSocket      ┌──────────────┐
│  Dashboard  │◄────────────────────►│  FastAPI App │
└─────────────┘                      └──────────────┘
                                            │
                     REST API               │
                        ▼                   ▼
                ┌──────────────┐    ┌─────────────┐
                │ Agent Actions│    │ Agent Store │
                └──────────────┘    └─────────────┘
                        │                   │
                        └───────┬───────────┘
                                ▼
                        ┌──────────────┐
                        │ Broadcast to │
                        │  All Clients │
                        └──────────────┘
```

## Production Considerations

### Current Implementation (Development/Testing)

- **In-memory store** for agent state
- **No authentication** on API endpoints
- **Single instance** deployment
- **No persistence** - state lost on restart

### Recommended for Production

1. **Replace In-Memory Store with Redis**
   ```python
   # Use Redis for shared state across instances
   import redis.asyncio as redis
   redis_client = await redis.from_url("redis://localhost")
   ```

2. **Add Authentication**
   ```python
   from fastapi import Depends, HTTPException
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   @router.post("/{agent_id}/action")
   async def execute_action(
       agent_id: str,
       action: AgentAction,
       token: str = Depends(security)
   ):
       # Verify token
       ...
   ```

3. **Use Pub/Sub for Multi-Instance**
   ```python
   # Broadcast events across instances using Redis Pub/Sub
   await redis_client.publish("agent_updates", json.dumps(message))
   ```

4. **Add Rate Limiting**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @router.post("/{agent_id}/action")
   @limiter.limit("10/minute")
   async def execute_action(...):
       ...
   ```

5. **Enable CORS** (if frontend is on different domain)
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

6. **Add Monitoring**
   - Use Prometheus client for metrics
   - Add structured logging
   - Implement distributed tracing

## Async Safety Notes

The implementation uses async/await throughout to maintain non-blocking operation:

- **asyncio.create_task()** for broadcasting WebSocket messages
- **run_in_executor()** for blocking calls (see comments in code)
- **asyncio.Lock** for thread-safe access to shared state

### Integrating with Model Providers

When calling model SDKs (Ollama, OpenAI, etc.):

**For synchronous/blocking SDKs:**
```python
import asyncio

# Wrap blocking call in executor
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, ollama.generate, prompt)
```

**For async SDKs:**
```python
# Call directly
result = await openai_client.chat.completions.create(...)
```

## Troubleshooting

### WebSocket Connection Fails

- Check firewall allows port 8000
- Verify server is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Try using `ws://` instead of `wss://` for local testing

### Agents Not Showing Up

- Check if demo agents initialized: check logs on startup
- Try refreshing manually with the Refresh button
- Verify API responds: `curl http://localhost:8000/api/agents`

### Actions Not Working

- Check agent status - some actions only work in specific states
- Verify action payload in browser Network tab
- Check server logs for error messages

### Tests Failing

- Ensure dependencies installed: `pip install -r requirements.txt`
- Clean test cache: `pytest --cache-clear`
- Run with verbose output: `pytest -vv`

## Contributing

When adding new features:

1. Update the REST API in `web/routers/agents.py`
2. Add corresponding tests in `tests/test_agents_api.py`
3. Update the dashboard UI if needed
4. Document new endpoints in this README
5. Consider async safety and production scalability

## License

See the main repository LICENSE file.
