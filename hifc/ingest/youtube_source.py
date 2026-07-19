from __future__ import annotations

import re
from datetime import date
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import CouldNotRetrieveTranscript

from hifc.ingest.build import build_source_document
from hifc.ingest.errors import YoutubeTranscriptUnavailable
from hifc.schemas import SourceDocument
from hifc.schemas.source import AuthorPerspective

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_SEGMENT_WINDOW_SECONDS = 45.0


def extract_video_id(url_or_id: str) -> str:
    candidate = url_or_id.strip()
    if _VIDEO_ID_RE.match(candidate):
        return candidate

    parsed = urlparse(candidate)
    if parsed.hostname in {"youtu.be"}:
        video_id = parsed.path.lstrip("/")
        if _VIDEO_ID_RE.match(video_id):
            return video_id
    if parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if _VIDEO_ID_RE.match(video_id):
                return video_id
        for prefix in ("/embed/", "/shorts/", "/live/"):
            if parsed.path.startswith(prefix):
                video_id = parsed.path[len(prefix) :]
                if _VIDEO_ID_RE.match(video_id):
                    return video_id

    raise YoutubeTranscriptUnavailable(f"Could not parse a YouTube video id from: {url_or_id}")


def fetch_transcript_entries(video_id: str, *, languages: list[str] | None = None) -> list[dict]:
    try:
        return YouTubeTranscriptApi.get_transcript(video_id, languages=languages or ["ja", "en"])
    except CouldNotRetrieveTranscript as exc:
        raise YoutubeTranscriptUnavailable(
            f"No transcript available for video {video_id}: {exc}. "
            "Fall back to `hifc ingest paste` with a manually copied transcript."
        ) from exc


def transcript_entries_to_text(entries: list[dict]) -> str:
    segments: list[list[str]] = []
    window_end = 0.0
    for entry in entries:
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        start = float(entry.get("start", 0.0))
        if not segments or start >= window_end:
            segments.append([])
            window_end = start + _SEGMENT_WINDOW_SECONDS
        segments[-1].append(text)
    return "\n\n".join(" ".join(segment) for segment in segments if segment)


def build_source_from_youtube(
    url_or_id: str,
    *,
    person_id: str,
    author_perspective: AuthorPerspective,
    published_at: date | None = None,
    language: str | None = None,
    languages: list[str] | None = None,
) -> SourceDocument:
    video_id = extract_video_id(url_or_id)
    entries = fetch_transcript_entries(video_id, languages=languages)
    raw_text = transcript_entries_to_text(entries)
    if not raw_text:
        raise YoutubeTranscriptUnavailable(f"Transcript for video {video_id} was empty")

    return build_source_document(
        person_id=person_id,
        raw_text=raw_text,
        source_type="video_transcript",
        origin=f"https://youtu.be/{video_id}",
        author_perspective=author_perspective,
        published_at=published_at,
        language=language or (languages[0] if languages else "ja"),
    )
