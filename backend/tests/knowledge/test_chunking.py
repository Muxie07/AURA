from app.knowledge.chunking import DocumentChunker


def test_chunker_basic():
    chunker = DocumentChunker(chunk_size=10, chunk_overlap=2)
    text = "012345678901234567890"  # 21 chars
    # chunks:
    # 0123456789
    # 8901234567
    # 67890

    chunks = chunker.chunk(text, {"doc": "1"})

    assert len(chunks) == 3
    assert chunks[0]["content"] == "0123456789"
    assert chunks[1]["content"] == "8901234567"
    assert chunks[2]["content"] == "67890"

    assert chunks[0]["metadata"]["chunk_index"] == 0
    assert chunks[1]["metadata"]["chunk_index"] == 1
    assert chunks[2]["metadata"]["chunk_index"] == 2
