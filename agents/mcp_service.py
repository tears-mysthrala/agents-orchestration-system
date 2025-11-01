"""MCP-style adapter service for agents.

This module exposes a simple HTTP API for any agent in `agents/` so they
can be run as independent services (easy to migrate to AI Toolkit / Agent
Boulder). Endpoints:
  - GET /health
  - GET /info
  - POST /execute

Run as: python -m agents.mcp_service --agent-id planner --config config/agents.config.json --port 8101
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
import uvicorn
import asyncio
import requests
import httpx
import threading
from pathlib import Path
import json

# Ensure package imports work when executed from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reviewer import ReviewerAgent


AGENT_MAP = {
    "planner": PlannerAgent,
    "executor": ExecutorAgent,
    "reviewer": ReviewerAgent,
}


# Use a plain dict body to avoid Pydantic model rebuild issues when importing as module


def create_app(
    agent_instance,
    manager_url: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8100,
) -> FastAPI:
    app = FastAPI(
        title=f"Agent Service: {agent_instance.agent_config.get('id', 'unknown')}"
    )

    app.state._agent_info = {
        "id": agent_instance.agent_config.get("id"),
        "metadata": {"defaultModel": agent_instance.agent_config.get("defaultModel")},
        "service_url": f"http://{host}:{port}",
        "manager_url": manager_url,
    }

    # Heartbeat task holder
    app.state._heartbeat_task = None
    app.state._lifecycle = {"status": "running", "current_task": None}

    @app.on_event("startup")
    async def _register_and_start_heartbeat():
        mgr = manager_url
        if not mgr:
            return
        register_url = mgr.rstrip("/") + "/api/agent-services/register"
        hb_url = mgr.rstrip("/") + "/api/agent-services/heartbeat"

        payload = {
            "id": app.state._agent_info["id"],
            "serviceUrl": app.state._agent_info["service_url"],
            "metadata": app.state._agent_info.get("metadata", {}),
        }

        try:
            async with httpx.AsyncClient() as client:
                await client.post(register_url, json=payload, timeout=2.0)
        except Exception:
            print(f"Warning: could not register service to manager at {mgr}")

        async def _heartbeat_loop():
            while True:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(hb_url, json=payload, timeout=2.0)
                except Exception:
                    # Best-effort; ignore failures
                    pass
                await asyncio.sleep(10)

        # start background heartbeat
        app.state._heartbeat_task = asyncio.create_task(_heartbeat_loop())

    @app.on_event("shutdown")
    async def _shutdown_unregister():
        mgr = manager_url
        if not mgr:
            return
        unregister_url = mgr.rstrip("/") + "/api/agent-services/unregister"
        payload = {"id": app.state._agent_info["id"]}

        # cancel heartbeat task
        task = app.state._heartbeat_task
        if task:
            task.cancel()
            try:
                await task
            except Exception:
                pass

        try:
            async with httpx.AsyncClient() as client:
                await client.post(unregister_url, json=payload, timeout=2.0)
        except Exception:
            pass

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/info")
    async def info():
        return {
            "id": agent_instance.agent_config.get("id"),
            "name": agent_instance.agent_config.get("name"),
            "defaultModel": agent_instance.agent_config.get("defaultModel"),
        }

    @app.post("/execute")
    async def execute(req: Dict[str, Any]):
        # Run the agent.execute in a thread to avoid blocking the event loop
        try:
            # Respect lifecycle pause/resume
            if app.state._lifecycle.get("status") == "paused":
                raise HTTPException(status_code=409, detail="Agent is paused")

            params = req.get("parameters", {}) if isinstance(req, dict) else {}
            loop = asyncio.get_running_loop()
            # mark current task
            app.state._lifecycle["current_task"] = params.get("task", "execute")
            result = await loop.run_in_executor(None, agent_instance.execute, params)
            app.state._lifecycle["current_task"] = None
            return {"result": result}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/status")
    async def status():
        return {"lifecycle": app.state._lifecycle}

    @app.post("/action")
    async def action(body: Dict[str, Any]):
        """Lifecycle actions: pause, resume, stop, restart"""
        action = body.get("action")
        if not action:
            raise HTTPException(status_code=400, detail="Missing action")

        if action == "pause":
            app.state._lifecycle["status"] = "paused"
            return {"message": "paused"}

        if action == "resume":
            app.state._lifecycle["status"] = "running"
            return {"message": "resumed"}

        if action == "stop":
            # Best-effort graceful shutdown: return response then exit process
            def _delayed_exit():
                try:
                    # small delay to allow response to be sent
                    threading.Event().wait(0.5)
                finally:
                    os._exit(0)

            threading.Thread(target=_delayed_exit, daemon=True).start()
            return {"message": "stopping"}

        if action == "restart":
            # Best-effort restart using execv; may not work in all environments
            try:
                python = sys.executable
                args = [python] + sys.argv
                threading.Thread(
                    target=lambda: os.execv(python, args), daemon=True
                ).start()
                return {"message": "restarting"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Could not restart: {e}")

        raise HTTPException(status_code=400, detail="Unsupported action")

    @app.get("/logs")
    async def logs(lines: int = 200):
        """Return last N lines from agent log file if present (best-effort)."""
        try:
            # Try to locate log file in config runtime logDirectory
            cfg_path = Path("config") / "agents.config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                log_dir = cfg.get("runtime", {}).get("logDirectory", "logs")
            else:
                log_dir = "logs"

            log_file = Path(log_dir) / f"{agent_instance.agent_config.get('id')}.log"
            if not log_file.exists():
                return {"logs": [], "note": "log file not found"}

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            tail = all_lines[-lines:]
            return {"logs": tail}
        except Exception:
            return {"logs": [], "note": "error reading logs"}

    return app


def main():
    parser = argparse.ArgumentParser(description="Run an agent as a small HTTP service")
    parser.add_argument(
        "--agent-id", required=True, help="Agent id (planner|executor|reviewer)"
    )
    parser.add_argument(
        "--config", default="config/agents.config.json", help="Path to agents config"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8100, help="Port to bind")
    parser.add_argument(
        "--manager-url",
        default="http://127.0.0.1:8000",
        help="URL of the web manager to register this service",
    )
    args = parser.parse_args()

    agent_id = args.agent_id
    AgentCls = AGENT_MAP.get(agent_id)
    if AgentCls is None:
        print(f"Unknown agent id: {agent_id}. Supported: {list(AGENT_MAP.keys())}")
        raise SystemExit(2)

    # Instantiate agent
    agent = AgentCls(config_path=args.config)

    app = create_app(agent)

    # Attempt to register service with the web manager so it can be discovered
    manager_url = getattr(args, "manager_url", None)
    if manager_url:
        try:
            register_url = manager_url.rstrip("/") + "/api/agent-services/register"
            payload = {
                "id": agent_id,
                "serviceUrl": f"http://{args.host if args.host != '0.0.0.0' else '127.0.0.1'}:{args.port}",
                "metadata": {
                    "defaultModel": agent.agent_config.get("defaultModel"),
                },
            }
            # Best-effort registration; don't fail startup if manager unreachable
            requests.post(register_url, json=payload, timeout=2.0)
        except Exception:
            # Log to stdout; uvicorn will handle logging when server starts
            print(f"Warning: could not register service to manager at {manager_url}")

    # Launch uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
