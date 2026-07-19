from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from hifc.ingest.build import build_source_document
from hifc.ingest.errors import IngestError
from hifc.schemas import SourceDocument
from hifc.schemas.source import AuthorPerspective, SourceType


def load_csv_sources(
    path: Path | str,
    *,
    person_id: str,
    default_source_type: SourceType | None = None,
    default_author_perspective: AuthorPerspective | None = None,
    default_language: str = "ja",
) -> list[SourceDocument]:
    """Batch-ingest one snippet per row. Columns: text, date, source_type, origin,
    author_perspective, title. Missing source_type/author_perspective fall back to the
    CLI-supplied defaults (DESIGN.md §4.2)."""
    csv_path = Path(path)
    sources: list[SourceDocument] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):
            text = (row.get("text") or "").strip()
            if not text:
                continue

            source_type = (row.get("source_type") or "").strip() or default_source_type
            if not source_type:
                raise IngestError(
                    f"{csv_path}:{row_number}: missing source_type and no default given"
                )

            author_perspective = (
                row.get("author_perspective") or ""
            ).strip() or default_author_perspective
            if not author_perspective:
                raise IngestError(
                    f"{csv_path}:{row_number}: missing author_perspective and no default given"
                )

            raw_date = (row.get("date") or "").strip()
            published_at: date | None = None
            if raw_date:
                try:
                    published_at = date.fromisoformat(raw_date)
                except ValueError as exc:
                    raise IngestError(
                        f"{csv_path}:{row_number}: invalid date {raw_date!r}"
                    ) from exc

            origin = (row.get("origin") or "").strip() or f"csv:{csv_path.name}:row{row_number}"
            title = (row.get("title") or "").strip() or None

            sources.append(
                build_source_document(
                    person_id=person_id,
                    raw_text=text,
                    source_type=source_type,  # type: ignore[arg-type]
                    origin=origin,
                    author_perspective=author_perspective,  # type: ignore[arg-type]
                    title=title,
                    published_at=published_at,
                    language=default_language,
                )
            )
    return sources
