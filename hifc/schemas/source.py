from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from hifc.schemas.common import ContentHash, SafeId, StrictBaseModel

SourceType = Literal[
    "blog",
    "interview",
    "news",
    "video_transcript",
    "sns",
    "book",
    "meeting_note",
    "other",
]

AuthorPerspective = Literal["first_person", "third_party"]


class Chunk(StrictBaseModel):
    chunk_id: SafeId
    text: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class SourceDocument(StrictBaseModel):
    source_id: SafeId
    person_id: SafeId
    content_hash: ContentHash
    source_type: SourceType
    origin: str = Field(min_length=1)
    title: str | None = None
    author_perspective: AuthorPerspective
    published_at: date | None = None
    retrieved_at: datetime
    language: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    chunks: list[Chunk] = Field(default_factory=list)
