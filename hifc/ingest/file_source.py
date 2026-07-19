from __future__ import annotations

from datetime import date
from pathlib import Path

import pdfplumber

from hifc.ingest.build import build_source_document
from hifc.ingest.errors import IngestError
from hifc.schemas import SourceDocument
from hifc.schemas.source import AuthorPerspective, SourceType

_TEXT_SUFFIXES = {".txt", ".md"}
_PDF_SUFFIXES = {".pdf"}


def build_source_from_paste(
    *,
    person_id: str,
    raw_text: str,
    source_type: SourceType,
    author_perspective: AuthorPerspective,
    title: str | None = None,
    published_at: date | None = None,
    language: str = "ja",
) -> SourceDocument:
    return build_source_document(
        person_id=person_id,
        raw_text=raw_text,
        source_type=source_type,
        origin="paste",
        author_perspective=author_perspective,
        title=title,
        published_at=published_at,
        language=language,
    )


def build_source_from_file(
    path: Path | str,
    *,
    person_id: str,
    source_type: SourceType,
    author_perspective: AuthorPerspective,
    title: str | None = None,
    published_at: date | None = None,
    language: str = "ja",
) -> SourceDocument:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        raw_text = file_path.read_text(encoding="utf-8")
    elif suffix in _PDF_SUFFIXES:
        raw_text = extract_pdf_text(file_path)
    else:
        raise IngestError(f"Unsupported file type: {suffix or file_path.name}")

    return build_source_document(
        person_id=person_id,
        raw_text=raw_text,
        source_type=source_type,
        origin=str(file_path),
        author_perspective=author_perspective,
        title=title or file_path.stem,
        published_at=published_at,
        language=language,
    )


def extract_pdf_text(path: Path | str) -> str:
    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text:
        raise IngestError(f"No extractable text found in PDF: {path}")
    return text
