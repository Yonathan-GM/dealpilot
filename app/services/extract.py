"""Read the text out of a file: .md, .txt, .pdf or .docx."""
from pathlib import Path

SUPPORTED = {".md", ".txt", ".pdf", ".docx"}


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        return "\n\n".join(p.text for p in document.paragraphs)
    raise ValueError(f"Unsupported file type: {suffix}")
