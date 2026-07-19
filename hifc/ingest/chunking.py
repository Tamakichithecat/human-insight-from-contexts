from __future__ import annotations

import re

from hifc.schemas import Chunk

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？.!?])\s*")
_SENTENCES_PER_CHUNK = 3
_LONG_PARAGRAPH_CHARS = 400


def split_into_chunks(source_id: str, raw_text: str) -> list[Chunk]:
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(raw_text) if p.strip()]
    if len(paragraphs) > 1:
        return [
            Chunk(chunk_id=f"{source_id}-p{i}", text=text, locator=f"paragraph:{i}")
            for i, text in enumerate(paragraphs, start=1)
        ]

    single_text = paragraphs[0] if paragraphs else raw_text.strip()
    if not single_text:
        return []
    if len(single_text) <= _LONG_PARAGRAPH_CHARS:
        return [Chunk(chunk_id=f"{source_id}-p1", text=single_text, locator="paragraph:1")]

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(single_text) if s.strip()]
    chunks: list[Chunk] = []
    for i in range(0, len(sentences), _SENTENCES_PER_CHUNK):
        group = sentences[i : i + _SENTENCES_PER_CHUNK]
        chunk_index = i // _SENTENCES_PER_CHUNK + 1
        chunks.append(
            Chunk(
                chunk_id=f"{source_id}-s{chunk_index}",
                text=" ".join(group),
                locator=f"sentence:{chunk_index}",
            )
        )
    return chunks


def locate_quote(chunks: list[Chunk], quote: str) -> str | None:
    normalized_quote = _normalize(quote)
    if not normalized_quote:
        return None
    for chunk in chunks:
        if normalized_quote in _normalize(chunk.text):
            return chunk.locator
    return None


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()
