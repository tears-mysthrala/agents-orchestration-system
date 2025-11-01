"""
Pruebas unitarias para el Agente Ejecutor

Tests para validar la funcionalidad del executor agent incluyendo:
- Carga de configuración
- Integración con prompts
- Ejecución de tareas
- Ejecución de pruebas
- Integración con git
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from agents.executor import ExecutorAgent


class TestExecutorAgent(unittest.TestCase):
    """Suite de pruebas para ExecutorAgent."""

    def setUp(self):
        """Configurar entorno de pruebas."""
        # Crear configuración de prueba
        self.test_config = {
            "metadata": {"project": "test-project", "version": "1.0.0"},
            "runtime": {"ollama": {"host": "http://localhost:11434"}},
            "models": {
                "ollama": {"deepseek-coder": {"temperature": 0.2, "context": 4096}}
            },
            "agents": [
                {
                    "id": "executor",
                    "defaultModel": "deepseek-coder",
                    "tools": ["git", "tests"],
                    "outputs": ["patches", "test-report.md"],
                    "requires": ["planner"],
                }
            ],
        }

        # Crear prompt de prueba
        self.test_prompt = """
# Prompt para Agente Ejecutor

Eres un agente ejecutor especializado en implementación de código.

## Instrucciones:
1. Recibe especificaciones de tarea
2. Implementa código según requerimientos
3. Ejecuta pruebas unitarias
4. Integra cambios en repositorios

## Formato de Salida:
- **Tarea Ejecutada**: Descripción
- **Código Implementado**: Fragmentos
- **Pruebas**: Resultados
- **Estado**: Completado/Pendiente

Especificación de tarea:
{{TASK_SPEC}}
"""

        # Crear archivos temporales
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "agents.config.json"
        self.prompt_file = self.temp_dir / "executor.prompt"

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
        agent = ExecutorAgent(str(self.config_file))
        self.assertEqual(agent.config["metadata"]["project"], "test-project")

    def test_load_config_file_not_found(self):
        """Probar manejo de archivo de configuración no encontrado."""
        with self.assertRaises(FileNotFoundError):
            ExecutorAgent("nonexistent.json")

    def test_load_config_invalid_json(self):
        """Probar manejo de JSON inválido."""
        invalid_config = self.temp_dir / "invalid.json"
        with open(invalid_config, "w") as f:
            f.write("invalid json content")

        with self.assertRaises(ValueError):
            ExecutorAgent(str(invalid_config))

    def test_get_agent_config_success(self):
        """Probar obtención de configuración del agente."""
        agent = ExecutorAgent(str(self.config_file))
        config = agent._get_agent_config()
        self.assertEqual(config["id"], "executor")
        self.assertEqual(config["defaultModel"], "deepseek-coder")

    def test_get_agent_config_not_found(self):
        """Probar error cuando agente no existe en config."""
        # Modificar config para no tener executor
        test_config_no_executor = self.test_config.copy()
        test_config_no_executor["agents"] = []

        config_file = self.temp_dir / "no_executor.json"
        with open(config_file, "w") as f:
            json.dump(test_config_no_executor, f)

        agent = ExecutorAgent.__new__(ExecutorAgent)  # Crear instancia sin __init__
        agent.config = test_config_no_executor

        with self.assertRaises(ValueError):
            agent._get_agent_config()

    def test_load_prompt_template_success(self):
        """Probar carga exitosa del template de prompt."""
        # Crear el directorio prompts y el archivo
        prompts_dir = self.temp_dir / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "executor.prompt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(self.test_prompt)

        # Cambiar al directorio temporal
        original_cwd = Path.cwd()
        import os

        try:
            os.chdir(self.temp_dir)
            agent = ExecutorAgent(str(self.config_file))
            prompt = agent._load_prompt_template()
            self.assertIn("Agente Ejecutor", prompt)
            self.assertIn("{{TASK_SPEC}}", prompt)
        finally:
            os.chdir(original_cwd)

    @patch("crewai.LLM")
    def test_initialize_llm(self, mock_llm_class):
        """Probar inicialización del LLM."""
        # Crear agente con configuración de prueba
        agent = ExecutorAgent.__new__(ExecutorAgent)
        agent.config = self.test_config
        agent.agent_config = self.test_config["agents"][0]
        agent._llm = None

        # Solo verificar que no lanza excepciones y retorna algo
        llm = agent._initialize_llm()
        self.assertIsNotNone(llm)

    @patch("agents.executor.Agent")
    def test_create_agent(self, mock_agent_class):
        """Probar creación del agente CrewAI."""
        agent = ExecutorAgent(str(self.config_file))
        crew_agent = agent.create_agent()

        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        self.assertEqual(call_args[1]["role"], "Ejecutor de Código")
        self.assertIn("desarrollo e implementación", call_args[1]["backstory"])
        self.assertIsNotNone(crew_agent)

    def test_format_task_spec(self):
        """Probar formateo de especificación de tarea."""
        agent = ExecutorAgent(str(self.config_file))

        task_spec = {
            "title": "Tarea de Prueba",
            "description": "Descripción de prueba",
            "requirements": "Requisitos de prueba",
            "files": ["file1.py", "file2.py"],
            "code_changes": ["Cambiar función X", "Agregar validación Y"],
        }

        formatted = agent._format_task_spec(task_spec)
        self.assertIn("Tarea de Prueba", formatted)
        self.assertIn("Descripción de prueba", formatted)
        self.assertIn("file1.py", formatted)
        self.assertIn("Cambiar función X", formatted)

    @patch("agents.executor.Crew")
    def test_execute_task(self, mock_crew_class):
        """Probar ejecución de tareas."""
        # Mock del resultado del crew
        mock_result = Mock()
        mock_result.__str__ = Mock(return_value="Resultado de ejecución")

        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance

        agent = ExecutorAgent(str(self.config_file))

        task_spec = {
            "title": "Test Task",
            "description": "Test",
            "requirements": "Test req",
        }

        result = agent.execute_task(task_spec)

        self.assertEqual(result["execution_result"], "Resultado de ejecución")
        self.assertEqual(result["status"], "completed")
        mock_crew_class.assert_called_once()
        mock_crew_instance.kickoff.assert_called_once()

    @patch("subprocess.run")
    def test_run_tests_success(self, mock_subprocess_run):
        """Probar ejecución exitosa de pruebas."""
        # Mock de resultado exitoso
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Tests passed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        agent = ExecutorAgent(str(self.config_file))

        test_files = ["test_module.py"]
        result = agent.run_tests(test_files)

        self.assertTrue(result["overall_success"])
        self.assertTrue(result["test_results"]["test_module.py"]["success"])
        self.assertEqual(
            result["test_results"]["test_module.py"]["stdout"], "Tests passed"
        )

    @patch("subprocess.run")
    def test_run_tests_failure(self, mock_subprocess_run):
        """Probar ejecución fallida de pruebas."""
        # Mock de resultado fallido
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Test failed"
        mock_subprocess_run.return_value = mock_result

        agent = ExecutorAgent(str(self.config_file))

        test_files = ["test_module.py"]
        result = agent.run_tests(test_files)

        self.assertFalse(result["overall_success"])
        self.assertFalse(result["test_results"]["test_module.py"]["success"])
        self.assertEqual(result["test_results"]["test_module.py"]["returncode"], 1)

    @patch("subprocess.run")
    def test_integrate_changes_success(self, mock_subprocess_run):
        """Probar integración exitosa de cambios."""
        # Mock de git status con cambios
        mock_status = Mock()
        mock_status.stdout = "M modified_file.py"
        mock_status.returncode = 0

        # Mock de git add y commit exitosos
        mock_add = Mock()
        mock_add.returncode = 0

        mock_commit = Mock()
        mock_commit.returncode = 0

        mock_subprocess_run.side_effect = [mock_status, mock_add, mock_commit]

        agent = ExecutorAgent(str(self.config_file))

        changes = {"modified_files": ["modified_file.py"]}
        result = agent.integrate_changes(changes, "Test commit")

        self.assertTrue(result["success"])
        self.assertTrue(result["committed"])
        self.assertIn("Test commit", result["message"])

    @patch("subprocess.run")
    def test_integrate_changes_no_changes(self, mock_subprocess_run):
        """Probar integración cuando no hay cambios."""
        # Mock de git status sin cambios
        mock_status = Mock()
        mock_status.stdout = ""
        mock_status.returncode = 0
        mock_subprocess_run.return_value = mock_status

        agent = ExecutorAgent(str(self.config_file))

        changes = {}
        result = agent.integrate_changes(changes, "Test commit")

        self.assertTrue(result["success"])
        self.assertFalse(result["committed"])
        self.assertIn("No hay cambios", result["message"])

    @patch("subprocess.run")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    def test_save_report(self, mock_file_open, mock_mkdir, mock_subprocess_run):
        """Probar guardado del reporte."""
        # Mock de git status sin cambios para evitar commits
        mock_status = Mock()
        mock_status.stdout = ""
        mock_status.returncode = 0
        mock_subprocess_run.return_value = mock_status

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

        agent = ExecutorAgent(str(self.config_file))

        report = {
            "status": "completed",
            "timestamp": "2025-01-01T00:00:00Z",
            "execution_result": "Test results",
        }
        agent.save_report(report, "test/report.md")

        mock_mkdir.assert_called_once()
        # Verificar que se escribió contenido
        calls = mock_report_file.write.call_args_list
        self.assertTrue(len(calls) > 0)
        # Verificar que incluye el estado
        content = "".join(call[0][0] for call in calls)
        self.assertIn("completed", content)


if __name__ == "__main__":
    unittest.main()
