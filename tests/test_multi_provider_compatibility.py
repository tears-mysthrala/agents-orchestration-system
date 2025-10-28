"""
Pruebas de Compatibilidad Multi-Proveedor

Tests para validar que los agentes funcionan correctamente con modelos locales (Ollama)
y remotos (GitHub Models, Azure AI Foundry), incluyendo lógica de fallback.
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from agents.base_agent import BaseAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reviewer import ReviewerAgent


class TestMultiProviderCompatibility(unittest.TestCase):
    """Suite de pruebas para compatibilidad multi-proveedor."""

    def setUp(self):
        """Configurar entorno de pruebas."""
        # Crear configuración de prueba con múltiples proveedores
        self.test_config = {
            "metadata": {"project": "test-project", "version": "1.0.0"},
            "runtime": {
                "defaultProvider": "ollama",
                "ollama": {"host": "http://localhost:11434"},
                "fallbackProviders": ["github-models", "azure-ai-foundry"],
            },
            "models": {
                "ollama": {
                    "llama3.2": {"temperature": 0.4, "context": 8192},
                    "deepseek-coder": {"temperature": 0.3, "context": 8192},
                    "gemma2": {"temperature": 0.4, "context": 8192},
                },
                "github-models": {
                    "gpt-4o-mini": {
                        "endpoint": "https://models.github.com",
                        "tokenEnv": "GITHUB_TOKEN",
                    }
                },
                "azure-ai-foundry": {
                    "gpt-4o": {
                        "endpointEnv": "AZURE_OPENAI_ENDPOINT",
                        "deploymentEnv": "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
                        "credential": "entra-id",
                    }
                },
            },
            "agents": [
                {
                    "id": "planner",
                    "defaultModel": "llama3.2",
                    "tools": ["task-registry"],
                    "outputs": ["plan.md"],
                    "requires": ["docs/tasks"],
                },
                {
                    "id": "executor",
                    "defaultModel": "deepseek-coder",
                    "tools": ["git", "tests"],
                    "outputs": ["patches"],
                    "requires": ["planner"],
                },
                {
                    "id": "reviewer",
                    "defaultModel": "gemma2",
                    "tools": ["lint", "diff-analyser"],
                    "outputs": ["review-notes.md"],
                    "requires": ["executor"],
                },
            ],
        }

        # Crear archivos temporales
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "agents.config.json"
        self.prompt_file = self.temp_dir / "test.prompt"

        # Escribir configuración de prueba
        with open(self.config_file, "w") as f:
            json.dump(self.test_config, f)

        # Crear archivo de prompt de prueba
        with open(self.prompt_file, "w") as f:
            f.write("Test prompt template")

    def tearDown(self):
        """Limpiar archivos temporales."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_base_agent_provider_validation(self):
        """Probar validación de compatibilidad de proveedores en BaseAgent."""

        # Crear agente básico para testing
        class TestAgent(BaseAgent):
            def __init__(self, config_path):
                import json

                with open(config_path, "r") as f:
                    self.test_config = json.load(f)
                super().__init__(config_path)

            def _get_agent_config(self):
                return self.test_config["agents"][0]  # planner

            def _load_prompt_template(self):
                # Mock prompt loading for tests
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Probar validación de proveedores
        compatibility = agent.validate_provider_compatibility()

        # Debería tener resultados para ollama, github-models, azure-ai-foundry
        self.assertIn("ollama", compatibility)
        self.assertIn("github-models", compatibility)
        self.assertIn("azure-ai-foundry", compatibility)

        # Ollama debería ser compatible (sin errores de configuración)
        self.assertTrue(compatibility["ollama"]["compatible"])

    @patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"})
    @patch("agents.base_agent.LLM")
    def test_github_models_initialization(self, mock_llm_class):
        """Probar inicialización con GitHub Models."""

        class TestAgent(BaseAgent):
            def _get_agent_config(self):
                return {"id": "test", "defaultModel": "gpt-4o-mini"}

            def _load_prompt_template(self):
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Intentar inicializar con GitHub Models
        agent._initialize_llm("github-models", "gpt-4o-mini")

        # Verificar que se llamó con los parámetros correctos
        mock_llm_class.assert_called_once()
        call_args = mock_llm_class.call_args
        self.assertEqual(call_args[1]["model"], "openai/gpt-4o-mini")
        self.assertEqual(call_args[1]["api_key"], "fake-token")
        self.assertIn("models.github.com", call_args[1]["base_url"])

    @patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "gpt-4o",
        },
    )
    @patch("agents.base_agent.LLM")
    def test_azure_initialization(self, mock_llm_class):
        """Probar inicialización con Azure AI Foundry."""

        class TestAgent(BaseAgent):
            def _get_agent_config(self):
                return {"id": "test", "defaultModel": "gpt-4o"}

            def _load_prompt_template(self):
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Intentar inicializar con Azure
        agent._initialize_llm("azure-ai-foundry", "gpt-4o")

        # Verificar que se llamó con los parámetros correctos
        mock_llm_class.assert_called_once()
        call_args = mock_llm_class.call_args
        self.assertEqual(call_args[1]["model"], "azure/gpt-4o")
        self.assertEqual(call_args[1]["base_url"], "https://test.openai.azure.com")
        self.assertIsNone(call_args[1]["api_key"])  # Entra ID

    @patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"})
    @patch("agents.base_agent.LLM")
    def test_fallback_logic(self, mock_llm_class):
        """Probar lógica de fallback entre proveedores."""
        # Configurar mock para que Ollama falle pero GitHub funcione
        mock_llm_class.side_effect = [
            Exception("Ollama not available"),  # Primer llamado falla
            Mock(),  # Segundo llamado (GitHub) funciona
        ]

        class TestAgent(BaseAgent):
            def _get_agent_config(self):
                return {"id": "test", "defaultModel": "llama3.2"}

            def _load_prompt_template(self):
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Intentar inicializar - debería hacer fallback
        agent._initialize_llm("ollama", "gpt-4o-mini")

        # Verificar que se intentó GitHub como fallback
        self.assertEqual(mock_llm_class.call_count, 2)

    def test_planner_agent_provider_switching(self):
        """Probar cambio dinámico de proveedor en PlannerAgent."""
        agent = PlannerAgent(str(self.config_file))

        # Verificar proveedor inicial
        self.assertEqual(agent.get_current_provider(), "ollama")

        # Cambiar a GitHub (sin ejecutar realmente)
        with patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"}):
            with patch("agents.base_agent.LLM") as mock_llm:
                agent.switch_provider("github-models", "gpt-4o-mini")

                # Verificar que cambió
                self.assertEqual(agent.get_current_provider(), "github-models")
                # El LLM se inicializa en el switch, así que debería llamarse
                mock_llm.assert_called_once()

    def test_executor_agent_provider_switching(self):
        """Probar cambio dinámico de proveedor en ExecutorAgent."""
        agent = ExecutorAgent(str(self.config_file))

        # Verificar proveedor inicial
        self.assertEqual(agent.get_current_provider(), "ollama")

        # Cambiar a Azure (sin ejecutar realmente)
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.azure.com",
                "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "gpt-4o",
            },
        ):
            with patch("agents.base_agent.LLM") as mock_llm:
                agent.switch_provider("azure-ai-foundry", "gpt-4o")

                # Verificar que cambió
                self.assertEqual(agent.get_current_provider(), "azure-ai-foundry")
                mock_llm.assert_called_once()

    def test_reviewer_agent_provider_switching(self):
        """Probar cambio dinámico de proveedor en ReviewerAgent."""
        agent = ReviewerAgent(str(self.config_file))

        # Verificar proveedor inicial
        self.assertEqual(agent.get_current_provider(), "ollama")

        # Cambiar proveedor (sin ejecutar realmente)
        with patch("agents.base_agent.LLM") as mock_llm:
            agent.switch_provider("ollama", "gemma2")

            # Verificar que cambió
            self.assertEqual(agent.get_current_provider(), "ollama")
            mock_llm.assert_called_once()

    @patch("crewai.LLM")
    def test_all_agents_compatibility_validation(self, mock_llm):
        """Probar validación de compatibilidad para todos los agentes."""
        agents = [
            PlannerAgent(str(self.config_file)),
            ExecutorAgent(str(self.config_file)),
            ReviewerAgent(str(self.config_file)),
        ]

        for agent in agents:
            with self.subTest(agent=agent.__class__.__name__):
                compatibility = agent.validate_provider_compatibility()

                # Todos deberían tener resultados para los proveedores configurados
                expected_providers = ["ollama", "github-models", "azure-ai-foundry"]
                for provider in expected_providers:
                    self.assertIn(provider, compatibility)
                    self.assertIn("compatible", compatibility[provider])
                    self.assertIn("model", compatibility[provider])

    def test_provider_error_handling(self):
        """Probar manejo de errores cuando proveedores no están disponibles."""

        class TestAgent(BaseAgent):
            def _get_agent_config(self):
                return {"id": "test", "defaultModel": "nonexistent-model"}

            def _load_prompt_template(self):
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Intentar inicializar con modelo que no existe
        with self.assertRaises(Exception):
            agent._initialize_llm("ollama", "nonexistent-model")

    @patch.dict("os.environ", {}, clear=True)  # No tokens
    def test_github_token_missing_error(self):
        """Probar error cuando falta token de GitHub."""

        class TestAgent(BaseAgent):
            def _get_agent_config(self):
                return {"id": "test", "defaultModel": "gpt-4o-mini"}

            def _load_prompt_template(self):
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Debería fallar por token faltante
        with self.assertRaises(Exception) as context:
            agent._initialize_llm("github-models", "gpt-4o-mini")

        self.assertIn("Todos los proveedores fallaron", str(context.exception))

    @patch.dict("os.environ", {}, clear=True)  # No env vars
    def test_azure_env_missing_error(self):
        """Probar error cuando faltan variables de entorno de Azure."""

        class TestAgent(BaseAgent):
            def _get_agent_config(self):
                return {"id": "test", "defaultModel": "gpt-4o"}

            def _load_prompt_template(self):
                return "Test prompt template"

            def create_agent(self):
                return Mock()

        agent = TestAgent(str(self.config_file))

        # Debería fallar por variables faltantes
        with self.assertRaises(Exception) as context:
            agent._initialize_llm("azure-ai-foundry", "gpt-4o")

        self.assertIn("Todos los proveedores fallaron", str(context.exception))


if __name__ == "__main__":
    unittest.main()
