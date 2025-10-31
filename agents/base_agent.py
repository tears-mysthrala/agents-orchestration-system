"""
Agente Base - Base Agent Class

Clase base que proporciona funcionalidad común para todos los agentes,
incluyendo soporte para múltiples proveedores de modelos (locales y remotos).
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from crewai import Agent, LLM
from .rag_retriever import RAGRetriever


class BaseAgent(ABC):
    """Clase base para todos los agentes con soporte multi-proveedor."""

    def __init__(self, config_path: str = "config/agents.config.json"):
        """Inicializar el agente base.

        Args:
            config_path: Ruta al archivo de configuración de agentes
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.agent_config = self._get_agent_config()
        self.prompt_template = self._load_prompt_template()
        self._llm: Optional[LLM] = None
        self._current_provider = None
        self._retriever: Optional[RAGRetriever] = None

    def _load_config(self) -> Dict[str, Any]:
        """Cargar configuración desde archivo JSON."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: {self.config_path}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al parsear configuración JSON: {e}")

    @abstractmethod
    def _get_agent_config(self) -> Dict[str, Any]:
        """Obtener configuración específica del agente. Debe ser implementado por subclases."""
        pass

    @abstractmethod
    def execute(self) -> Any:
        """Ejecutar la lógica principal del agente. Debe ser implementado por subclases."""
        pass

    def _load_prompt_template(self) -> str:
        """Cargar template del prompt desde archivo."""
        prompt_path = Path("prompts") / f"{self.agent_config['id']}.prompt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo de prompt no encontrado: {prompt_path}")

    def _initialize_llm(
        self, provider: Optional[str] = None, model_name: Optional[str] = None
    ) -> LLM:
        """Inicializar el modelo de lenguaje con soporte multi-proveedor.

        Args:
            provider: Proveedor a usar ('ollama', 'github-models', 'azure-ai-foundry')
            model_name: Nombre específico del modelo

        Returns:
            Instancia de LLM configurada
        """
        if provider is None:
            provider = self.config["runtime"]["defaultProvider"]

        if model_name is None:
            model_name = self.agent_config["defaultModel"]

        self._current_provider = provider

        try:
            if provider == "ollama":
                return self._initialize_ollama_llm(model_name)  # type: ignore
            elif provider == "github-models":
                return self._initialize_github_llm(model_name)  # type: ignore
            elif provider == "azure-ai-foundry":
                return self._initialize_azure_llm(model_name)  # type: ignore
            else:
                raise ValueError(f"Proveedor no soportado: {provider}")
        except Exception as e:
            # Intentar fallback providers
            return self._try_fallback_providers(model_name, provider, e)  # type: ignore

    def _initialize_ollama_llm(self, model_name: str) -> LLM:
        """Inicializar LLM con Ollama (local)."""
        ollama_config = self.config["runtime"]["ollama"]
        model_config = self.config["models"]["ollama"][model_name]

        return LLM(
            model=f"ollama/{model_name}",
            base_url=ollama_config["host"],
            temperature=model_config["temperature"],
            max_tokens=model_config["context"],
        )

    def _initialize_github_llm(self, model_name: str) -> LLM:
        """Inicializar LLM con GitHub Models."""
        model_config = self.config["models"]["github-models"][model_name]
        token = os.getenv(model_config["tokenEnv"])

        if not token:
            raise ValueError(
                f"Token de GitHub no encontrado en variable: {model_config['tokenEnv']}"
            )

        return LLM(
            model=f"openai/{model_name}",
            api_key=token,
            base_url=model_config["endpoint"],
            temperature=0.7,  # Default for GitHub models
            max_tokens=4096,
        )

    def _initialize_azure_llm(self, model_name: str) -> LLM:
        """Inicializar LLM con Azure AI Foundry."""
        model_config = self.config["models"]["azure-ai-foundry"][model_name]

        endpoint = os.getenv(model_config["endpointEnv"])
        deployment = os.getenv(model_config["deploymentEnv"])

        if not endpoint or not deployment:
            raise ValueError("Variables de entorno de Azure no configuradas")

        # Para Azure OpenAI, necesitamos configurar la API key o usar managed identity
        if model_config["credential"] == "entra-id":
            # Usar managed identity (sin API key explícita)
            api_key = None
        else:
            api_key = os.getenv("AZURE_OPENAI_API_KEY")

        return LLM(
            model=f"azure/{deployment}",
            api_key=api_key,
            base_url=endpoint,
            temperature=0.7,
            max_tokens=4096,
        )

    def _try_fallback_providers(
        self, model_name: str, failed_provider: str, original_error: Exception
    ) -> LLM:
        """Intentar proveedores de fallback cuando el principal falla.

        Args:
            model_name: Nombre del modelo solicitado
            failed_provider: Proveedor que falló
            original_error: Error original

        Returns:
            LLM del proveedor de fallback

        Raises:
            Exception: Si todos los proveedores fallan
        """
        fallback_providers = self.config["runtime"]["fallbackProviders"]

        for provider in fallback_providers:
            if provider == failed_provider:
                continue  # Saltar el que ya falló

            try:
                print(
                    f"Intentando proveedor de fallback: {provider} (falló: {failed_provider})"
                )
                return self._initialize_llm(provider, model_name)
            except Exception as e:
                print(f"Proveedor de fallback {provider} también falló: {e}")
                continue

        # Si todos fallan, lanzar el error original
        raise Exception(
            f"Todos los proveedores fallaron. Error original de {failed_provider}: {original_error}"
        )

    @abstractmethod
    def create_agent(self) -> Agent:
        """Crear el agente CrewAI. Debe ser implementado por subclases."""
        pass

    def switch_provider(self, provider: str, model_name: Optional[str] = None) -> None:
        """Cambiar dinámicamente el proveedor de modelos.

        Args:
            provider: Nuevo proveedor ('ollama', 'github-models', 'azure-ai-foundry')
            model_name: Nombre del modelo (opcional)
        """
        if model_name is None:
            model_name = self.agent_config["defaultModel"]

        self._llm = self._initialize_llm(provider, model_name)
        print(f"Proveedor cambiado a: {provider} con modelo: {model_name}")

    def get_current_provider(self) -> str:
        """Obtener el proveedor actualmente en uso."""
        return self._current_provider or self.config["runtime"]["defaultProvider"]

    def validate_provider_compatibility(self) -> Dict[str, Any]:
        """Validar compatibilidad con todos los proveedores configurados.

        Returns:
            Diccionario con estado de compatibilidad por proveedor
        """
        results = {}
        providers = [self.config["runtime"]["defaultProvider"]] + self.config[
            "runtime"
        ]["fallbackProviders"]

        for provider in providers:
            try:
                self._initialize_llm(provider)
                results[provider] = {
                    "compatible": True,
                    "model": self.agent_config["defaultModel"],
                    "error": None,
                }
            except Exception as e:
                results[provider] = {
                    "compatible": False,
                    "model": self.agent_config["defaultModel"],
                    "error": str(e),
                }

        return results

    @property
    def llm(self) -> LLM:
        """Obtener el modelo de lenguaje, inicializándolo si es necesario."""
        if self._llm is None:
            self._llm = self._initialize_llm()
        return self._llm

    @property
    def retriever(self) -> RAGRetriever:
        """Obtener el retriever RAG, inicializándolo si es necesario."""
        if self._retriever is None:
            self._retriever = RAGRetriever()
        return self._retriever

    def retrieve_relevant_info(self, query: str, k: int = 3) -> str:
        """Recuperar información relevante para una consulta usando RAG.

        Args:
            query: Consulta para buscar información relevante
            k: Número de documentos a recuperar

        Returns:
            String con la información relevante formateada
        """
        results = self.retriever.retrieve(query, k=k)

        if not results:
            return "No se encontró información relevante en la base de conocimientos."

        formatted_info = "Información relevante recuperada:\n\n"
        for i, result in enumerate(results, 1):
            formatted_info += f"**Fuente {i}: {result['source']}**\n"
            formatted_info += f"{result['content'][:500]}{'...' if len(result['content']) > 500 else ''}\n\n"

        return formatted_info
