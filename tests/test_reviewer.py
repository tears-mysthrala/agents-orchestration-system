"""
Pruebas unitarias para el Agente Revisor

Tests para validar la funcionalidad del reviewer agent incluyendo:
- Carga de configuración
- Integración con prompts
- Revisión de código
- Análisis de rendimiento
- Validación de estándares
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from agents.reviewer import ReviewerAgent


class TestReviewerAgent(unittest.TestCase):
    """Suite de pruebas para ReviewerAgent."""

    def setUp(self):
        """Configurar entorno de pruebas."""
        # Crear configuración de prueba
        self.test_config = {
            "metadata": {"project": "test-project", "version": "1.0.0"},
            "runtime": {"ollama": {"host": "http://localhost:11434"}},
            "models": {"ollama": {"gemma2": {"temperature": 0.3, "context": 8192}}},
            "agents": [
                {
                    "id": "reviewer",
                    "defaultModel": "gemma2",
                    "tools": ["lint", "diff-analyser"],
                    "outputs": ["review-notes.md"],
                    "requires": ["executor"],
                }
            ],
        }

        # Crear prompt de prueba
        self.test_prompt = """
# Prompt para Agente Revisor

Eres un agente revisor especializado en evaluación de calidad.

## Instrucciones:
1. Revisa código implementado
2. Evalúa métricas de rendimiento
3. Identifica problemas y mejoras
4. Sugiere optimizaciones

## Formato de Salida:
- **Análisis General**: Evaluación
- **Problemas**: Lista con severidad
- **Sugerencias**: Recomendaciones
- **Aprobación**: Sí/No

Cambios de código:
{{CODE_CHANGES}}
"""

        # Crear archivos temporales
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "agents.config.json"
        self.prompt_file = self.temp_dir / "reviewer.prompt"

        # Escribir archivos de prueba
        with open(self.config_file, "w") as f:
            json.dump(self.test_config, f)

        with open(self.prompt_file, "w", encoding="utf-8") as f:
            f.write(self.test_prompt)

    def tearDown(self):
        """Limpiar archivos temporales."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_config_success(self):
        """Probar carga exitosa de configuración."""
        agent = ReviewerAgent(str(self.config_file))
        self.assertEqual(agent.config["metadata"]["project"], "test-project")

    def test_load_config_file_not_found(self):
        """Probar manejo de archivo de configuración no encontrado."""
        with self.assertRaises(FileNotFoundError):
            ReviewerAgent("nonexistent.json")

    def test_load_config_invalid_json(self):
        """Probar manejo de JSON inválido."""
        invalid_config = self.temp_dir / "invalid.json"
        with open(invalid_config, "w") as f:
            f.write("invalid json content")

        with self.assertRaises(ValueError):
            ReviewerAgent(str(invalid_config))

    def test_get_agent_config_success(self):
        """Probar obtención de configuración del agente."""
        agent = ReviewerAgent(str(self.config_file))
        config = agent._get_agent_config()
        self.assertEqual(config["id"], "reviewer")
        self.assertEqual(config["defaultModel"], "gemma2")

    def test_get_agent_config_not_found(self):
        """Probar error cuando agente no existe en config."""
        # Modificar config para no tener reviewer
        test_config_no_reviewer = self.test_config.copy()
        test_config_no_reviewer["agents"] = []

        config_file = self.temp_dir / "no_reviewer.json"
        with open(config_file, "w") as f:
            json.dump(test_config_no_reviewer, f)

        agent = ReviewerAgent.__new__(ReviewerAgent)  # Crear instancia sin __init__
        agent.config = test_config_no_reviewer

        with self.assertRaises(ValueError):
            agent._get_agent_config()

    def test_load_prompt_template_success(self):
        """Probar carga exitosa del template de prompt."""
        # Crear el directorio prompts y el archivo
        prompts_dir = self.temp_dir / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "reviewer.prompt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(self.test_prompt)

        # Cambiar al directorio temporal
        original_cwd = Path.cwd()
        import os

        try:
            os.chdir(self.temp_dir)
            agent = ReviewerAgent(str(self.config_file))
            prompt = agent._load_prompt_template()
            self.assertIn("Agente Revisor", prompt)
            self.assertIn("{{CODE_CHANGES}}", prompt)
        finally:
            os.chdir(original_cwd)

    @patch("crewai.LLM")
    def test_initialize_llm(self, mock_llm_class):
        """Probar inicialización del LLM."""
        # Crear agente con configuración de prueba
        agent = ReviewerAgent.__new__(ReviewerAgent)
        agent.config = self.test_config
        agent.agent_config = self.test_config["agents"][0]
        agent._llm = None

        # Solo verificar que no lanza excepciones y retorna algo
        llm = agent._initialize_llm()
        self.assertIsNotNone(llm)

    @patch("agents.reviewer.Agent")
    def test_create_agent(self, mock_agent_class):
        """Probar creación del agente CrewAI."""
        agent = ReviewerAgent(str(self.config_file))
        crew_agent = agent.create_agent()

        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        self.assertEqual(call_args[1]["role"], "Revisor de Código")
        self.assertIn("revisión de código", call_args[1]["backstory"])
        self.assertIsNotNone(crew_agent)

    def test_format_code_changes(self):
        """Probar formateo de cambios de código."""
        agent = ReviewerAgent(str(self.config_file))

        changes = {
            "files": ["utils.py", "main.py"],
            "change_type": "Refactorización",
            "diff": "+ def new_function():\n    pass",
            "new_code": "def new_function():\n    return True",
        }

        formatted = agent._format_code_changes(changes)
        self.assertIn("utils.py", formatted)
        self.assertIn("Refactorización", formatted)
        self.assertIn("new_function", formatted)

    def test_format_metrics(self):
        """Probar formateo de métricas."""
        agent = ReviewerAgent(str(self.config_file))

        metrics = {
            "execution_time": "2.5s",
            "memory_usage": "150MB",
            "cpu_usage": "45%",
        }

        formatted = agent._format_metrics(metrics)
        self.assertIn("execution_time: 2.5s", formatted)
        self.assertIn("memory_usage: 150MB", formatted)
        self.assertIn("cpu_usage: 45%", formatted)

    @patch("agents.reviewer.Crew")
    def test_review_code(self, mock_crew_class):
        """Probar revisión de código."""
        # Mock del resultado del crew
        mock_result = Mock()
        mock_result.__str__ = Mock(return_value="Revisión completada")

        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance

        agent = ReviewerAgent(str(self.config_file))

        code_changes = {"files": ["test.py"], "change_type": "Bug fix"}

        result = agent.review_code(code_changes)

        self.assertEqual(result["review_report"], "Revisión completada")
        self.assertEqual(result["status"], "reviewed")
        mock_crew_class.assert_called_once()
        mock_crew_instance.kickoff.assert_called_once()

    @patch("agents.reviewer.Crew")
    def test_analyze_performance(self, mock_crew_class):
        """Probar análisis de rendimiento."""
        # Mock del resultado del crew
        mock_result = Mock()
        mock_result.__str__ = Mock(return_value="Análisis de rendimiento completado")

        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance

        agent = ReviewerAgent(str(self.config_file))

        metrics = {"execution_time": "1.2s", "memory": "100MB"}

        result = agent.analyze_performance(metrics)

        self.assertEqual(
            result["performance_analysis"], "Análisis de rendimiento completado"
        )
        self.assertEqual(result["status"], "analyzed")
        mock_crew_class.assert_called_once()

    @patch("subprocess.run")
    def test_run_linting_success(self, mock_subprocess_run):
        """Probar linting exitoso."""
        # Mock de resultado exitoso
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        agent = ReviewerAgent(str(self.config_file))

        files = ["test.py"]
        result = agent.run_linting(files)

        self.assertTrue(result["overall_success"])
        self.assertTrue(result["lint_results"]["test.py"]["success"])

    @patch("subprocess.run")
    def test_run_linting_failure(self, mock_subprocess_run):
        """Probar linting fallido."""
        # Mock de resultado fallido
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "E501 line too long"
        mock_subprocess_run.return_value = mock_result

        agent = ReviewerAgent(str(self.config_file))

        files = ["test.py"]
        result = agent.run_linting(files)

        self.assertFalse(result["overall_success"])
        self.assertFalse(result["lint_results"]["test.py"]["success"])
        self.assertEqual(result["lint_results"]["test.py"]["returncode"], 1)

    @patch("agents.reviewer.Crew")
    def test_validate_standards(self, mock_crew_class):
        """Probar validación de estándares."""
        # Mock del resultado del crew
        mock_result = Mock()
        mock_result.__str__ = Mock(return_value="Validación completada")

        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance

        agent = ReviewerAgent(str(self.config_file))

        code_changes = {"files": ["test.py"]}
        standards = ["PEP 8", "Type hints"]

        result = agent.validate_standards(code_changes, standards)

        self.assertEqual(result["standards_validation"], "Validación completada")
        self.assertEqual(result["status"], "validated")
        mock_crew_class.assert_called_once()

    def test_parse_review_result(self):
        """Probar parseo del resultado de revisión."""
        agent = ReviewerAgent(str(self.config_file))

        result_str = "Esta es una revisión de prueba"
        parsed = agent._parse_review_result(result_str)

        self.assertEqual(parsed["review_report"], result_str)
        self.assertEqual(parsed["status"], "reviewed")
        self.assertIn("timestamp", parsed)

    @patch("builtins.open")
    @patch("pathlib.Path.mkdir")
    def test_save_review_report(self, mock_mkdir, mock_file_open):
        """Probar guardado del reporte de revisión."""
        # Mock de git status sin cambios para evitar commits
        mock_config_file = mock_open(
            read_data=json.dumps(self.test_config)
        ).return_value
        mock_prompt_file = mock_open(read_data=self.test_prompt).return_value
        mock_report_file = mock_open().return_value

        mock_file_open.side_effect = [
            mock_config_file,
            mock_prompt_file,
            mock_report_file,
        ]

        agent = ReviewerAgent(str(self.config_file))

        review = {
            "status": "reviewed",
            "timestamp": "2025-01-01T00:00:00Z",
            "review_report": "Contenido de revisión",
        }
        agent.save_review_report(review, "test/review.md")

        mock_mkdir.assert_called_once()
        # Verificar que se escribió contenido
        calls = mock_report_file.write.call_args_list
        self.assertTrue(len(calls) > 0)
        # Verificar que incluye el estado
        content = "".join(call[0][0] for call in calls)
        self.assertIn("reviewed", content)


if __name__ == "__main__":
    unittest.main()
