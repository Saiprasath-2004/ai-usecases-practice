"""Extract text from PDF resumes."""

from pathlib import Path

from pypdf import PdfReader


def load_resume_text(path: str | Path) -> str:
    """Extract and return text from all pages of a PDF resume."""
    resume_path = Path(path)

    if not resume_path.is_file():
        raise FileNotFoundError(
            f"Resume PDF not found: {resume_path}"
        )

    try:
        reader = PdfReader(resume_path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read resume PDF: {resume_path}"
        ) from exc

    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text()

        if text and text.strip():
            pages.append(text.strip())

    resume_text = "\n\n".join(pages).strip()

    if not resume_text:
        raise ValueError(
            f"Resume PDF contains no extractable text: {resume_path}"
        )

    return resume_text