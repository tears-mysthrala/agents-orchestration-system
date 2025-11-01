def pytest_configure(config):
    """Silence colorama/crewai atexit noise in test environment by wrapping reset_all."""
    try:
        import colorama.initialise as colour_init

        orig = getattr(colour_init, "reset_all", None)

        def _safe_reset_all():
            try:
                if orig:
                    orig()
            except Exception:
                # Suppress any errors during interpreter shutdown in test env
                pass

        if orig:
            setattr(colour_init, "reset_all", _safe_reset_all)
    except Exception:
        # colorama not installed or unexpected state; ignore
        pass
    # Provide a lightweight Fake RAG retriever for tests to avoid heavy ML/native deps
    try:
        import agents.rag_retriever as rag_mod

        class FakeRAGRetriever:
            def __init__(self, *args, **kwargs):
                self.docs_path = kwargs.get("docs_path", "docs")
                self.vector_store_path = kwargs.get("vector_store_path", "vectorstore")
                self.embedding_provider = kwargs.get(
                    "embedding_provider", "sentence-transformers"
                )
                self.chunk_size = kwargs.get("chunk_size", 1000)
                self.chunk_overlap = kwargs.get("chunk_overlap", 200)
                self.embeddings = None
                self.vectorstore = None

            def retrieve(self, query: str, k: int = 5):
                return []

            def retrieve_with_scores(self, query: str, k: int = 5):
                return []

            def add_documents(self, documents):
                return None

            def rebuild_index(self):
                return None

            def get_stats(self):
                return {"status": "mocked", "document_count": 0}

        rag_mod.RAGRetriever = FakeRAGRetriever
    except Exception:
        # If module not present or import fails, ignore and let tests fail later if necessary
        pass
