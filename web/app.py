"""
API web para controlar y monitorizar agentes.

Proporciona endpoints para:
- Listar agentes
- Ver estado de agentes
- Ejecutar agentes y workflows
- Gestionar configuración de agentes
- WebSocket en tiempo real para monitoreo de agentes
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import logging
from typing import Dict, Any
from pathlib import Path
import os
import sys
import time
from datetime import datetime

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.coordinator import AgentCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentes Orchestration Web Interface",
    version="1.0.0",
    description="Real-time agent orchestration and monitoring system"
)

# Path al archivo de configuración
CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.config.json"

# Instancia del coordinador
coordinator = AgentCoordinator()


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
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "agents-orchestration-system"
    }


@app.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint.
    
    Returns minimal metrics. For production, consider using Prometheus client
    to expose detailed metrics about agent performance, task queues, etc.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time(),
        "metrics": {
            "requests_total": 0,  # TODO: Implement request counter
            "agents_active": 0,   # TODO: Query from agent_store
            "tasks_queued": 0     # TODO: Query from task queue
        }
    }


@app.get("/")
async def root():
    """Sirve la interfaz web principal."""
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


# Import and register the agents router
from web.routers import agents

app.include_router(agents.router)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Agents Orchestration System...")
    
    # Initialize demo agents for testing
    await agents.initialize_demo_agents()
    
    logger.info("Application startup complete")


# Note: Async/Blocking Model Integration
# =======================================
# When integrating with model providers (Ollama, GitHub Models, etc.):
#
# 1. For synchronous/blocking SDK calls, use run_in_executor:
#    ```python
#    import asyncio
#    loop = asyncio.get_event_loop()
#    result = await loop.run_in_executor(None, blocking_ollama_call, prompt)
#    ```
#
# 2. For async-native SDKs, call directly:
#    ```python
#    result = await async_model_call(prompt)
#    ```
#
# 3. Always avoid blocking calls in the main event loop to maintain responsiveness
#    of the WebSocket connections and REST API.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
