"""
Agente Ejecutor - Executor Agent

Este agente se especializa en ejecutar código, integrar con repositorios y correr pruebas unitarias.
Utiliza modelos locales (Ollama) con fallback a proveedores remotos.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, LLM
from .base_agent import BaseAgent


class ExecutorAgent(BaseAgent):
    """Agente ejecutor que implementa código y ejecuta pruebas."""

    def __init__(self, config_path: str = "config/agents.config.json"):
        """Inicializar el agente ejecutor.

        Args:
            config_path: Ruta al archivo de configuración de agentes
        """
        super().__init__(config_path)

    def _get_agent_config(self) -> Dict[str, Any]:
        """Obtener configuración específica del agente ejecutor."""
        agents = self.config.get("agents", [])
        for agent in agents:
            if agent["id"] == "executor":
                return agent
        raise ValueError("Configuración del agente 'executor' no encontrada")

    def create_agent(self) -> Agent:
        """Crear el agente CrewAI para ejecución."""
        return Agent(
            role="Ejecutor de Código",
            goal="Implementar código según especificaciones, ejecutar pruebas y integrar cambios",
            backstory="Soy un agente especializado en desarrollo e implementación de software. "
            "Mi expertise radica en escribir código de alta calidad, ejecutar pruebas automatizadas, "
            "y mantener la integridad de los repositorios de código.",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def execute_task(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar una tarea específica según las especificaciones.

        Args:
            task_spec: Especificación de la tarea con descripción, código, etc.

        Returns:
            Diccionario con resultados de la ejecución
        """
        # Crear prompt personalizado con la especificación de tarea
        task_text = self._format_task_spec(task_spec)

        # Recuperar información relevante usando RAG
        rag_query = f"implementación de código y desarrollo: {task_spec.get('description', '')} {task_spec.get('requirements', '')}"
        relevant_info = self.retrieve_relevant_info(rag_query, k=3)

        # Combinar especificación de tarea con conocimiento recuperado
        combined_context = f"{task_text}\n\n{relevant_info}"

        prompt = self.prompt_template.replace("{{TASK_SPEC}}", combined_context)

        # Crear tarea de ejecución
        execution_task = Task(
            description=prompt,
            expected_output="Resultado de la ejecución con código implementado, pruebas ejecutadas "
            "y estado de integración.",
            agent=self.create_agent(),
        )

        # Crear crew y ejecutar
        crew = Crew(agents=[self.create_agent()], tasks=[execution_task], verbose=True)

        result = crew.kickoff()

        # Procesar resultado y retornar en formato estructurado
        return self._parse_execution_result(result)

    def run_tests(self, test_files: List[str]) -> Dict[str, Any]:
        """Ejecutar pruebas unitarias para archivos específicos.

        Args:
            test_files: Lista de archivos de prueba a ejecutar

        Returns:
            Resultados de las pruebas
        """
        results = {}
        for test_file in test_files:
            try:
                # Ejecutar pruebas usando unittest
                cmd = ["python", "-m", "unittest", test_file, "-v"]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=Path.cwd()
                )

                results[test_file] = {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            except Exception as e:
                results[test_file] = {"success": False, "error": str(e)}

        return {
            "test_results": results,
            "overall_success": all(r.get("success", False) for r in results.values()),
        }

    def integrate_changes(
        self, changes: Dict[str, Any], commit_message: str
    ) -> Dict[str, Any]:
        """Integrar cambios en el repositorio git.

        Args:
            changes: Diccionario con archivos modificados
            commit_message: Mensaje del commit

        Returns:
            Resultado de la integración
        """
        try:
            # Verificar si hay cambios
            result_status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            if not result_status.stdout.strip():
                return {
                    "success": True,
                    "message": "No hay cambios para integrar",
                    "committed": False,
                }

            # Agregar archivos
            subprocess.run(["git", "add", "."], check=True, cwd=Path.cwd())

            # Crear commit
            subprocess.run(
                ["git", "commit", "-m", commit_message], check=True, cwd=Path.cwd()
            )

            return {
                "success": True,
                "message": f"Cambios integrados exitosamente: {commit_message}",
                "committed": True,
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Error en integración git: {e}",
                "committed": False,
            }

    def _format_task_spec(self, task_spec: Dict[str, Any]) -> str:
        """Formatear especificación de tarea para el prompt."""
        formatted = []
        formatted.append(f"**Tarea**: {task_spec.get('title', 'Sin título')}")
        formatted.append(f"**Descripción**: {task_spec.get('description', 'N/A')}")
        formatted.append(f"**Requisitos**: {task_spec.get('requirements', 'N/A')}")
        formatted.append(
            f"**Archivos a modificar**: {', '.join(task_spec.get('files', []))}"
        )

        if "code_changes" in task_spec:
            formatted.append("**Cambios de código**:")
            for change in task_spec["code_changes"]:
                formatted.append(f"- {change}")

        return "\n".join(formatted)

    def _parse_execution_result(self, result) -> Dict[str, Any]:
        """Parsear el resultado de la ejecución en formato estructurado."""
        # Por simplicidad, retornamos el resultado como string por ahora
        # En una implementación completa, podríamos parsear el Markdown
        return {
            "execution_result": str(result),
            "status": "completed",
            "timestamp": "2025-01-01T00:00:00Z",  # Placeholder
        }

    def save_report(
        self, report: Dict[str, Any], output_path: str = "artifacts/execution-report.md"
    ):
        """Guardar el reporte de ejecución en archivo."""
        output_dir = Path(output_path).parent
        output_dir.mkdir(exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Reporte de Ejecución\n\n")
            f.write(f"**Estado**: {report.get('status', 'Desconocido')}\n")
            f.write(f"**Timestamp**: {report.get('timestamp', 'N/A')}\n\n")
            f.write("## Resultados\n\n")
            f.write(report.get("execution_result", "Sin resultados"))

        print(f"Reporte guardado en: {output_path}")

    def execute(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ejecutar la lógica principal del agente ejecutor."""
        if parameters and "planner_result" in parameters:
            # Usar el plan del planner
            planner_result = parameters["planner_result"]
            plan_content = planner_result.get("plan", "")
            tasks = self._parse_plan_to_tasks(plan_content)
            # Ejecutar la primera tarea por simplicidad
            if tasks:
                result = self.execute_task(tasks[0])
            else:
                result = {"status": "error", "message": "No tasks found in plan"}
        else:
            # Sample task for demonstration
            sample_task = {
                "title": "Implementar función de validación",
                "description": "Crear función que valide entrada de usuario",
                "requirements": "Debe retornar True/False, manejar excepciones",
                "files": ["utils/validation.py"],
                "code_changes": ["Agregar función validate_input()", "Incluir pruebas"],
            }
            result = self.execute_task(sample_task)

        self.save_report(result)
        return result

    def _parse_plan_to_tasks(self, plan_content: str) -> List[Dict[str, Any]]:
        """Parsear el plan generado por el planner a tareas ejecutables."""
        # Por simplicidad, extraer líneas que parezcan tareas
        lines = plan_content.split("\n")
        tasks = []
        current_task = None

        for line in lines:
            line = line.strip()
            if line.startswith("## ") or line.startswith("### "):
                # Nueva tarea
                if current_task:
                    tasks.append(current_task)
                title = line[3:].strip()
                current_task = {
                    "title": title,
                    "description": title,
                    "requirements": "Implementar según especificaciones",
                    "files": [],  # Se determinará dinámicamente
                    "code_changes": [title],
                }

        if current_task:
            tasks.append(current_task)

        return tasks

    @property
    def llm(self) -> LLM:
        """Obtener el modelo de lenguaje, inicializándolo si es necesario."""
        if self._llm is None:
            self._llm = self._initialize_llm()
        return self._llm


if __name__ == "__main__":
    # Ejemplo de uso
    executor = ExecutorAgent()

    # Ejemplo de especificación de tarea
    sample_task = {
        "title": "Implementar función de validación",
        "description": "Crear función que valide entrada de usuario",
        "requirements": "Debe retornar True/False, manejar excepciones",
        "files": ["utils/validation.py"],
        "code_changes": ["Agregar función validate_input()", "Incluir pruebas"],
    }

    result = executor.execute_task(sample_task)
    executor.save_report(result)
