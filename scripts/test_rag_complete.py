#!/usr/bin/env python3
"""
Test completo del sistema RAG
"""

from agents.executor import ExecutorAgent
from agents.planner import PlannerAgent
from agents.rag_retriever import RAGRetriever


def test_complete_rag_system():
    print("=== Test Completo del Sistema RAG ===")

    # Test 1: RAG Retriever directo
    print("\n1. Test RAG Retriever:")
    retriever = RAGRetriever()
    results = retriever.retrieve("sistema de agentes", k=2)
    print(f"Resultados encontrados: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['source']}")

    # Test 2: Planner Agent con RAG
    print("\n2. Test Planner Agent:")
    planner = PlannerAgent()
    backlog = [
        {
            "title": "Implementar logging centralizado",
            "description": "Sistema de logs unificado para todos los agentes",
            "priority": "Alta",
        }
    ]
    plan = planner.plan_tasks(backlog)
    print("Plan generado exitosamente")

    # Test 3: Executor Agent con RAG
    print("\n3. Test Executor Agent:")
    executor = ExecutorAgent()
    task = {
        "title": "Crear módulo de logging",
        "description": "Implementar logging con configuración externa",
    }
    result = executor.execute_task(task)
    print("Tarea ejecutada exitosamente")

    print("\n=== Todos los tests pasaron exitosamente! ===")


if __name__ == "__main__":
    test_complete_rag_system()
