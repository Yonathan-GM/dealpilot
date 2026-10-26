from app.services.chunking import chunk_text

SAMPLE = """# Price Guide

Intro paragraph about the guide.

## Stretch Film

Product A costs $10 per roll.

Product B costs $12 per roll.

## Boxes

Product C costs $1 per box.
"""


def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunks_carry_title_and_heading_context():
    chunks = chunk_text(SAMPLE)
    film = [c for c in chunks if "Product A" in c.text][0]
    assert film.text.startswith("[Price Guide > Stretch Film]")
    assert film.heading == "Stretch Film"


def test_sections_are_not_mixed():
    chunks = chunk_text(SAMPLE)
    for c in chunks:
        assert not ("Product A" in c.text and "Product C" in c.text)


def test_chunks_respect_max_size():
    long_text = "# Doc\n\n## S\n\n" + "\n\n".join(f"Paragraph number {i} " + "x" * 200 for i in range(20))
    chunks = chunk_text(long_text, max_chars=500)
    assert len(chunks) > 1
    for c in chunks:
        body = c.text.split("\n", 1)[1]  # drop the "[context]" line
        assert len(body) <= 500


def test_oversized_paragraph_is_split():
    huge = "# Doc\n\n## S\n\n" + " ".join(["word"] * 1000)
    chunks = chunk_text(huge, max_chars=300)
    assert len(chunks) > 1
    assert all(len(c.text.split("\n", 1)[1]) <= 300 for c in chunks)


def test_indexes_are_sequential():
    chunks = chunk_text(SAMPLE, max_chars=40)
    assert [c.index for c in chunks] == list(range(len(chunks)))
