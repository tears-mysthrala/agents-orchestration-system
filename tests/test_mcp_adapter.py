from fastapi.testclient import TestClient

from agents.mcp_service import create_app


class DummyAgent:
    def __init__(self):
        self.agent_config = {
            "id": "planner",
            "name": "Planner",
            "defaultModel": "test-model",
        }

    def execute(self, params=None):
        # simple deterministic response for tests
        return {"ok": True, "received": params}


def test_mcp_adapter_execute_and_lifecycle():
    agent = DummyAgent()
    app = create_app(agent, manager_url=None, host="127.0.0.1", port=8100)
    client = TestClient(app)

    # health and info
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"

    r = client.get("/info")
    assert r.status_code == 200
    info = r.json()
    assert info["id"] == "planner"

    # execute normally
    payload = {"parameters": {"task": "do-something"}}
    r = client.post("/execute", json=payload)
    assert r.status_code == 200
    assert r.json()["result"]["ok"] is True

    # lifecycle: pause
    r = client.post("/action", json={"action": "pause"})
    assert r.status_code == 200
    assert r.json().get("message") == "paused"

    # execute while paused -> 409
    r = client.post("/execute", json=payload)
    assert r.status_code == 409

    # resume
    r = client.post("/action", json={"action": "resume"})
    assert r.status_code == 200
    assert r.json().get("message") == "resumed"

    # execute after resume -> OK
    r = client.post("/execute", json=payload)
    assert r.status_code == 200
    assert r.json()["result"]["received"]["task"] == "do-something"

    # status endpoint
    r = client.get("/status")
    assert r.status_code == 200
    lifecycle = r.json().get("lifecycle")
    assert lifecycle.get("status") == "running"

    # logs endpoint (best-effort)
    r = client.get("/logs")
    assert r.status_code == 200
    assert isinstance(r.json().get("logs"), list)
