import subprocess
import sys
import time
import requests


def wait_for(url, timeout=10.0, interval=0.2):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1.0)
            return r
        except Exception:
            time.sleep(interval)
    raise TimeoutError(f"{url} not available after {timeout}s")


def test_e2e_manager_and_dummy_agent():
    # Start manager (uvicorn) as a subprocess
    mgr_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "web.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--log-level",
        "warning",
    ]

    mgr_proc = subprocess.Popen(mgr_cmd)

    try:
        wait_for("http://127.0.0.1:8000/health", timeout=15)

        # Start dummy agent service which will register to manager
        agent_cmd = [
            sys.executable,
            "-m",
            "agents.mcp_service",
            "--agent-id",
            "planner",
            "--host",
            "0.0.0.0",
            "--port",
            "8100",
            "--manager-url",
            "http://127.0.0.1:8000",
            "--dummy",
        ]

        agent_proc = subprocess.Popen(agent_cmd)

        try:
            # Wait for registration to show up in manager
            start = time.time()
            registered = False
            while time.time() - start < 15:
                r = requests.get(
                    "http://127.0.0.1:8000/api/agent-services", timeout=1.0
                )
                if r.status_code == 200:
                    services = r.json()
                    if any(s.get("id") == "planner" for s in services):
                        registered = True
                        break
                time.sleep(0.5)

            assert registered, "Agent did not register with manager"

            # Execute via manager
            payload = {"parameters": {"task": "hello"}}
            r = requests.post(
                "http://127.0.0.1:8000/api/agent-services/planner/execute",
                json=payload,
                timeout=5,
            )
            assert r.status_code == 200
            assert r.json().get("result", {}).get("dummy") is True

            # Pause agent via manager
            r = requests.post(
                "http://127.0.0.1:8000/api/agent-services/planner/action",
                json={"action": "pause"},
                timeout=5,
            )
            assert r.status_code == 200

            # Execute while paused -> expect 409
            r = requests.post(
                "http://127.0.0.1:8000/api/agent-services/planner/execute",
                json=payload,
                timeout=5,
            )
            assert r.status_code == 409

            # Resume
            r = requests.post(
                "http://127.0.0.1:8000/api/agent-services/planner/action",
                json={"action": "resume"},
                timeout=5,
            )
            assert r.status_code == 200

            # Execute after resume
            r = requests.post(
                "http://127.0.0.1:8000/api/agent-services/planner/execute",
                json=payload,
                timeout=5,
            )
            assert r.status_code == 200

        finally:
            agent_proc.terminate()
            try:
                agent_proc.wait(timeout=5)
            except Exception:
                agent_proc.kill()

    finally:
        mgr_proc.terminate()
        try:
            mgr_proc.wait(timeout=5)
        except Exception:
            mgr_proc.kill()
