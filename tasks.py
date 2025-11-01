"""
Invoke tasks for agent orchestration and parallel execution.

Usage:
    invoke --list
    invoke run-agents
    invoke run-parallel
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from invoke.tasks import task

from logging_config import get_logger, setup_logging

# Configurar logging
setup_logging()


@task
def install(c):
    """Install dependencies."""
    c.run("pip install -r requirements.txt")


@task
def test(c):
    """Run tests."""
    c.run("python -m pytest")


@task
def clean(c):
    """Clean up temporary files."""
    # Cross-platform cleanup using Python APIs to avoid shell differences.
    import shutil
    from pathlib import Path

    cwd = Path(".")

    # Remove common caches and virtualenvs
    for pattern in [
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".venv",
        ".venv_migration",
        "venv",
        "env",
    ]:
        for p in cwd.rglob(pattern):
            try:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink()
            except Exception:
                pass

    # Clear logs but keep directory
    logs_dir = cwd / "logs"
    if logs_dir.exists() and logs_dir.is_dir():
        for item in logs_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
            except Exception:
                pass


@task
def run_planner(c):
    """Run planner agent."""
    c.run(
        'python -c "from agents.planner import PlannerAgent; agent = PlannerAgent(); agent.execute()"'
    )


@task
def run_executor(c):
    """Run executor agent."""
    c.run(
        'python -c "from agents.executor import ExecutorAgent; agent = ExecutorAgent(); agent.execute()"'
    )


@task
def run_reviewer(c):
    """Run reviewer agent."""
    c.run(
        'python -c "from agents.reviewer import ReviewerAgent; agent = ReviewerAgent(); agent.execute()"'
    )


@task
def run_agents(c):
    """Run all agents sequentially."""
    run_planner(c)
    run_executor(c)
    run_reviewer(c)


@task
def run_parallel(c):
    """Run agents in parallel using ThreadPoolExecutor."""
    logger = get_logger("tasks")
    import subprocess

    logger.info("Iniciando ejecución paralela de agentes")

    agents = [
        (
            "Planner",
            'python -c "from agents.planner import PlannerAgent; agent = PlannerAgent(); agent.execute()"',
        ),
        (
            "Executor",
            'python -c "from agents.executor import ExecutorAgent; agent = ExecutorAgent(); agent.execute()"',
        ),
        (
            "Reviewer",
            'python -c "from agents.reviewer import ReviewerAgent; agent = ReviewerAgent(); agent.execute()"',
        ),
    ]

    def run_agent(name, cmd):
        logger.info(f"Iniciando agente: {name}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Agente {name} completado exitosamente")
                return f"{name}: Success"
            else:
                logger.error(f"Agente {name} falló: {result.stderr}")
                return f"{name}: Failed - {result.stderr}"
        except Exception as e:
            logger.error(f"Error en agente {name}: {e}")
            return f"{name}: Error - {e}"

    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        futures = [executor.submit(run_agent, name, cmd) for name, cmd in agents]
        for future in as_completed(futures):
            result = future.result()
            logger.info(f"Resultado: {result}")

    logger.info("Ejecución paralela completada")


@task
def coordinator_run(c):
    """Run agents using the coordinator."""
    c.run(
        'python -c "from orchestration.coordinator import AgentCoordinator; coord = AgentCoordinator(); coord.execute_workflow()"'
    )


@task
def setup_logs(c):
    """Setup logging directory."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    print(f"Logs directory ready at {log_dir}")


@task
def validate_config(c):
    """Validate agent configuration."""
    config_path = Path("config/agents.config.json")
    if not config_path.exists():
        print("Configuration file not found!")
        return

    with open(config_path) as f:
        config = json.load(f)

    print(f"Project: {config.get('metadata', {}).get('project', 'Unknown')}")
    print(f"Agents: {len(config.get('agents', []))}")

    for agent in config.get("agents", []):
        print(f"- {agent['id']}: {agent.get('defaultModel', 'No model')}")
