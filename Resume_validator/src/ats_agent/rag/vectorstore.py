"""Chroma persistence and deduplication helpers."""

from langchain_chroma import Chroma

from ats_agent.rag.embeddings import get_embedding_model

COLLECTION_NAME = "job_description"
PERSIST_DIRECTORY = "./vectorstore"


def create_vectorstore(chunks) -> Chroma:
    """Create or reuse the persisted Chroma collection for JD chunks."""

    embeddings = get_embedding_model()

    vectorstore = Chroma(
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIRECTORY,
    )

    existing = vectorstore.get(include=["documents"])

    if not existing["ids"]:
        vectorstore.add_documents(
            chunks,
            ids=[f"jd-chunk-{index}" for index in range(len(chunks))],
        )
        print("JD documents added to Chroma")
    else:
        print("Existing JD found. Reusing Chroma.")

    return vectorstore


def remove_duplicate_documents(vectorstore) -> None:
    """Delete repeated document bodies from an existing vector store."""
    records = vectorstore.get(include=["documents"])
    seen = set()
    duplicate_ids = []

    for record_id, document in zip(records["ids"], records["documents"]):
        if document in seen:
            duplicate_ids.append(record_id)
        else:
            seen.add(document)

    if duplicate_ids:
        vectorstore.delete(ids=duplicate_ids)
