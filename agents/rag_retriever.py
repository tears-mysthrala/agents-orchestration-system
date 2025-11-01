"""
RAG Retriever - Retrieval-Augmented Generation Component

Este módulo proporciona funcionalidad de RAG para los agentes,
permitiendo recuperar información relevante de una base de conocimientos.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class RAGRetriever:
    """Clase para manejar recuperación de información usando RAG."""

    def __init__(
        self,
        docs_path: str = "docs",
        vector_store_path: str = "vectorstore",
        embedding_provider: str = "sentence-transformers",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """Inicializar el retriever RAG.

        Args:
            docs_path: Ruta a la carpeta de documentos
            vector_store_path: Ruta donde guardar el vector store
            embedding_provider: Proveedor de embeddings ('sentence-transformers' o 'openai')
            chunk_size: Tamaño de chunks para dividir documentos
            chunk_overlap: Solapamiento entre chunks
        """
        self.docs_path = Path(docs_path)
        self.vector_store_path = Path(vector_store_path)
        self.embedding_provider = embedding_provider
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embeddings = self._initialize_embeddings()
        self.vectorstore = None
        self._load_or_create_vectorstore()

    def _initialize_embeddings(self):
        """Inicializar el modelo de embeddings."""
        if self.embedding_provider == "openai":
            return OpenAIEmbeddings(
                model="text-embedding-ada-002",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
        elif self.embedding_provider == "sentence-transformers":
            return SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        else:
            raise ValueError(
                f"Proveedor de embeddings no soportado: {self.embedding_provider}"
            )

    def _load_or_create_vectorstore(self):
        """Cargar vector store existente o crear uno nuevo."""
        if self.vector_store_path.exists():
            try:
                if (self.vector_store_path / "index.faiss").exists():
                    self.vectorstore = FAISS.load_local(
                        str(self.vector_store_path),
                        self.embeddings,
                        allow_dangerous_deserialization=True,
                    )
                else:
                    # If no FAISS index exists, create new
                    self._create_vectorstore()
                print(f"Vector store cargado desde: {self.vector_store_path}")
            except Exception as e:
                print(f"Error cargando vector store: {e}. Creando nuevo...")
                self._create_vectorstore()
        else:
            self._create_vectorstore()

    def _create_vectorstore(self):
        """Crear un nuevo vector store desde los documentos."""
        print("Creando nuevo vector store...")
        documents = self._load_documents()

        if not documents:
            print("No se encontraron documentos para indexar.")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        splits = text_splitter.split_documents(documents)

        # Usar FAISS por defecto
        self.vectorstore = FAISS.from_documents(
            documents=splits, embedding=self.embeddings
        )

        # Guardar el índice
        self.vectorstore.save_local(str(self.vector_store_path))

        print(
            f"Vector store creado con {len(splits)} chunks de {len(documents)} documentos."
        )

    def _load_documents(self) -> List[Document]:
        """Cargar documentos desde la carpeta docs."""
        documents = []

        if not self.docs_path.exists():
            print(f"Ruta de documentos no existe: {self.docs_path}")
            return documents

        for file_path in self.docs_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [
                ".md",
                ".txt",
                ".py",
                ".json",
            ]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Crear documento con metadata
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path.relative_to(self.docs_path.parent)),
                            "file_type": file_path.suffix,
                            "file_name": file_path.name,
                        },
                    )
                    documents.append(doc)
                    print(f"Documento cargado: {file_path}")

                except Exception as e:
                    print(f"Error cargando {file_path}: {e}")

        return documents

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recuperar documentos relevantes para una consulta.

        Args:
            query: Consulta de búsqueda
            k: Número de documentos a recuperar

        Returns:
            Lista de documentos relevantes con contenido y metadata
        """
        if self.vectorstore is None:
            print("Vector store no inicializado.")
            return []

        try:
            docs = self.vectorstore.similarity_search(query, k=k)

            results = []
            for doc in docs:
                results.append(
                    {
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "file_type": doc.metadata.get("file_type", "unknown"),
                        "score": getattr(
                            doc, "score", None
                        ),  # Algunos vectorstores incluyen score
                    }
                )

            return results

        except Exception as e:
            print(f"Error en búsqueda: {e}")
            return []

    def retrieve_with_scores(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recuperar documentos con scores de similitud.

        Args:
            query: Consulta de búsqueda
            k: Número de documentos a recuperar

        Returns:
            Lista de documentos con scores
        """
        if self.vectorstore is None:
            return []

        try:
            docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=k)

            results = []
            for doc, score in docs_and_scores:
                results.append(
                    {
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "file_type": doc.metadata.get("file_type", "unknown"),
                        "score": score,
                    }
                )

            return results

        except Exception as e:
            print(f"Error en búsqueda con scores: {e}")
            return []

    def add_documents(self, documents: List[Document]):
        """Agregar nuevos documentos al vector store.

        Args:
            documents: Lista de documentos a agregar
        """
        if self.vectorstore is None:
            self._create_vectorstore()
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

        splits = text_splitter.split_documents(documents)
        self.vectorstore.add_documents(splits)

        # Persistir cambios
        self.vectorstore.save_local(str(self.vector_store_path))

    def rebuild_index(self):
        """Reconstruir completamente el índice desde los documentos."""
        if self.vector_store_path.exists():
            import shutil

            shutil.rmtree(self.vector_store_path)

        self._create_vectorstore()

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del vector store."""
        if self.vectorstore is None:
            return {"status": "not_initialized"}

        try:
            # Intentar obtener count (depende del tipo de vectorstore)
            count = getattr(self.vectorstore, "_collection", None)
            if count and hasattr(count, "count"):
                doc_count = count.count()
            else:
                doc_count = "unknown"

            return {
                "status": "initialized",
                "document_count": doc_count,
                "embedding_provider": self.embedding_provider,
                "chunk_size": self.chunk_size,
                "docs_path": str(self.docs_path),
                "vector_store_path": str(self.vector_store_path),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Ejemplo de uso
    retriever = RAGRetriever()

    # Probar búsqueda
    results = retriever.retrieve("planificación de tareas", k=3)
    print(f"Resultados encontrados: {len(results)}")

    for i, result in enumerate(results, 1):
        print(f"\n--- Resultado {i} ---")
        print(f"Source: {result['source']}")
        print(f"Content: {result['content'][:200]}...")

    # Mostrar estadísticas
    stats = retriever.get_stats()
    print(f"\nEstadísticas: {stats}")
