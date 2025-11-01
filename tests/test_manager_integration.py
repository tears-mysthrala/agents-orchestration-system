from types import SimpleNamespace
import httpx
from fastapi.testclient import TestClient

from web.app import app as manager_app


def _make_fake_client_behavior():
    state = {"paused": False}

    async def fake_post(self, url, json=None, timeout=None):
        # simple routing by URL suffix
        if url.endswith("/execute"):
            # respect paused state
            if state["paused"]:
                return SimpleNamespace(
                    status_code=409,
                    text="Agent paused",
                    json=lambda: {"detail": "Agent is paused"},
                )
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {
                    "result": {"ok": True, "received": json.get("parameters")}
                },
            )

        if url.endswith("/action"):
            action = (json or {}).get("action")
            if action == "pause":
                state["paused"] = True
                return SimpleNamespace(
                    status_code=200, text="", json=lambda: {"message": "paused"}
                )
            if action == "resume":
                state["paused"] = False
                return SimpleNamespace(
                    status_code=200, text="", json=lambda: {"message": "resumed"}
                )
            if action in ("stop", "restart"):
                return SimpleNamespace(
                    status_code=200, text="", json=lambda: {"message": action}
                )

        if (
            url.endswith("/register")
            or url.endswith("/heartbeat")
            or url.endswith("/unregister")
        ):
            return SimpleNamespace(
                status_code=200, text="", json=lambda: {"message": "ok"}
            )

        return SimpleNamespace(status_code=404, text="not found", json=lambda: {})

    async def fake_get(self, url, params=None, timeout=None):
        if url.endswith("/logs"):
            lines = int(params.get("lines", 200)) if params else 200
            logs = [f"line {i}" for i in range(max(0, 100 - lines), 100)]
            return SimpleNamespace(
                status_code=200, text="", json=lambda: {"logs": logs}
            )
        if url.endswith("/status"):
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"lifecycle": {"status": "running", "current_task": None}},
            )
        return SimpleNamespace(status_code=404, text="not found", json=lambda: {})

    return fake_post, fake_get


def test_manager_forwards_to_agent(monkeypatch):
    fake_post, fake_get = _make_fake_client_behavior()

    # Patch httpx.AsyncClient.post and get to our fakes
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    client = TestClient(manager_app)

    # Register agent (manager stores it)
    reg = {"id": "planner", "serviceUrl": "http://127.0.0.1:8100", "metadata": {}}
    r = client.post("/api/agent-services/register", json=reg)
    assert r.status_code == 200

    # Execute via manager -> forwarded
    payload = {"task": "do-stuff"}
    r = client.post("/api/agent-services/planner/execute", json=payload)
    assert r.status_code == 200
    assert r.json()["result"]["ok"] is True

    # Pause via manager
    r = client.post("/api/agent-services/planner/action", json={"action": "pause"})
    assert r.status_code == 200
    assert r.json().get("message") == "paused"

    # Execute while paused -> manager should surface 409
    r = client.post("/api/agent-services/planner/execute", json=payload)
    assert r.status_code == 409

    # Resume
    r = client.post("/api/agent-services/planner/action", json={"action": "resume"})
    assert r.status_code == 200

    # Execute after resume
    r = client.post("/api/agent-services/planner/execute", json=payload)
    assert r.status_code == 200

    # Logs via manager
    r = client.get("/api/agent-services/planner/logs?lines=10")
    assert r.status_code == 200
    assert isinstance(r.json().get("logs"), list)
