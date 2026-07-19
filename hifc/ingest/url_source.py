from __future__ import annotations

import json
from datetime import date

import httpx
import trafilatura

from hifc.ingest.build import build_source_document
from hifc.ingest.errors import IngestError
from hifc.schemas import SourceDocument
from hifc.schemas.source import AuthorPerspective, SourceType

_TIMEOUT_SECONDS = 30.0
# A generic UA (e.g. "hifc-ingest/0.1") gets 403'd by sites like Wikipedia that
# block non-browser clients; a common desktop browser UA avoids that.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch_html(url: str, *, timeout_seconds: float = _TIMEOUT_SECONDS) -> str:
    try:
        response = httpx.get(
            url,
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IngestError(f"Failed to fetch URL {url}: {exc}") from exc
    return response.text


def extract_article(html: str, url: str) -> dict:
    extracted = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        favor_precision=True,
    )
    if not extracted:
        raise IngestError(f"Could not extract article content from {url}")
    return json.loads(extracted)


def build_source_from_url(
    url: str,
    *,
    person_id: str,
    source_type: SourceType,
    author_perspective: AuthorPerspective,
    published_at: date | None = None,
    language: str | None = None,
) -> SourceDocument:
    html = fetch_html(url)
    return build_source_from_html(
        html,
        url,
        person_id=person_id,
        source_type=source_type,
        author_perspective=author_perspective,
        published_at=published_at,
        language=language,
    )


def build_source_from_html(
    html: str,
    url: str,
    *,
    person_id: str,
    source_type: SourceType,
    author_perspective: AuthorPerspective,
    published_at: date | None = None,
    language: str | None = None,
) -> SourceDocument:
    data = extract_article(html, url)
    text = (data.get("text") or "").strip()
    if not text:
        raise IngestError(f"Extracted article from {url} has no text")

    resolved_published_at = published_at
    if resolved_published_at is None and data.get("date"):
        try:
            resolved_published_at = date.fromisoformat(data["date"])
        except ValueError:
            resolved_published_at = None

    return build_source_document(
        person_id=person_id,
        raw_text=text,
        source_type=source_type,
        origin=url,
        author_perspective=author_perspective,
        title=data.get("title"),
        published_at=resolved_published_at,
        language=language or data.get("language") or "ja",
    )
