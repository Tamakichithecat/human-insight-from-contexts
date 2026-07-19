from __future__ import annotations

from datetime import UTC, date, datetime

from hifc.ingest.chunking import split_into_chunks
from hifc.schemas import SourceDocument
from hifc.schemas.source import AuthorPerspective, SourceType
from hifc.storage import source_content_hash

_SOURCE_ID_HASH_CHARS = 16


def source_id_from_text(raw_text: str) -> str:
    """Derive a stable, content-hash-based source_id (DESIGN.md §4.1: dedup by content)."""
    return f"src-{source_content_hash(raw_text)[:_SOURCE_ID_HASH_CHARS]}"


def build_source_document(
    *,
    person_id: str,
    raw_text: str,
    source_type: SourceType,
    origin: str,
    author_perspective: AuthorPerspective,
    title: str | None = None,
    published_at: date | None = None,
    language: str = "ja",
    retrieved_at: datetime | None = None,
) -> SourceDocument:
    normalized_text = raw_text.strip()
    if not normalized_text:
        raise ValueError("raw_text must not be empty")
    source_id = source_id_from_text(normalized_text)
    return SourceDocument(
        source_id=source_id,
        person_id=person_id,
        content_hash=source_content_hash(normalized_text),
        source_type=source_type,
        origin=origin,
        title=title,
        author_perspective=author_perspective,
        published_at=published_at,
        retrieved_at=retrieved_at or datetime.now(UTC),
        language=language,
        raw_text=normalized_text,
        chunks=split_into_chunks(source_id, normalized_text),
    )
