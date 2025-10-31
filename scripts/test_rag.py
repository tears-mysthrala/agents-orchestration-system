#!/usr/bin/env python3
"""
Test script para verificar la funcionalidad RAG en los agentes
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from agents.planner import PlannerAgent


def test_rag_retrieval():
    """Prueba la recuperación de información RAG."""
    print("=== Prueba de Recuperación RAG ===")

    # Crear agente
    planner = PlannerAgent()

    # Probar recuperación directa
    query = "planificación de proyectos"
    print(f"Consultando: '{query}'")

    relevant_info = planner.retrieve_relevant_info(query, k=2)
    print("Información relevante recuperada:")
    print(relevant_info)
    print()


def test_planner_with_rag():
    """Prueba el agente planificador con RAG."""
    print("=== Prueba del Agente Planificador con RAG ===")

    planner = PlannerAgent()

    # Backlog de ejemplo
    sample_backlog = [
        {
            "title": "Implementar sistema de autenticación",
            "description": "Crear login/registro con JWT tokens",
            "priority": "Alta",
            "estimate": "3 días",
            "dependencies": [],
        },
        {
            "title": "Diseñar arquitectura del sistema",
            "description": "Definir componentes y flujo de datos",
            "priority": "Alta",
            "estimate": "2 días",
            "dependencies": [],
        },
    ]

    print("Generando plan con RAG...")
    plan = planner.plan_tasks(sample_backlog)

    print("Plan generado:")
    print(plan["plan"])
    print()


if __name__ == "__main__":
    try:
        test_rag_retrieval()
        test_planner_with_rag()
        print("=== Todas las pruebas completadas exitosamente ===")
    except Exception as e:
        print(f"Error durante las pruebas: {e}")
        sys.exit(1)
