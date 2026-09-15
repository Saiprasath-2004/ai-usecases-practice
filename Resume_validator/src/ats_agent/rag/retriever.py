"""Utilities for chunking job descriptions and creating retrievers."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_jd(document: Document) -> list[Document]:
    """Split a job description into overlapping retrieval chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    return splitter.split_documents([document])


def get_retriever(vectorstore):
    """Create a retriever that returns the four most relevant chunks."""
    return vectorstore.as_retriever(search_kwargs={"k": 4})
