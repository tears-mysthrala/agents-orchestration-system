from fastapi.testclient import TestClient
import importlib.util
from pathlib import Path

# Import the mcp_service module directly from file to avoid package import issues
module_path = Path(__file__).resolve().parents[1] / "agents" / "mcp_service.py"
spec = importlib.util.spec_from_file_location("mcp_service_mod", str(module_path))
if spec is None or spec.loader is None:
    raise SystemExit(f"Could not load module spec from {module_path}")

m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
AGENT_MAP = m.AGENT_MAP
create_app = m.create_app

AgentCls = AGENT_MAP.get("planner")
if AgentCls is None:
    raise SystemExit("planner agent class not found in AGENT_MAP")

agent = AgentCls(config_path="config/agents.config.json")
app = create_app(agent)
client = TestClient(app)

print("GET /health ->", client.get("/health").json())
print("GET /info ->", client.get("/info").json())

# Simple execute call with empty parameters
resp = client.post("/execute", json={"parameters": {}})
print("POST /execute status:", resp.status_code)
print("POST /execute json:", resp.json())
