"""
Agente Revisor - Reviewer Agent

Este agente se especializa en revisar código implementado, evaluar rendimiento y sugerir mejoras.
Utiliza modelos locales (Ollama) con fallback a proveedores remotos.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, LLM
from .base_agent import BaseAgent


class ReviewerAgent(BaseAgent):
    """Agente revisor que evalúa código y sugiere mejoras."""

    def __init__(self, config_path: str = "config/agents.config.json"):
        """Inicializar el agente revisor.

        Args:
            config_path: Ruta al archivo de configuración de agentes
        """
        super().__init__(config_path)

    def _get_agent_config(self) -> Dict[str, Any]:
        """Obtener configuración específica del agente revisor."""
        agents = self.config.get("agents", [])
        for agent in agents:
            if agent["id"] == "reviewer":
                return agent
        raise ValueError("Configuración del agente 'reviewer' no encontrada")

    def create_agent(self) -> Agent:
        """Crear el agente CrewAI para revisión."""
        return Agent(
            role="Revisor de Código",
            goal="Evaluar calidad del código, identificar problemas y sugerir mejoras",
            backstory="Soy un agente especializado en revisión de código y análisis de calidad. "
            "Mi expertise radica en identificar bugs, problemas de rendimiento, violaciones de estándares, "
            "y oportunidades de optimización para mejorar la calidad y mantenibilidad del código.",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def review_code(self, code_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Revisar cambios de código y generar reporte de revisión.

        Args:
            code_changes: Diccionario con cambios de código, archivos modificados, etc.

        Returns:
            Diccionario con el reporte de revisión
        """
        # Crear prompt personalizado con los cambios de código
        changes_text = self._format_code_changes(code_changes)
        prompt = self.prompt_template.replace("{{CODE_CHANGES}}", changes_text)

        # Crear tarea de revisión
        review_task = Task(
            description=prompt,
            expected_output="Análisis completo de revisión con problemas identificados, "
            "sugerencias de mejora y evaluación de calidad.",
            agent=self.create_agent(),
        )

        # Crear crew y ejecutar
        crew = Crew(agents=[self.create_agent()], tasks=[review_task], verbose=True)

        result = crew.kickoff()

        # Procesar resultado y retornar en formato estructurado
        return self._parse_review_result(result)

    def analyze_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar métricas de rendimiento y sugerir optimizaciones.

        Args:
            metrics: Diccionario con métricas de rendimiento

        Returns:
            Análisis de rendimiento con sugerencias
        """
        # Crear prompt para análisis de rendimiento
        metrics_text = self._format_metrics(metrics)
        performance_prompt = f"""
Analiza las siguientes métricas de rendimiento y sugiere optimizaciones:

{metrics_text}

Proporciona:
- Evaluación del rendimiento actual
- Cuellos de botella identificados
- Sugerencias específicas de optimización
- Métricas objetivo recomendadas
"""

        # Crear tarea de análisis
        analysis_task = Task(
            description=performance_prompt,
            expected_output="Análisis detallado de rendimiento con recomendaciones específicas.",
            agent=self.create_agent(),
        )

        # Crear crew y ejecutar
        crew = Crew(agents=[self.create_agent()], tasks=[analysis_task], verbose=True)

        result = crew.kickoff()

        return {
            "performance_analysis": str(result),
            "status": "analyzed",
            "timestamp": "2025-01-01T00:00:00Z",
        }

    def run_linting(self, files: List[str]) -> Dict[str, Any]:
        """Ejecutar análisis de linting en archivos específicos.

        Args:
            files: Lista de archivos a analizar

        Returns:
            Resultados del linting
        """
        results = {}
        for file_path in files:
            try:
                # Ejecutar flake8 o similar (asumiendo que está disponible)
                result = subprocess.run(
                    ["python", "-m", "flake8", "--max-line-length=100", file_path],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd(),
                )

                results[file_path] = {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            except FileNotFoundError:
                results[file_path] = {
                    "success": False,
                    "error": "Linter no disponible (instalar flake8)",
                }
            except Exception as e:
                results[file_path] = {"success": False, "error": str(e)}

        return {
            "lint_results": results,
            "overall_success": all(r.get("success", False) for r in results.values()),
        }

    def validate_standards(
        self, code_changes: Dict[str, Any], standards: List[str]
    ) -> Dict[str, Any]:
        """Validar cumplimiento de estándares de código.

        Args:
            code_changes: Cambios de código a validar
            standards: Lista de estándares a verificar

        Returns:
            Validación de estándares
        """
        # Crear prompt para validación de estándares
        standards_text = "\n".join(f"- {std}" for std in standards)
        changes_text = self._format_code_changes(code_changes)

        validation_prompt = f"""
Valida el cumplimiento de los siguientes estándares en los cambios de código:

Estándares:
{standards_text}

Cambios de código:
{changes_text}

Proporciona:
- Cumplimiento por estándar
- Violaciones identificadas
- Recomendaciones para cumplimiento
"""

        # Crear tarea de validación
        validation_task = Task(
            description=validation_prompt,
            expected_output="Evaluación detallada del cumplimiento de estándares.",
            agent=self.create_agent(),
        )

        # Crear crew y ejecutar
        crew = Crew(agents=[self.create_agent()], tasks=[validation_task], verbose=True)

        result = crew.kickoff()

        return {
            "standards_validation": str(result),
            "status": "validated",
            "timestamp": "2025-01-01T00:00:00Z",
        }

    def _format_code_changes(self, changes: Dict[str, Any]) -> str:
        """Formatear cambios de código para el prompt."""
        formatted = []
        formatted.append(
            f"**Archivos modificados**: {', '.join(changes.get('files', []))}"
        )
        formatted.append(f"**Tipo de cambios**: {changes.get('change_type', 'N/A')}")

        if "diff" in changes:
            formatted.append("**Diff**:")
            formatted.append(f"```\n{changes['diff']}\n```")

        if "new_code" in changes:
            formatted.append("**Código nuevo**:")
            formatted.append(f"```\n{changes['new_code']}\n```")

        return "\n".join(formatted)

    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Formatear métricas para el prompt."""
        formatted = []
        for key, value in metrics.items():
            formatted.append(f"- {key}: {value}")
        return "\n".join(formatted)

    def _parse_review_result(self, result) -> Dict[str, Any]:
        """Parsear el resultado de la revisión en formato estructurado."""
        # Por simplicidad, retornamos el resultado como string por ahora
        # En una implementación completa, podríamos parsear el Markdown
        return {
            "review_report": str(result),
            "status": "reviewed",
            "timestamp": "2025-01-01T00:00:00Z",  # Placeholder
        }

    def save_review_report(
        self, review: Dict[str, Any], output_path: str = "artifacts/review-report.md"
    ):
        """Guardar el reporte de revisión en archivo."""
        output_dir = Path(output_path).parent
        output_dir.mkdir(exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Reporte de Revisión\n\n")
            f.write(f"**Estado**: {review.get('status', 'Desconocido')}\n")
            f.write(f"**Timestamp**: {review.get('timestamp', 'N/A')}\n\n")
            f.write("## Resultados de Revisión\n\n")
            f.write(review.get("review_report", "Sin resultados"))

        print(f"Reporte de revisión guardado en: {output_path}")

    def execute(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ejecutar la lógica principal del agente revisor."""
        if parameters and "executor_result" in parameters:
            # Revisar el resultado de la ejecución
            executor_result = parameters["executor_result"]
            # Crear cambios de código basados en el resultado
            code_changes = {
                "files": executor_result.get("files_modified", []),
                "change_type": "Implementación de tarea",
                "new_code": executor_result.get("code_implemented", ""),
            }
            review = self.review_code(code_changes)
        else:
            # Sample code changes for demonstration
            sample_changes = {
                "files": ["utils/validation.py"],
                "change_type": "Nueva funcionalidad",
                "new_code": "def validate_input(data):\n    return isinstance(data, str) and len(data) > 0",
            }
            review = self.review_code(sample_changes)

        self.save_review_report(review)
        return review

    @property
    def llm(self) -> LLM:
        """Obtener el modelo de lenguaje, inicializándolo si es necesario."""
        if self._llm is None:
            self._llm = self._initialize_llm()
        return self._llm


if __name__ == "__main__":
    # Ejemplo de uso
    reviewer = ReviewerAgent()

    # Ejemplo de cambios de código
    sample_changes = {
        "files": ["utils/validation.py"],
        "change_type": "Nueva funcionalidad",
        "new_code": "def validate_input(data):\n    return isinstance(data, str) and len(data) > 0",
    }

    review = reviewer.review_code(sample_changes)
    reviewer.save_review_report(review)
