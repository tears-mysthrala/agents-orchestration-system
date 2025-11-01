"""API web para controlar y monitorizar agentes.

Proporciona endpoints para:
- Listar agentes
- Ver estado de agentes
- Ejecutar agentes y workflows
- Gestionar configuración de agentes
- Real-time updates via WebSocket
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from orchestration.coordinator import AgentCoordinator

    coordinator = AgentCoordinator()
except ImportError as e:
    logger.warning(
        f"Could not import AgentCoordinator: {e}. Some features may be unavailable."
    )
    coordinator = None

from web.routers import agents as agents_router
from web.routers import manager as manager_router

app = FastAPI(title="Agentes Orchestration Web Interface", version="1.0.0")

# Include real-time agents router
app.include_router(agents_router.router)
# Include manager router to forward requests to per-agent services (MCP-style)
app.include_router(manager_router.router)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks such as registry cleaner for agent services."""
    task = None
    try:
        # Start the registry cleaner from manager router
        import web.routers.manager as manager_module

        # Create a background task; it will run until application shutdown
        import asyncio

        task = asyncio.create_task(manager_module.start_registry_cleaner())
        yield
    except Exception:
        logger.exception("Failed to start registry cleaner background task")
        yield
    finally:
        try:
            # Cancel the background task on shutdown
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except BaseException:
                    # Suppress CancelledError and other shutdown-related exceptions
                    pass
        except Exception:
            pass


app.router.lifespan_context = lifespan


# Path al archivo de configuración
CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.config.json"


def load_config() -> Dict[str, Any]:
    """Carga la configuración de agentes."""
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail="Config file not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict[str, Any]):
    """Guarda la configuración de agentes."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint (Prometheus-compatible format).

    In production, consider using prometheus_client library for proper metrics.
    """
    agents = await agents_router.store.get_all()

    metrics_text = f"""# HELP agents_total Total number of agents
# TYPE agents_total gauge
agents_total {len(agents)}

# HELP agents_by_status Number of agents by status
# TYPE agents_by_status gauge
"""

    status_counts = {}
    for agent in agents:
        status_counts[agent.status.value] = status_counts.get(agent.status.value, 0) + 1

    for status, count in status_counts.items():
        metrics_text += f'agents_by_status{{status="{status}"}} {count}\n'

    return metrics_text


@app.get("/")
async def root():
    """Sirve la interfaz web principal."""
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    # Fallback to old index.html if dashboard doesn't exist yet
    return FileResponse("web/static/index.html")


@app.get("/api/agents")
async def get_agents():
    """Lista todos los agentes configurados."""
    config = load_config()
    return {"agents": config.get("agents", [])}


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Obtiene detalles de un agente específico."""
    config = load_config()
    agents = config.get("agents", [])
    agent = next((a for a in agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.post("/api/agents")
async def add_agent(agent: Dict[str, Any]):
    """Añade un nuevo agente a la configuración."""
    config = load_config()
    agents = config.get("agents", [])
    # Verificar que no exista ya
    if any(a["id"] == agent["id"] for a in agents):
        raise HTTPException(status_code=400, detail="Agent ID already exists")
    agents.append(agent)
    config["agents"] = agents
    save_config(config)
    return {"message": "Agent added successfully"}


@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, agent: Dict[str, Any]):
    """Actualiza un agente existente."""
    config = load_config()
    agents = config.get("agents", [])
    for i, a in enumerate(agents):
        if a["id"] == agent_id:
            agents[i] = agent
            save_config(config)
            return {"message": "Agent updated successfully"}
    raise HTTPException(status_code=404, detail="Agent not found")


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Elimina un agente de la configuración."""
    config = load_config()
    agents = config.get("agents", [])
    agents = [a for a in agents if a["id"] != agent_id]
    config["agents"] = agents
    save_config(config)
    return {"message": "Agent deleted successfully"}


@app.get("/api/workflows")
async def get_workflows():
    """Lista los workflows configurados."""
    config = load_config()
    workflows = config.get("workflow", [])
    projects = config.get("projects", [])

    # Convertir proyectos a formato workflow para la UI
    project_workflows = []
    for project in projects:
        project_workflows.append(
            {
                "from": "project",
                "to": project["id"],
                "artifact": project["name"],
                "type": "project",
                "project": project,
            }
        )

    return {"workflows": workflows + project_workflows}


@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):
    """Ejecuta un workflow completo."""
    if coordinator is None:
        raise HTTPException(
            status_code=503,
            detail="Coordinator not available. Install required dependencies.",
        )

    try:
        config = load_config()

        # Verificar si es un proyecto
        projects = config.get("projects", [])
        project = next((p for p in projects if p["id"] == workflow_id), None)

        if project:
            # Es un proyecto, ejecutar con sus parámetros
            parameters = {
                "markdown": project["markdown"],
                "base_path": project["base_path"],
                "project_id": project["id"],
            }

            execution = coordinator.execute_workflow(
                workflow_id=workflow_id, parameters=parameters
            )

            # Actualizar status del proyecto
            for p in projects:
                if p["id"] == workflow_id:
                    p["status"] = "running"
                    p["execution_id"] = execution.workflow_id
                    break
            save_config(config)

            return {
                "message": f"Project '{project['name']}' workflow execution started",
                "execution_id": execution.workflow_id,
            }
        else:
            # Es un workflow estándar
            execution = coordinator.execute_workflow(workflow_id=workflow_id)
            return {
                "message": f"Workflow {workflow_id} execution started",
                "execution_id": execution.workflow_id,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/new")
async def create_new_project(project: Dict[str, Any]):
    """Crear y ejecutar un nuevo proyecto basado en especificaciones."""
    if coordinator is None:
        raise HTTPException(
            status_code=503,
            detail="Coordinator not available. Install required dependencies.",
        )

    try:
        markdown = project.get("markdown", "")
        base_path = project.get("base_path", "")
        name = project.get("name", f"Proyecto {int(time.time())}")

        if not markdown:
            raise HTTPException(
                status_code=400, detail="Markdown specifications are required"
            )

        # Cargar config
        config = load_config()
        if "projects" not in config:
            config["projects"] = []

        # Crear ID único para el proyecto
        project_id = f"project_{int(time.time())}"

        # Guardar proyecto en config
        new_project = {
            "id": project_id,
            "name": name,
            "markdown": markdown,
            "base_path": base_path,
            "created_at": datetime.now().isoformat(),
            "status": "created",
        }
        config["projects"].append(new_project)
        save_config(config)

        # Crear workflow personalizado con parámetros
        parameters = {
            "markdown": markdown,
            "base_path": base_path,
            "project_id": project_id,
        }

        execution = coordinator.execute_workflow(
            workflow_id=project_id, parameters=parameters
        )

        # Actualizar status del proyecto
        for p in config["projects"]:
            if p["id"] == project_id:
                p["status"] = "running"
                p["execution_id"] = execution.workflow_id
                break
        save_config(config)

        return {
            "message": f"New project '{name}' created and workflow started",
            "project_id": project_id,
            "execution_id": execution.workflow_id,
            "parameters": parameters,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Montar archivos estáticos usando pathlib para compatibilidad Windows/Unix
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Example of handling blocking calls with run_in_executor
async def run_blocking_task(func, *args):
    """Run a blocking function in a thread pool executor.

    Example usage for CPU-bound or blocking I/O operations:
        result = await run_blocking_task(some_blocking_function, arg1, arg2)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting web server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
