import sys

checks = [
    ("import langchain", "import langchain"),
    (
        "from langchain_core.documents import Document",
        "from langchain_core.documents import Document",
    ),
    (
        "from langchain_text_splitters import RecursiveCharacterTextSplitter",
        "from langchain_text_splitters import RecursiveCharacterTextSplitter",
    ),
    (
        "from langchain_community.vectorstores import FAISS",
        "from langchain_community.vectorstores import FAISS",
    ),
    (
        "from langchain_community.embeddings import SentenceTransformerEmbeddings",
        "from langchain_community.embeddings import SentenceTransformerEmbeddings",
    ),
    (
        "from langchain_openai import OpenAIEmbeddings",
        "from langchain_openai import OpenAIEmbeddings",
    ),
]

if __name__ == "__main__":
    for desc, code in checks:
        try:
            exec(code, {})
            print(f"OK: {desc}")
        except Exception as e:
            print(f"FAIL: {desc} -> {e.__class__.__name__}: {e}")
    sys.exit(0)
