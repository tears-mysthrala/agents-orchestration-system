import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

# Load web.app module from file
module_path = Path(__file__).resolve().parents[1] / "web" / "app.py"
spec = importlib.util.spec_from_file_location("web_app_mod", str(module_path))
if spec is None or spec.loader is None:
    raise SystemExit(f"Could not load module spec from {module_path}")

m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
app = getattr(m, "app")
client = TestClient(app)

# Register a fake agent service
payload = {
    "id": "planner",
    "serviceUrl": "http://127.0.0.1:8100",
    "metadata": {"defaultModel": "llama3.2:latest"},
}
resp = client.post("/api/agent-services/register", json=payload)
print("status:", resp.status_code)
print(resp.json())

# List services and print first matching planner
resp2 = client.get("/api/agent-services")
print("list status:", resp2.status_code)
print(resp2.json())
