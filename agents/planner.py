"""
Agente Planificador - Planner Agent

Este agente se especializa en analizar entradas del backlog y generar planes de trabajo ordenados.
Utiliza modelos locales (Ollama) con fallback a proveedores remotos.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from crewai import LLM, Agent, Crew, Task

from .base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """Agente planificador que genera planes de trabajo ordenados."""

    def __init__(self, config_path: str = "config/agents.config.json"):
        """Inicializar el agente planificador.

        Args:
            config_path: Ruta al archivo de configuración de agentes
        """
        super().__init__(config_path)

    def _get_agent_config(self) -> Dict[str, Any]:
        """Obtener configuración específica del agente planificador."""
        agents = self.config.get("agents", [])
        for agent in agents:
            if agent["id"] == "planner":
                return agent
        raise ValueError("Configuración del agente 'planner' no encontrada")

    def _load_prompt_template(self) -> str:
        """Cargar template del prompt desde archivo."""
        prompt_path = Path("prompts/planner.prompt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo de prompt no encontrado: {prompt_path}")

    def create_agent(self) -> Agent:
        """Crear el agente CrewAI para planificación."""
        return Agent(
            role="Planificador de Proyectos",
            goal="Analizar entradas del backlog y generar planes de trabajo ordenados y priorizados",
            backstory="Soy un agente especializado en planificación estratégica de proyectos. "
            "Mi expertise radica en descomponer objetivos complejos en tareas manejables, "
            "priorizar actividades según impacto y dependencia, y crear cronogramas realistas.",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def plan_tasks(self, backlog_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar un plan de trabajo a partir de entradas del backlog.

        Args:
            backlog_entries: Lista de entradas del backlog con descripción, prioridad, etc.

        Returns:
            Diccionario con el plan generado
        """
        # Crear prompt personalizado con las entradas del backlog
        backlog_text = self._format_backlog_entries(backlog_entries)

        # Recuperar información relevante usando RAG
        rag_query = f"planificación de tareas y gestión de proyectos: {' '.join([entry.get('title', '') + ' ' + entry.get('description', '') for entry in backlog_entries])}"
        relevant_info = self.retrieve_relevant_info(rag_query, k=3)

        # Combinar información del backlog con conocimiento recuperado
        combined_context = f"{backlog_text}\n\n{relevant_info}"

        prompt = self.prompt_template.replace("{{BACKLOG_ENTRIES}}", combined_context)

        # Crear tarea de planificación
        planning_task = Task(
            description=prompt,
            expected_output="Un plan de trabajo detallado en formato Markdown con tareas ordenadas, "
            "estimaciones de tiempo, dependencias y prioridades.",
            agent=self.create_agent(),
        )

        # Crear crew y ejecutar
        crew = Crew(agents=[self.create_agent()], tasks=[planning_task], verbose=True)

        result = crew.kickoff()

        # Procesar resultado y retornar en formato estructurado
        return self._parse_plan_result(result)

    def _format_backlog_entries(self, entries: List[Dict[str, Any]]) -> str:
        """Formatear entradas del backlog para el prompt."""
        formatted = []
        for i, entry in enumerate(entries, 1):
            formatted.append(
                f"{i}. **{entry.get('title', 'Sin título')}**\n"
                f"   - Descripción: {entry.get('description', 'N/A')}\n"
                f"   - Prioridad: {entry.get('priority', 'Media')}\n"
                f"   - Estimación: {entry.get('estimate', 'N/A')}\n"
                f"   - Dependencias: {', '.join(entry.get('dependencies', []))}\n"
            )
        return "\n".join(formatted)

    def _parse_plan_result(self, result) -> Dict[str, Any]:
        """Parsear el resultado del plan en formato estructurado."""
        # Por simplicidad, retornamos el resultado como string por ahora.
        # Incluir tanto la clave 'plan' (compatibilidad previa) como
        # 'plan_markdown' (esperada por algunas pruebas).
        text = str(result)
        return {
            "plan": text,
            "plan_markdown": text,
            "status": "generated",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def execute(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ejecutar la lógica principal del agente planificador."""
        if parameters and "markdown" in parameters:
            # Parsear el markdown para extraer tareas
            markdown_content = parameters["markdown"]
            backlog_entries = self._parse_markdown_to_backlog(markdown_content)
        else:
            # Usar sample backlog por defecto
            backlog_entries = [
                {
                    "title": "Implementar autenticación de usuarios",
                    "description": "Crear sistema de login con JWT",
                    "priority": "Alta",
                    "estimate": "2 días",
                    "dependencies": [],
                },
                {
                    "title": "Crear esquema de BD para usuarios y proyectos",
                    "description": "Diseñar tablas y relaciones",
                    "priority": "Alta",
                    "estimate": "1 día",
                    "dependencies": [],
                },
            ]

        plan = self.plan_tasks(backlog_entries)
        self.save_plan(plan)
        return plan

    def save_plan(self, plan: Dict[str, Any], output_path: str = "artifacts/plan.md"):
        """Guardar el plan generado en archivo."""
        output_dir = Path(output_path).parent
        output_dir.mkdir(exist_ok=True)
        # Soportar ambas formas: plan['plan'] o plan['plan_markdown']
        content = plan.get("plan_markdown") or plan.get("plan") or ""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Plan guardado en: {output_path}")

    @property
    def llm(self) -> LLM:
        """Obtener el modelo de lenguaje, inicializándolo si es necesario."""
        if self._llm is None:
            self._llm = self._initialize_llm()
        return self._llm

    def _parse_markdown_to_backlog(self, markdown: str) -> List[Dict[str, Any]]:
        """Parsear markdown simple a entradas del backlog."""
        lines = markdown.strip().split("\n")
        backlog = []
        current_task = None

        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                # Nueva tarea
                if current_task:
                    backlog.append(current_task)
                title = line[2:].strip()
                current_task = {
                    "title": title,
                    "description": title,  # Usar título como descripción por defecto
                    "priority": "Media",
                    "estimate": "N/A",
                    "dependencies": [],
                }
            elif current_task and line.startswith("  - ") and ":" in line:
                # Propiedad de la tarea
                key, value = line[4:].split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "prioridad" or key == "priority":
                    current_task["priority"] = value
                elif key == "estimación" or key == "estimate":
                    current_task["estimate"] = value
                elif key == "dependencias" or key == "dependencies":
                    current_task["dependencies"] = [d.strip() for d in value.split(",")]

        if current_task:
            backlog.append(current_task)

        return backlog


if __name__ == "__main__":
    # Ejemplo de uso
    planner = PlannerAgent()

    # Ejemplo de entradas del backlog
    sample_backlog = [
        {
            "title": "Implementar autenticación de usuarios",
            "description": "Crear sistema de login/registro con JWT",
            "priority": "Alta",
            "estimate": "2 días",
            "dependencies": [],
        },
        {
            "title": "Diseñar base de datos",
            "description": "Crear esquema de BD para usuarios y proyectos",
            "priority": "Alta",
            "estimate": "1 día",
            "dependencies": [],
        },
    ]

    plan = planner.plan_tasks(sample_backlog)
    planner.save_plan(plan)
