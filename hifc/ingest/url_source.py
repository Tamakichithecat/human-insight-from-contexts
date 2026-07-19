from __future__ import annotations

import ipaddress
import json
import socket
import threading
from contextlib import contextmanager
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

# Guards the socket.getaddrinfo monkeypatch in _pinned_resolution below so two
# ingest calls can never interleave their pins if this is ever used from threads.
_resolution_lock = threading.Lock()


class UnsafeUrlError(IngestError):
    """Raised when a URL targets a non-public/internal network address (SSRF guard)."""


def _is_public_address(address: str) -> bool:
    """Allowlist a resolved address as safe to connect to.

    A denylist of specific ranges (private/loopback/link-local/reserved/...)
    misses anything not explicitly enumerated — e.g. CGNAT/shared address space
    (100.64.0.0/10, RFC 6598) is not `is_private` in Python's ipaddress module,
    nor are IETF protocol assignments, TEST-NET ranges, or benchmarking space.
    `is_global` is itself an allowlist (true only for addresses that are
    actually publicly routable), so use that instead and additionally exclude
    multicast, which `is_global` alone does not rule out.
    """
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_multicast


def _resolve_public_addresses(hostname: str, url: str) -> list[tuple]:
    try:
        # Restrict to TCP/SOCK_STREAM: that's what socket.create_connection
        # requests when httpx connects, and it also avoids duplicate UDP/RAW
        # entries for the same address that would otherwise get pinned too.
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except OSError as exc:
        raise UnsafeUrlError(f"Could not resolve host {hostname!r} for {url}: {exc}") from exc
    if not infos:
        raise UnsafeUrlError(f"Host {hostname!r} did not resolve to any address for {url}")

    for info in infos:
        address = info[4][0]
        if not _is_public_address(address):
            raise UnsafeUrlError(
                f"Refusing to fetch {url}: host {hostname!r} resolves to "
                f"non-public address {address}"
            )
    return infos


def _validate_public_url(url: str) -> tuple[str, list[tuple]]:
    """Guard against SSRF: only allow http(s) requests to publicly-routable hosts.

    Ingest URLs come from the operator pasting a link (possibly one shared by a
    third party), so a malicious/shortened URL could otherwise point the fetcher at
    localhost, RFC1918 ranges, or a cloud metadata endpoint (169.254.169.254).

    Returns the hostname and the addrinfo that was validated, so the caller can
    pin the actual TCP connection to these exact addresses via
    `_pinned_resolution` — resolving the hostname again at connect time would
    reopen a DNS-rebinding gap between validation and connection.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Unsupported URL scheme {parsed.scheme!r} in {url} (http/https only)")
    if not parsed.hostname:
        raise UnsafeUrlError(f"URL has no hostname: {url}")
    return parsed.hostname, _resolve_public_addresses(parsed.hostname, url)


@contextmanager
def _pinned_resolution(hostname: str, addrinfo: list[tuple]):
    """Force `socket.getaddrinfo` to resolve `hostname` to the pre-validated
    `addrinfo` for the duration of the request.

    httpx's sync transport connects via `socket.create_connection`, which calls
    `socket.getaddrinfo` again at connect time. Without pinning, a DNS-rebinding
    attacker could return a public address for the validation lookup above and a
    private one for this second lookup, bypassing the SSRF guard entirely.
    """
    original_getaddrinfo = socket.getaddrinfo

    def pinned(host, port, *args, **kwargs):
        if host != hostname:
            return original_getaddrinfo(host, port, *args, **kwargs)
        resolved_port = port if isinstance(port, int) else 0
        return [
            (family, socktype, proto, canonname, (sockaddr[0], resolved_port, *sockaddr[2:]))
            for family, socktype, proto, canonname, sockaddr in addrinfo
        ]

    with _resolution_lock:
        socket.getaddrinfo = pinned
        try:
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo


def fetch_html(url: str, *, timeout_seconds: float = _TIMEOUT_SECONDS) -> str:
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        hostname, addrinfo = _validate_public_url(current_url)
        try:
            with _pinned_resolution(hostname, addrinfo):
                response = httpx.get(
                    current_url,
                    timeout=timeout_seconds,
                    follow_redirects=False,
                    headers={"User-Agent": _USER_AGENT},
                )
                if response.has_redirect_location:
                    current_url = urljoin(current_url, response.headers["location"])
                    continue
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IngestError(f"Failed to fetch URL {current_url}: {exc}") from exc
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
