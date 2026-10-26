"""Split a document into chunks that are good for semantic search.

Design (explained in the README):
  1. Split the document into sections at Markdown headings.
  2. Inside each section, pack whole paragraphs into chunks up to `max_chars`.
  3. Prefix every chunk with "Document title > Section heading", so a chunk
     like a single price table row still carries the context it needs.

This module is pure Python (no API calls, no database), so it is easy to test.
"""
import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class Chunk:
    index: int      # position of the chunk inside the document
    heading: str    # section heading the chunk came from ("" if none)
    text: str       # final text that is embedded and stored (context + body)


def _split_sections(text: str, title: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (document_title, [(heading, body), ...])."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            level, heading = len(match.group(1)), match.group(2)
            if level == 1:
                title = heading  # the document's own title wins over the filename
            else:
                sections.append((heading, []))
            continue
        sections[-1][1].append(line)
    return title, [(h, "\n".join(lines).strip()) for h, lines in sections]


def _pack(units: list[str], separator: str, max_chars: int) -> list[str]:
    """Greedily join units with `separator` without exceeding max_chars."""
    packed: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}{separator}{unit}" if current else unit
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                packed.append(current)
            current = unit
    if current:
        packed.append(current)
    return packed


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Break an oversized paragraph (e.g. a big table) by line, then by word."""
    line_units: list[str] = []
    for line in paragraph.splitlines():
        if len(line) <= max_chars:
            line_units.append(line)
        else:
            line_units.extend(_pack(line.split(" "), " ", max_chars))
    return _pack(line_units, "\n", max_chars)


def _pack_paragraphs(body: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            units.extend(_split_long_paragraph(paragraph, max_chars))
        else:
            units.append(paragraph)
    return _pack(units, "\n\n", max_chars)


def chunk_text(text: str, title: str = "", max_chars: int = 800) -> list[Chunk]:
    """Turn a document's text into a list of Chunk objects."""
    doc_title, sections = _split_sections(text, title)
    chunks: list[Chunk] = []
    for heading, body in sections:
        if not body:
            continue
        context = f"{doc_title} > {heading}" if heading and doc_title else (heading or doc_title)
        for piece in _pack_paragraphs(body, max_chars):
            full_text = f"[{context}]\n{piece}" if context else piece
            chunks.append(Chunk(index=len(chunks), heading=heading, text=full_text))
    return chunks
