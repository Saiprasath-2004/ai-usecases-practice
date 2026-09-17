"""Embedding model used for semantic ATS matching."""

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    """Create and cache the local embedding model."""

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={
            "device": "cpu",
        },
        encode_kwargs={
            "normalize_embeddings": True,
        },
    )