"""
Módulo de orquestación para coordinar la ejecución de agentes.

Este módulo proporciona:
- Coordinador de agentes con lógica de flujo de trabajo
- Programador para ejecuciones automáticas
- Manejo de estados y dependencias entre agentes
"""

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from agents.executor import ExecutorAgent
from agents.planner import PlannerAgent
from agents.reviewer import ReviewerAgent
from logging_config import (get_logger, log_agent_action, log_error,
                            log_execution_end, log_execution_start,
                            setup_logging)

# Configurar logging al importar el módulo
setup_logging()


class ExecutionState(Enum):
    """Estados posibles de ejecución de un workflow."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(Enum):
    """Tipos de agentes disponibles."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"


@dataclass
class WorkflowStep:
    """Representa un paso en el workflow de agentes."""

    agent_type: AgentType
    depends_on: Optional[List[AgentType]] = None
    timeout: int = 300  # 5 minutos por defecto
    retry_count: int = 1
    parameters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class WorkflowExecution:
    """Representa la ejecución de un workflow completo."""

    workflow_id: str
    steps: Dict[AgentType, WorkflowStep]
    state: ExecutionState = ExecutionState.PENDING
    results: Dict[AgentType, Any] = None  # type: ignore
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: Dict[AgentType, str] = None  # type: ignore

    def __post_init__(self):
        if self.results is None:
            self.results = {}
        if self.errors is None:
            self.errors = {}


class AgentCoordinator:
    """
    Coordinador principal para la ejecución de agentes.

    Gestiona el flujo de trabajo entre Planner, Executor y Reviewer,
    incluyendo dependencias, reintentos y manejo de errores.
    """

    def __init__(self, config_path: str = "config/agents.config.json"):
        self.config_path = config_path
        self.logger = get_logger("coordinator")

        # Instancias de agentes
        self.agents = {
            AgentType.PLANNER: PlannerAgent(config_path),
            AgentType.EXECUTOR: ExecutorAgent(config_path),
            AgentType.REVIEWER: ReviewerAgent(config_path),
        }

        # Scheduler para ejecuciones programadas
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Historial de ejecuciones
        self.execution_history: List[WorkflowExecution] = []

    def create_standard_workflow(self) -> Dict[AgentType, WorkflowStep]:
        """
        Crea el workflow estándar: Planner -> Executor -> Reviewer.

        Returns:
            Dict[AgentType, WorkflowStep]: Pasos del workflow configurados
        """
        return {
            AgentType.PLANNER: WorkflowStep(
                agent_type=AgentType.PLANNER,
                depends_on=[],
                timeout=180,  # 3 minutos para planning
                retry_count=2,
            ),
            AgentType.EXECUTOR: WorkflowStep(
                agent_type=AgentType.EXECUTOR,
                depends_on=[AgentType.PLANNER],
                timeout=600,  # 10 minutos para ejecución
                retry_count=1,
            ),
            AgentType.REVIEWER: WorkflowStep(
                agent_type=AgentType.REVIEWER,
                depends_on=[AgentType.EXECUTOR],
                timeout=300,  # 5 minutos para revisión
                retry_count=2,
            ),
        }

    def execute_workflow(
        self,
        workflow_id: Optional[str] = None,
        custom_steps: Optional[Dict[AgentType, WorkflowStep]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Ejecuta un workflow completo de agentes.

        Args:
            workflow_id: ID único para el workflow (generado si no se proporciona)
            custom_steps: Pasos personalizados (usa estándar si no se proporciona)
            parameters: Parámetros adicionales para pasar a los agentes

        Returns:
            WorkflowExecution: Resultado de la ejecución completa
        """
        if workflow_id is None:
            workflow_id = f"workflow_{int(time.time())}"

        steps = custom_steps or self.create_standard_workflow()

        execution = WorkflowExecution(
            workflow_id=workflow_id, steps=steps, start_time=datetime.now()
        )

        log_execution_start(self.logger, workflow_id, agent_count=len(steps))

        try:
            execution.state = ExecutionState.RUNNING

            # Ejecutar pasos en orden considerando dependencias
            completed_steps = set()

            for step_type, step in steps.items():
                # Verificar dependencias
                dependencies = step.depends_on or []
                if not all(dep in completed_steps for dep in dependencies):
                    execution.errors[step_type] = (
                        f"Dependencias no satisfechas: {step.depends_on}"
                    )
                    execution.state = ExecutionState.FAILED
                    break

                # Ejecutar paso con reintentos
                success = self._execute_step_with_retry(
                    execution, step_type, step, parameters
                )

                if success:
                    completed_steps.add(step_type)
                    # Acumular resultado para siguientes agentes
                    if parameters is None:
                        parameters = {}
                    parameters[f"{step_type.value}_result"] = execution.results[
                        step_type
                    ]
                    log_agent_action(
                        self.logger,
                        step_type.value,
                        "completed",
                        execution_id=workflow_id,
                    )
                else:
                    execution.state = ExecutionState.FAILED
                    log_error(
                        self.logger,
                        Exception(f"Paso {step_type.value} falló"),
                        execution_id=workflow_id,
                    )
                    break

            if execution.state == ExecutionState.RUNNING:
                execution.state = ExecutionState.COMPLETED
                log_execution_end(
                    self.logger,
                    workflow_id,
                    "success",
                    completed_steps=len(completed_steps),
                )

        except Exception as e:
            execution.state = ExecutionState.FAILED
            execution.errors[AgentType.PLANNER] = (
                f"Error general del workflow: {str(e)}"
            )
            log_error(self.logger, e, execution_id=workflow_id)

        finally:
            execution.end_time = datetime.now()
            self.execution_history.append(execution)

        return execution

    def _execute_step_with_retry(
        self,
        execution: WorkflowExecution,
        step_type: AgentType,
        step: WorkflowStep,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ejecuta un paso con lógica de reintentos.

        Args:
            execution: Ejecución del workflow
            step_type: Tipo de agente a ejecutar
            step: Configuración del paso

        Returns:
            bool: True si el paso se completó exitosamente
        """
        agent = self.agents[step_type]
        last_error = None

        for attempt in range(step.retry_count + 1):
            try:
                log_agent_action(
                    self.logger,
                    step_type.value,
                    f"starting_attempt_{attempt + 1}",
                    execution_id=execution.workflow_id,
                )

                # Ejecutar agente con timeout
                result = self._execute_agent_with_timeout(
                    agent, step.timeout, step.parameters or parameters
                )

                execution.results[step_type] = result
                log_agent_action(
                    self.logger,
                    step_type.value,
                    "success",
                    execution_id=execution.workflow_id,
                    attempt=attempt + 1,
                )
                return True

            except Exception as e:
                last_error = str(e)
                log_error(
                    self.logger,
                    e,
                    execution_id=execution.workflow_id,
                    agent=step_type.value,
                    attempt=attempt + 1,
                )

                if attempt < step.retry_count:
                    time.sleep(2**attempt)  # Exponential backoff

        # Todos los intentos fallaron
        execution.errors[step_type] = (
            f"Falló después de {step.retry_count + 1} intentos. Último error: {last_error}"
        )
        return False

    def _execute_agent_with_timeout(
        self, agent, timeout: int, parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Ejecuta un agente con timeout.

        Args:
            agent: Instancia del agente
            timeout: Timeout en segundos
            parameters: Parámetros para pasar al agente

        Returns:
            Resultado de la ejecución del agente
        """
        # Para esta implementación simplificada, asumimos que los agentes
        # tienen un método execute() que retorna el resultado
        # En una implementación real, esto debería manejar timeouts apropiadamente
        return agent.execute(parameters)

    def schedule_workflow(
        self,
        cron_expression: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        workflow_id_prefix: str = "scheduled",
    ) -> str:
        """
        Programa la ejecución periódica de un workflow.

        Args:
            cron_expression: Expresión cron para scheduling (ej: "0 */2 * * *")
            interval_minutes: Intervalo en minutos (alternativo a cron)
            workflow_id_prefix: Prefijo para IDs de workflows programados

        Returns:
            str: ID del job programado
        """

        def scheduled_execution():
            workflow_id = f"{workflow_id_prefix}_{int(time.time())}"
            self.execute_workflow(workflow_id)

        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression)
        elif interval_minutes:
            trigger = IntervalTrigger(minutes=interval_minutes)
        else:
            raise ValueError("Debe proporcionar cron_expression o interval_minutes")

        job = self.scheduler.add_job(
            scheduled_execution,
            trigger=trigger,
            id=f"{workflow_id_prefix}_job",
            replace_existing=True,
        )

        self.logger.info(f"Workflow programado: {job.id}")
        return job.id

    def get_execution_history(self, limit: int = 10) -> List[WorkflowExecution]:
        """
        Obtiene el historial de ejecuciones recientes.

        Args:
            limit: Número máximo de ejecuciones a retornar

        Returns:
            List[WorkflowExecution]: Historial de ejecuciones
        """
        return self.execution_history[-limit:]

    def cancel_scheduled_job(self, job_id: str) -> bool:
        """
        Cancela un job programado.

        Args:
            job_id: ID del job a cancelar

        Returns:
            bool: True si se canceló exitosamente
        """
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Job {job_id} cancelado")
            return True
        except Exception as e:
            self.logger.error(f"Error cancelando job {job_id}: {str(e)}")
            return False

    def shutdown(self):
        """Detiene el scheduler y libera recursos."""
        self.scheduler.shutdown()
        self.logger.info("Coordinator shutdown complete")


# Funciones de utilidad para uso directo
def run_standard_workflow(
    config_path: str = "config/agents.config.json",
) -> WorkflowExecution:
    """
    Ejecuta el workflow estándar de agentes.

    Args:
        config_path: Ruta al archivo de configuración

    Returns:
        WorkflowExecution: Resultado de la ejecución
    """
    coordinator = AgentCoordinator(config_path)
    try:
        return coordinator.execute_workflow()
    finally:
        coordinator.shutdown()


def schedule_daily_workflow(
    hour: int = 9, minute: int = 0, config_path: str = "config/agents.config.json"
) -> str:
    """
    Programa ejecución diaria del workflow.

    Args:
        hour: Hora del día (0-23)
        minute: Minuto de la hora (0-59)
        config_path: Ruta al archivo de configuración

    Returns:
        str: ID del job programado
    """
    coordinator = AgentCoordinator(config_path)
    cron_expression = f"{minute} {hour} * * *"
    return coordinator.schedule_workflow(cron_expression=cron_expression)
