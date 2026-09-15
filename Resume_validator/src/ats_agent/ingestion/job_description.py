"""Load job descriptions into LangChain document objects."""

from pathlib import Path

from langchain_core.documents import Document


def load_job_description(path: str | Path) -> Document:
    """Read a UTF-8 job description and attach its source path as metadata."""
    job_description_path = Path(path)
    text = job_description_path.read_text(encoding="utf-8")

    return Document(
        page_content=text,
        metadata={"source": str(job_description_path)},
    )
