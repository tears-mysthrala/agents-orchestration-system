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
from contextlib import asynccontextmanager
import time
import uvicorn
import asyncio
import requests
import httpx
import threading
from pathlib import Path
import json

# Ensure package imports work when executed from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Agent classes are imported lazily in main() to avoid importing heavy ML/RAG
def _make_lazy_agent(module_path: str, class_name: str):
    def _lazy_factory(config_path: str = "config/agents.config.json"):
        # Import the real agent class only when instantiated
        mod = __import__(module_path, fromlist=[class_name])
        AgentCls = getattr(mod, class_name)
        return AgentCls(config_path=config_path)

    # Return a callable that acts like a class (callable to construct instance)
    return _lazy_factory


AGENT_MAP = {
    "planner": _make_lazy_agent("agents.planner", "PlannerAgent"),
    "executor": _make_lazy_agent("agents.executor", "ExecutorAgent"),
    "reviewer": _make_lazy_agent("agents.reviewer", "ReviewerAgent"),
}


# Use a plain dict body to avoid Pydantic model rebuild issues when importing as module


def create_app(
    agent_instance,
    manager_url: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8100,
    drain_timeout: int = 30,
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
    # Flag indicates a graceful shutdown/restart has been requested. When True,
    # the service should not accept new execute requests and should drain
    # existing work before exiting or restarting.
    app.state._shutdown_requested = False
    # Drain timeout (seconds) used to bound graceful shutdown/restart waiting
    app.state._drain_timeout = int(drain_timeout or 30)

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        """Lifespan context: register with manager and start heartbeat loop."""
        mgr = manager_url
        hb_task = None
        try:
            if mgr:
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

                hb_task = asyncio.create_task(_heartbeat_loop())

            app.state._heartbeat_task = hb_task
            yield
        finally:
            # shutdown: cancel heartbeat and unregister
            try:
                task = app.state._heartbeat_task
                if task:
                    task.cancel()
                    try:
                        await task
                    except Exception:
                        pass

                if mgr:
                    unregister_url = mgr.rstrip("/") + "/api/agent-services/unregister"
                    payload = {"id": app.state._agent_info["id"]}
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(unregister_url, json=payload, timeout=2.0)
                    except Exception:
                        pass
            except Exception:
                pass

    app.router.lifespan_context = _lifespan

    # lifespan takes care of shutdown/unregister

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
            # Respect lifecycle pause/resume/stop
            if app.state._lifecycle.get("status") == "paused":
                raise HTTPException(status_code=409, detail="Agent is paused")
            if (
                app.state._shutdown_requested
                or app.state._lifecycle.get("status") == "stopping"
            ):
                # Reject new work while we're shutting down/restarting
                raise HTTPException(status_code=409, detail="Agent is stopping")

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
            # Request graceful shutdown: set flag and wait for current task to
            # finish before exiting. We return immediately to the caller and
            # perform the blocking wait in a daemon thread so the response is
            # delivered quickly.
            app.state._shutdown_requested = True
            app.state._lifecycle["status"] = "stopping"

            def _drain_and_exit():
                try:
                    # Wait for current task to clear (or timeout after drain_timeout)
                    start = time.time()
                    while True:
                        cur = app.state._lifecycle.get("current_task")
                        if cur is None:
                            break
                        if time.time() - start > app.state._drain_timeout:
                            break
                        time.sleep(0.1)
                finally:
                    # Force exit; use os._exit to avoid complex teardown ordering
                    os._exit(0)

            threading.Thread(target=_drain_and_exit, daemon=True).start()
            return {"message": "stopping"}

        if action == "restart":
            # Graceful restart: mark shutdown requested, wait for current task
            # to finish (with timeout), then execv to replace the process.
            app.state._shutdown_requested = True
            app.state._lifecycle["status"] = "stopping"

            def _drain_and_exec():
                try:
                    start = time.time()
                    while True:
                        cur = app.state._lifecycle.get("current_task")
                        if cur is None:
                            break
                        if time.time() - start > app.state._drain_timeout:
                            break
                        time.sleep(0.1)

                    python = sys.executable
                    args = [python] + sys.argv
                    # Replace the current process image with a new one.
                    os.execv(python, args)
                except Exception:
                    # If execv fails, make sure the process still exits so we
                    # don't leave an unstable service running.
                    try:
                        os._exit(1)
                    except Exception:
                        pass

            threading.Thread(target=_drain_and_exec, daemon=True).start()
            return {"message": "restarting"}

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
    parser.add_argument(
        "--dummy",
        action="store_true",
        help="Run a lightweight dummy agent (no ML/RAG dependencies)",
    )
    args = parser.parse_args()

    agent_id = args.agent_id
    # If requested, run a dummy lightweight agent (no ML/RAG deps)
    if getattr(args, "dummy", False):

        class DummyAgent:
            def __init__(self, aid: str):
                self.agent_config = {
                    "id": aid,
                    "name": f"dummy-{aid}",
                    "defaultModel": "dummy",
                }

            def execute(self, params=None):
                return {"ok": True, "dummy": True, "params": params}

        agent = DummyAgent(agent_id)
    else:
        # Lazy import of real agent classes to avoid importing heavy deps at module import
        try:
            from agents.planner import PlannerAgent
            from agents.executor import ExecutorAgent
            from agents.reviewer import ReviewerAgent
        except Exception as e:
            print(f"Error importing agent classes: {e}")
            raise

        AGENT_MAP.update(
            {
                "planner": PlannerAgent,
                "executor": ExecutorAgent,
                "reviewer": ReviewerAgent,
            }
        )

        AgentCls = AGENT_MAP.get(agent_id)
        if AgentCls is None:
            print(f"Unknown agent id: {agent_id}. Supported: {list(AGENT_MAP.keys())}")
            raise SystemExit(2)

        # Instantiate agent
        agent = AgentCls(config_path=args.config)

    # Determine drain timeout (env var overrides config)
    cfg_path = Path(args.config)
    cfg_drain = None
    try:
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg_drain = cfg.get("runtime", {}).get("drainTimeoutSeconds")
    except Exception:
        cfg_drain = None

    env_drain = os.environ.get("MCP_DRAIN_TIMEOUT")
    try:
        drain_timeout = (
            int(env_drain)
            if env_drain is not None
            else (int(cfg_drain) if cfg_drain is not None else 30)
        )
    except Exception:
        drain_timeout = 30

    app = create_app(
        agent,
        manager_url=getattr(args, "manager_url", None),
        host=(args.host if args.host != "0.0.0.0" else "127.0.0.1"),
        port=args.port,
        drain_timeout=drain_timeout,
    )

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
