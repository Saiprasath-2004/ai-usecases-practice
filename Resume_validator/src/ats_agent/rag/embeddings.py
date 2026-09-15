"""Embedding model factory used by the job-description retriever."""

from langchain_huggingface import HuggingFaceEmbeddings


def get_embedding_model() -> HuggingFaceEmbeddings:
    """Create the configured local sentence-embedding model."""
    return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
