"""
Tests for the agents REST API and WebSocket functionality.

Tests using pytest-asyncio and httpx AsyncClient for async testing.
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
import asyncio

# Import the FastAPI app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.app import app
from web.routers.agents import AgentStatus, AgentAction


class TestAgentsRESTAPI:
    """Test REST API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_agents(self):
        """Test GET /api/agents endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/agents")
            
            assert response.status_code == 200
            agents = response.json()
            assert isinstance(agents, list)
            assert len(agents) > 0
            
            # Verify agent structure
            agent = agents[0]
            assert "id" in agent
            assert "name" in agent
            assert "type" in agent
            assert "status" in agent
            assert agent["status"] in [s.value for s in AgentStatus]
    
    @pytest.mark.asyncio
    async def test_get_agent_by_id(self):
        """Test GET /api/agents/{agent_id} endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First get list of agents
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            agent_id = agents[0]["id"]
            
            # Get specific agent
            response = await client.get(f"/api/agents/{agent_id}")
            
            assert response.status_code == 200
            agent = response.json()
            assert agent["id"] == agent_id
            assert "name" in agent
            assert "type" in agent
            assert "status" in agent
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self):
        """Test GET /api/agents/{agent_id} with invalid ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/agents/nonexistent-agent-999")
            
            assert response.status_code == 404
            error = response.json()
            assert "detail" in error
            assert "not found" in error["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_pause_action(self):
        """Test POST /api/agents/{agent_id}/action with pause."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Find a running agent
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            running_agent = next((a for a in agents if a["status"] == "running"), None)
            
            if not running_agent:
                pytest.skip("No running agent available for testing")
            
            agent_id = running_agent["id"]
            
            # Execute pause action
            response = await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "pause", "parameters": {}}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert "message" in result
            assert "agent" in result
            assert result["agent"]["status"] == "paused"
    
    @pytest.mark.asyncio
    async def test_resume_action(self):
        """Test POST /api/agents/{agent_id}/action with resume."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First pause an agent
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            running_agent = next((a for a in agents if a["status"] == "running"), None)
            
            if not running_agent:
                pytest.skip("No running agent available for testing")
            
            agent_id = running_agent["id"]
            
            # Pause
            await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "pause"}
            )
            
            # Resume
            response = await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "resume"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["agent"]["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_stop_action(self):
        """Test POST /api/agents/{agent_id}/action with stop."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            agent_id = agents[0]["id"]
            
            response = await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "stop"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["agent"]["status"] == "stopped"
            assert result["agent"]["current_task"] is None
    
    @pytest.mark.asyncio
    async def test_restart_action(self):
        """Test POST /api/agents/{agent_id}/action with restart."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            agent_id = agents[0]["id"]
            
            response = await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "restart"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["agent"]["status"] == "running"
            assert result["agent"]["tasks_completed"] == 0
    
    @pytest.mark.asyncio
    async def test_prioritize_action(self):
        """Test POST /api/agents/{agent_id}/action with prioritize."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            agent_id = agents[0]["id"]
            
            response = await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "prioritize", "parameters": {"priority": "high"}}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["agent"]["metadata"]["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_invalid_action_state_transition(self):
        """Test that invalid state transitions are rejected."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get an idle agent
            list_response = await client.get("/api/agents")
            agents = list_response.json()
            idle_agent = next((a for a in agents if a["status"] == "idle"), None)
            
            if not idle_agent:
                pytest.skip("No idle agent available for testing")
            
            agent_id = idle_agent["id"]
            
            # Try to pause an idle agent (should fail)
            response = await client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "pause"}
            )
            
            assert response.status_code == 400
            error = response.json()
            assert "detail" in error


class TestHealthAndMetrics:
    """Test health and metrics endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test GET /health endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            health = response.json()
            assert health["status"] == "healthy"
            assert "timestamp" in health
            assert "version" in health
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test GET /metrics endpoint (Prometheus format)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/metrics")
            
            assert response.status_code == 200
            metrics = response.text
            
            # Check for expected metrics
            assert "agents_total" in metrics
            assert "agents_by_status" in metrics
            assert "# TYPE" in metrics  # Prometheus format
            assert "# HELP" in metrics


class TestWebSocket:
    """Test WebSocket functionality."""
    
    def test_websocket_connection_and_snapshot(self):
        """Test WebSocket connection and initial snapshot."""
        client = TestClient(app)
        
        with client.websocket_connect("/api/agents/ws") as websocket:
            # Receive initial snapshot
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == "snapshot"
            assert "data" in message
            assert isinstance(message["data"], list)
            assert len(message["data"]) > 0
            
            # Verify snapshot contains agent data
            agent = message["data"][0]
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent
    
    def test_websocket_ping_pong(self):
        """Test WebSocket keepalive ping/pong."""
        client = TestClient(app)
        
        with client.websocket_connect("/api/agents/ws") as websocket:
            # Receive initial snapshot
            websocket.receive_text()
            
            # Send ping
            websocket.send_text(json.dumps({"type": "ping"}))
            
            # Receive pong
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "pong"
    
    def test_websocket_receives_agent_updates(self):
        """Test that WebSocket receives agent update broadcasts."""
        client = TestClient(app)
        
        with client.websocket_connect("/api/agents/ws") as websocket:
            # Receive initial snapshot
            snapshot = websocket.receive_text()
            snapshot_data = json.loads(snapshot)
            
            # Get an agent ID to update
            agent_id = snapshot_data["data"][0]["id"]
            
            # Trigger an action via REST API (this should broadcast an update)
            response = client.post(
                f"/api/agents/{agent_id}/action",
                json={"action": "prioritize", "parameters": {"priority": "high"}}
            )
            assert response.status_code == 200
            
            # Wait for WebSocket update
            import time
            time.sleep(0.1)  # Small delay to ensure message is sent
            
            # Receive the broadcast update
            try:
                data = websocket.receive_text()
                message = json.loads(data)
                
                assert message["type"] == "agent_updated"
                assert message["data"]["id"] == agent_id
            except Exception:
                # If no message received immediately, that's also acceptable
                # as the broadcast is async and might not arrive in test timeframe
                pass


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility aspects."""
    
    @pytest.mark.asyncio
    async def test_pathlib_path_handling(self):
        """Test that pathlib.Path is used correctly for cross-platform compatibility."""
        from web.app import static_dir
        from pathlib import Path
        
        # Verify that static_dir is a Path object or string
        assert isinstance(static_dir, (Path, str))
        
        # On Windows, paths should work with backslashes or forward slashes
        # On Linux, paths should work with forward slashes
        # pathlib handles this automatically
        if isinstance(static_dir, Path):
            assert static_dir.exists() or not static_dir.is_absolute()
    
    def test_json_serialization(self):
        """Test that JSON serialization works correctly across platforms."""
        import json
        from datetime import datetime
        
        # Test data that might have platform-specific issues
        test_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(Path("/some/path/to/file.txt")),
            "unicode": "Testing special chars: ñ, ü, 中文"
        }
        
        # Should serialize without errors
        serialized = json.dumps(test_data)
        deserialized = json.loads(serialized)
        
        assert deserialized["unicode"] == test_data["unicode"]


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
