"""Extract text from PDF resumes."""

from pathlib import Path

from pypdf import PdfReader


def load_resume_text(path: str | Path) -> str:
    """Return the concatenated text extracted from every PDF page."""
    resume_path = Path(path)

    reader = PdfReader(resume_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)
