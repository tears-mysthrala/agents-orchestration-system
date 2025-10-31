#!/usr/bin/env python3
"""
Script para indexar documentos en el vector store de RAG

Este script inicializa o actualiza el índice de documentos para el sistema RAG
de los agentes de orquestación.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from agents.rag_retriever import RAGRetriever


def main():
    """Función principal para indexar documentos."""
    print("=== Indexador de Documentos RAG ===")

    # Verificar que estamos en el directorio correcto
    if not Path("docs").exists():
        print(
            "Error: No se encuentra la carpeta 'docs'. Asegúrate de ejecutar desde la raíz del proyecto."
        )
        sys.exit(1)

    try:
        print("Inicializando RAG Retriever...")
        retriever = RAGRetriever()

        print("Obteniendo estadísticas del vector store...")
        stats = retriever.get_stats()
        print(f"Estado actual: {stats}")

        # Si ya existe un índice, preguntar si reconstruir
        if stats.get("status") == "initialized":
            response = input(
                "Ya existe un índice. ¿Quieres reconstruirlo completamente? (y/N): "
            )
            if response.lower() in ["y", "yes"]:
                print("Reconstruyendo índice...")
                retriever.rebuild_index()
            else:
                print("Actualizando índice existente...")
                # Aquí podríamos agregar lógica para actualizar solo documentos nuevos
        else:
            print("Creando nuevo índice...")

        # Mostrar estadísticas finales
        final_stats = retriever.get_stats()
        print("\n=== Estadísticas Finales ===")
        for key, value in final_stats.items():
            print(f"{key}: {value}")

        print("\n=== Indexación completada exitosamente ===")

    except Exception as e:
        print(f"Error durante la indexación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
