"""Load job description text from a file."""

from pathlib import Path


def load_job_description(path: str | Path) -> str:
    """Read and return the job description as plain text."""
    job_description_path = Path(path)

    if not job_description_path.is_file():
        raise FileNotFoundError(
            f"Job description file not found: {job_description_path}"
        )

    text = job_description_path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError(
            f"Job description file is empty: {job_description_path}"
        )

    return text