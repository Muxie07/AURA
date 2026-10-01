import math
from typing import Any


class DocumentChunker:
    """
    Configurable document chunking logic using recursive character splitting.
    """

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 256):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        separator = separators[0]
        for sep in separators:
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: list[str] = []
        _separator = separator if separator is not None else ""
        for s in splits:
            if good_splits:
                good_splits.append(_separator + s)
            else:
                good_splits.append(s)

        merged_chunks = []
        current_chunk: list[str] = []
        current_length = 0

        for split in good_splits:
            split_len = len(split)
            if current_length + split_len > self.chunk_size and current_length > 0:
                merged_chunks.append("".join(current_chunk))

                # Backtrack for overlap
                overlap_length = 0
                overlap_chunk: list[str] = []
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > self.chunk_overlap:
                        break
                    overlap_chunk.insert(0, s)
                    overlap_length += len(s)

                current_chunk = overlap_chunk
                current_length = overlap_length

            current_chunk.append(split)
            current_length += split_len

        if current_chunk:
            merged_chunks.append("".join(current_chunk))

        # Recursively split chunks that are still too large
        final_chunks = []
        next_separators = separators[1:] if len(separators) > 1 else [""]
        for chunk in merged_chunks:
            if len(chunk) > self.chunk_size and next_separators != [""]:
                final_chunks.extend(self._split_text(chunk, next_separators))
            else:
                final_chunks.append(chunk)

        return final_chunks

    def chunk(self, text: str, document_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Splits text into chunks and attaches metadata.
        Returns a list of dicts: {"content": str, "metadata": dict}
        """
        if not text:
            return []

        raw_chunks = self._split_text(text, self.separators)
        chunks = []
        text_length = len(text)
        current_pos = 0

        chunk_idx = 0
        for chunk_content in raw_chunks:
            chunk_content = chunk_content.strip()
            if not chunk_content:
                continue

            chunk_meta = document_metadata.copy()
            chunk_meta["chunk_index"] = chunk_idx

            # Find approximate position in original text (just for page estimation)
            pos = text.find(chunk_content[:20], current_pos)
            if pos != -1:
                current_pos = pos
            progress = current_pos / text_length if text_length > 0 else 0

            if (
                "pages" in chunk_meta
                and isinstance(chunk_meta["pages"], int)
                and chunk_meta["pages"] > 0
            ):
                approx_page = max(1, math.ceil(progress * chunk_meta["pages"]))
                chunk_meta["approx_page"] = approx_page

            chunks.append({"content": chunk_content, "metadata": chunk_meta})
            chunk_idx += 1

        return chunks
