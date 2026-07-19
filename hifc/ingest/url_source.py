from __future__ import annotations

import ipaddress
import json
import socket
from datetime import date
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from hifc.ingest.build import build_source_document
from hifc.ingest.errors import IngestError
from hifc.schemas import SourceDocument
from hifc.schemas.source import AuthorPerspective, SourceType

_TIMEOUT_SECONDS = 30.0
_MAX_REDIRECTS = 5
_ALLOWED_SCHEMES = {"http", "https"}
# A generic UA (e.g. "hifc-ingest/0.1") gets 403'd by sites like Wikipedia that
# block non-browser clients; a common desktop browser UA avoids that.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class UnsafeUrlError(IngestError):
    """Raised when a URL targets a non-public/internal network address (SSRF guard)."""


def _reject_non_public_addresses(hostname: str, url: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError as exc:
        raise UnsafeUrlError(f"Could not resolve host {hostname!r} for {url}: {exc}") from exc

    for info in infos:
        address = info[4][0]
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(
                f"Refusing to fetch {url}: host {hostname!r} resolves to "
                f"non-public address {address}"
            )


def _validate_public_url(url: str) -> None:
    """Guard against SSRF: only allow http(s) requests to publicly-routable hosts.

    Ingest URLs come from the operator pasting a link (possibly one shared by a
    third party), so a malicious/shortened URL could otherwise point the fetcher at
    localhost, RFC1918 ranges, or a cloud metadata endpoint (169.254.169.254).
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Unsupported URL scheme {parsed.scheme!r} in {url} (http/https only)")
    if not parsed.hostname:
        raise UnsafeUrlError(f"URL has no hostname: {url}")
    _reject_non_public_addresses(parsed.hostname, url)


def fetch_html(url: str, *, timeout_seconds: float = _TIMEOUT_SECONDS) -> str:
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        _validate_public_url(current_url)
        try:
            response = httpx.get(
                current_url,
                timeout=timeout_seconds,
                follow_redirects=False,
                headers={"User-Agent": _USER_AGENT},
            )
        except httpx.HTTPError as exc:
            raise IngestError(f"Failed to fetch URL {current_url}: {exc}") from exc

        if response.has_redirect_location:
            current_url = urljoin(current_url, response.headers["location"])
            continue

        response.raise_for_status()
        return response.text

    raise IngestError(f"Too many redirects starting from {url}")


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
