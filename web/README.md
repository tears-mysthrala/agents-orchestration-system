# Web Dashboard - Real-time Agent Management

Web interface for real-time monitoring and control of orchestration agents. Built with FastAPI (backend) and vanilla JavaScript (frontend) for maximum compatibility.

## Features

- **Real-time Updates**: WebSocket-based live updates of agent status
- **Agent Management**: Control agents with actions (pause, resume, stop, restart, prioritize)
- **REST API**: Full REST API for programmatic access
- **Cross-platform**: Works on Windows 11 and Arch Linux
- **Monitoring**: Health checks and Prometheus-compatible metrics

## Architecture

### Backend (FastAPI)

- **web/app.py**: Main FastAPI application with health/metrics endpoints
- **web/routers/agents.py**: Agents router with REST API and WebSocket support
  - In-memory store (ready to be replaced with Redis)
  - Thread-safe operations with asyncio.Lock
  - WebSocket connection manager for broadcasting

### Frontend (HTML/JS)

- **web/static/dashboard.html**: Dashboard UI
- **web/static/app.js**: WebSocket client and UI logic
- Compatible with modern browsers on Windows and Linux

## Quick Start

### Windows 11

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run the web server
python scripts\run_web.py
```

### Linux (Arch, Ubuntu, etc.)

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Optional: Install uvloop for better performance (Linux only)
pip install uvloop

# Run the web server
python scripts/run_web.py
```

### Access the Dashboard

Open your browser and navigate to:
- **Dashboard**: http://127.0.0.1:8000/static/dashboard.html
- **API Documentation**: http://127.0.0.1:8000/docs (Swagger UI)
- **Health Check**: http://127.0.0.1:8000/health
- **Metrics**: http://127.0.0.1:8000/metrics

## API Endpoints

### REST API

#### List Agents
```
GET /api/agents
```

Returns list of all agents with their current status.

#### Get Agent Details
```
GET /api/agents/{agent_id}
```

Returns detailed information about a specific agent.

#### Execute Action
```
POST /api/agents/{agent_id}/action
Content-Type: application/json

{
  "action": "pause|resume|stop|restart|prioritize",
  "parameters": {
    "priority": "high"  // For prioritize action
  }
}
```

Available actions:
- **pause**: Pause a running agent
- **resume**: Resume a paused agent
- **stop**: Stop an agent
- **restart**: Restart an agent (resets task counters)
- **prioritize**: Change agent priority

### WebSocket

#### Real-time Updates
```
WS /api/agents/ws
```

Connect to receive real-time updates. Messages are JSON-formatted:

**Snapshot** (sent on connect):
```json
{
  "type": "snapshot",
  "data": [
    {
      "id": "planner-001",
      "name": "Planner Agent",
      "status": "running",
      "tasks_completed": 5,
      "tasks_pending": 2
    }
  ],
  "timestamp": "2024-11-01T12:00:00.000Z"
}
```

**Agent Updated**:
```json
{
  "type": "agent_updated",
  "data": {
    "id": "planner-001",
    "status": "paused"
  },
  "timestamp": "2024-11-01T12:00:00.000Z"
}
```

**Task Events**:
```json
{
  "type": "task_added|task_completed",
  "data": {
    "agent_id": "planner-001",
    "task": "Task description"
  }
}
```

**Log Line**:
```json
{
  "type": "log_line",
  "data": {
    "agent_id": "planner-001",
    "message": "Processing task...",
    "level": "info"
  }
}
```

### Health & Metrics

#### Health Check
```
GET /health
```

Returns server health status.

#### Metrics (Prometheus-compatible)
```
GET /metrics
```

Returns metrics in Prometheus text format.

## Development

### Running Tests

```bash
# Run all tests
pytest tests/test_agents_api.py -v

# Run specific test class
pytest tests/test_agents_api.py::TestAgentsRESTAPI -v

# Run with coverage
pytest tests/test_agents_api.py --cov=web --cov-report=html
```

### Project Structure

```
web/
├── app.py                  # Main FastAPI application
├── routers/
│   ├── __init__.py
│   └── agents.py          # Agents router (REST + WebSocket)
├── static/
│   ├── dashboard.html     # Dashboard UI
│   ├── app.js            # WebSocket client
│   └── index.html        # Legacy interface
└── README.md             # This file
```

## Production Considerations

### Replace In-Memory Store with Redis

The current implementation uses an in-memory store for simplicity. For production with multiple server instances, replace with Redis:

**1. Install Redis client:**
```bash
pip install redis
```

**2. Replace store operations in `web/routers/agents.py`:**

```python
import redis.asyncio as redis

# Initialize Redis
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Replace AgentStore methods:
async def get_all():
    keys = await redis_client.keys("agent:*")
    agents = []
    for key in keys:
        agent_data = await redis_client.hgetall(key)
        agents.append(Agent(**agent_data))
    return agents

async def update_agent(agent_id, updates):
    await redis_client.hset(f"agent:{agent_id}", mapping=updates)
```

**3. Replace WebSocket broadcast with Redis Pub/Sub:**

```python
async def broadcast(message):
    await redis_client.publish("agent_events", message.model_dump_json())

# In a separate coroutine:
async def listen_for_events():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("agent_events")
    async for message in pubsub.listen():
        if message["type"] == "message":
            # Broadcast to local WebSocket connections
            await manager._broadcast_to_local(message["data"])
```

### Security

For production deployment:

1. **Add Authentication**: Implement JWT or OAuth2 authentication
2. **Rate Limiting**: Add rate limiting to API endpoints
3. **CORS Configuration**: Configure CORS for specific origins
4. **HTTPS**: Use HTTPS for WebSocket (WSS) and API endpoints
5. **Input Validation**: Already implemented with Pydantic models

### Scaling

- Use Redis for shared state across multiple server instances
- Deploy behind a load balancer (nginx, HAProxy)
- Use Redis Pub/Sub for WebSocket message distribution
- Consider using a WebSocket gateway (Socket.IO with Redis adapter)

## Troubleshooting

### WebSocket connection fails

- **Check firewall settings**: Ensure port 8000 is accessible
- **Verify server is running**: Check that uvicorn is running without errors
- **Browser console**: Check for JavaScript errors in browser developer tools

### Agent actions not working

- **Check agent status**: Verify the agent is in a valid state for the action
- **Review server logs**: Look for error messages in the terminal
- **Test with curl**: Try executing actions via curl to isolate UI issues

```bash
curl -X POST http://127.0.0.1:8000/api/agents/planner-001/action \
  -H "Content-Type: application/json" \
  -d '{"action":"pause","parameters":{}}'
```

### Performance issues

- **On Linux**: Install uvloop for better async performance: `pip install uvloop`
- **Monitor metrics**: Use `/metrics` endpoint to monitor agent counts
- **Check logs**: Look for warnings about connection limits or resource usage

## Platform-Specific Notes

### Windows 11

- Uses standard asyncio ProactorEventLoop (appropriate for Windows)
- Line endings should be CRLF or LF (Git handles this automatically)
- PowerShell commands use backslashes for paths (handled by pathlib)

### Linux (Arch, Ubuntu, etc.)

- Can use uvloop for ~2x better async performance
- Recommended to install uvloop: `pip install uvloop`
- Line endings should be LF

## Contributing

When contributing to the web interface:

1. Maintain cross-platform compatibility (use pathlib for paths)
2. Test on both Windows and Linux if possible
3. Update tests in `tests/test_agents_api.py`
4. Update this README with new features
5. Follow existing code style and patterns

## License

Same as parent project (MIT License)
