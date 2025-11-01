"""Manager router to interact with per-agent MCP-style services.

This provides endpoints that the web UI can call to forward commands to
the agent HTTP services started with `scripts/run-mcp-agents.ps1`.
"""

from typing import Any, Dict, List
from pathlib import Path
import json
import time

from fastapi import APIRouter, HTTPException, Body
import httpx
import asyncio

router = APIRouter(prefix="/api/agent-services", tags=["agent-services"])

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "agents.config.json"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("Config file not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _agent_service_url(
    index: int, host: str = "127.0.0.1", base_port: int = 8100
) -> str:
    return f"http://{host}:{base_port + index}"


@router.get("", response_model=List[Dict[str, Any]])
async def list_services():
    cfg = load_config()
    agents = cfg.get("agents", [])
    services = []

    # Prefer registered services when available
    for i, a in enumerate(agents):
        agent_id = a.get("id")
        registered = REGISTERED_SERVICES.get(agent_id)
        if registered:
            entry = {
                "id": agent_id,
                "description": a.get("description"),
                "entryPoint": a.get("entryPoint"),
                "serviceUrl": registered.get("serviceUrl"),
                "metadata": registered.get("metadata", {}),
                "registered_at": registered.get("registered_at"),
            }
        else:
            # If config provides explicit port, use it for deterministic URL
            cfg_port = a.get("port")
            if cfg_port:
                service_fallback = f"http://127.0.0.1:{cfg_port}"
            else:
                service_fallback = _agent_service_url(i)

            entry = {
                "id": agent_id,
                "description": a.get("description"),
                "entryPoint": a.get("entryPoint"),
                "serviceUrl": service_fallback,
                "metadata": {},
            }
        services.append(entry)

    # Also include any registered services not present in config (edge cases)
    for rid, rinfo in REGISTERED_SERVICES.items():
        if not any(s["id"] == rid for s in services):
            services.append({"id": rid, **rinfo})

    return services


# In-memory registry of services (agent_id -> {serviceUrl, metadata, registered_at})
REGISTERED_SERVICES: Dict[str, Dict[str, Any]] = {}


def _purge_stale(ttl_seconds: int = 30):
    """Remove services not seen within ttl_seconds."""
    now = time.time()
    stale = [
        rid
        for rid, info in REGISTERED_SERVICES.items()
        if now - info.get("registered_at", 0) > ttl_seconds
    ]
    for rid in stale:
        REGISTERED_SERVICES.pop(rid, None)


async def start_registry_cleaner(interval: int = 10, ttl: int = 30):
    """Background task that periodically purges stale registered services."""
    while True:
        _purge_stale(ttl)
        await asyncio.sleep(interval)


@router.post("/{agent_id}/execute")
async def execute_on_agent(agent_id: str, payload: Dict[str, Any]):
    cfg = load_config()
    agents = cfg.get("agents", [])
    idx = next((i for i, a in enumerate(agents) if a.get("id") == agent_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Agent not found in config")

    # Prefer registered service if available
    cfg = load_config()
    agents = cfg.get("agents", [])
    agent_cfg = agents[idx]
    agent_id_cfg = agent_cfg.get("id")
    registered = REGISTERED_SERVICES.get(agent_id_cfg)
    service_url = None
    if registered:
        service_url = registered.get("serviceUrl")

    if service_url:
        url = service_url.rstrip("/") + "/execute"
    else:
        url = _agent_service_url(idx) + "/execute"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json={"parameters": payload})
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Error contacting agent service: {e}"
            )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/{agent_id}/action")
async def action_on_agent(agent_id: str, body: Dict[str, Any]):
    """Forward lifecycle actions to the agent service (pause/resume/stop/restart)"""
    cfg = load_config()
    agents = cfg.get("agents", [])
    idx = next((i for i, a in enumerate(agents) if a.get("id") == agent_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Agent not found in config")

    agent_cfg = agents[idx]
    registered = REGISTERED_SERVICES.get(agent_cfg.get("id"))
    if registered:
        service_url = registered.get("serviceUrl")
        if service_url:
            url = service_url.rstrip("/") + "/action"
        else:
            url = None
    else:
        cfg_port = agent_cfg.get("port")
        if cfg_port:
            url = f"http://127.0.0.1:{cfg_port}/action"
        else:
            url = _agent_service_url(idx) + "/action"

    # fallback if registered service had no serviceUrl
    if not url:
        cfg_port = agent_cfg.get("port")
        if cfg_port:
            url = f"http://127.0.0.1:{cfg_port}/action"
        else:
            url = _agent_service_url(idx) + "/action"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=body)
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Error contacting agent service: {e}"
            )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.get("/{agent_id}/logs")
async def logs_on_agent(agent_id: str, lines: int = 200):
    cfg = load_config()
    agents = cfg.get("agents", [])
    idx = next((i for i, a in enumerate(agents) if a.get("id") == agent_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Agent not found in config")

    agent_cfg = agents[idx]
    registered = REGISTERED_SERVICES.get(agent_cfg.get("id"))
    if registered:
        service_url = registered.get("serviceUrl")
        if service_url:
            url = service_url.rstrip("/") + "/logs"
        else:
            url = None
    else:
        cfg_port = agent_cfg.get("port")
        if cfg_port:
            url = f"http://127.0.0.1:{cfg_port}/logs"
        else:
            url = _agent_service_url(idx) + "/logs"

    # fallback if registered service had no serviceUrl
    if not url:
        cfg_port = agent_cfg.get("port")
        if cfg_port:
            url = f"http://127.0.0.1:{cfg_port}/logs"
        else:
            url = _agent_service_url(idx) + "/logs"

    params = {"lines": lines}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, params=params)
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Error contacting agent service: {e}"
            )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.get("/{agent_id}/status")
async def status_on_agent(agent_id: str):
    cfg = load_config()
    agents = cfg.get("agents", [])
    idx = next((i for i, a in enumerate(agents) if a.get("id") == agent_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Agent not found in config")

    agent_cfg = agents[idx]
    registered = REGISTERED_SERVICES.get(agent_cfg.get("id"))
    if registered:
        service_url = registered.get("serviceUrl")
        url = service_url.rstrip("/") + "/status" if service_url else None
    else:
        cfg_port = agent_cfg.get("port")
        if cfg_port:
            url = f"http://127.0.0.1:{cfg_port}/status"
        else:
            url = _agent_service_url(idx) + "/status"

    if not url:
        cfg_port = agent_cfg.get("port")
        if cfg_port:
            url = f"http://127.0.0.1:{cfg_port}/status"
        else:
            url = _agent_service_url(idx) + "/status"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Error contacting agent service: {e}"
            )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/register")
async def register_service(body: Dict[str, Any]):
    """Register an agent service so manager can route to it.

    Expected body: {"id": "planner", "serviceUrl": "http://127.0.0.1:8100", "metadata": {...}}
    """
    agent_id = body.get("id")
    service_url = body.get("serviceUrl")
    metadata = body.get("metadata", {})
    if not agent_id or not service_url:
        raise HTTPException(status_code=400, detail="Missing id or serviceUrl")

    REGISTERED_SERVICES[agent_id] = {
        "serviceUrl": service_url,
        "metadata": metadata,
        "registered_at": time.time(),
    }

    return {"message": "registered", "agent_id": agent_id}


@router.post("/unregister")
async def unregister_service(body: Dict[str, Any]):
    agent_id = body.get("id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="Missing id")
    REGISTERED_SERVICES.pop(agent_id, None)
    return {"message": "unregistered", "agent_id": agent_id}


@router.post("/heartbeat")
async def heartbeat(body: Dict[str, Any] = Body(...)):
    """Agent services should call this periodically to indicate liveness.

    Body: {"id": "planner", "serviceUrl": "http://127.0.0.1:8100"}
    """
    agent_id = body.get("id")
    service_url = body.get("serviceUrl")
    metadata = body.get("metadata", {})
    if not agent_id:
        raise HTTPException(status_code=400, detail="Missing id")

    entry = REGISTERED_SERVICES.get(agent_id)
    if entry:
        entry["registered_at"] = time.time()
        if service_url:
            entry["serviceUrl"] = service_url
        if metadata:
            entry["metadata"] = metadata
    else:
        # Implicit register if not present
        REGISTERED_SERVICES[agent_id] = {
            "serviceUrl": service_url or "",
            "metadata": metadata,
            "registered_at": time.time(),
        }

    return {"message": "heartbeat accepted", "agent_id": agent_id}
