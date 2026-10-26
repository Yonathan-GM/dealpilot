"""Ingest every document in data/synthetic/docs into the database.

Run from the project root:  python -m scripts.ingest_docs
Safe to run again: each file replaces its previous version.
"""
from pathlib import Path

from app.services.extract import SUPPORTED
from app.services.ingestion import ingest_file

DOCS_DIR = Path("data/synthetic/docs")


def guess_doc_type(filename: str) -> str:
    name = filename.lower()
    if name.startswith("spec_"):
        return "spec"
    if "catalog" in name:
        return "catalog"
    if "faq" in name:
        return "faq"
    if "pricing" in name or "terms" in name:
        return "policy"
    return "other"


def main() -> None:
    files = sorted(p for p in DOCS_DIR.iterdir() if p.suffix.lower() in SUPPORTED)
    if not files:
        print(f"No documents found in {DOCS_DIR}")
        return
    total = 0
    for path in files:
        count = ingest_file(path, doc_type=guess_doc_type(path.name))
        total += count
        print(f"{path.name:35} -> {count} chunks")
    print(f"Done. {len(files)} documents, {total} chunks.")


if __name__ == "__main__":
    main()
