from __future__ import annotations


class IngestError(RuntimeError):
    pass


class YoutubeTranscriptUnavailable(IngestError):
    """Raised when a YouTube transcript cannot be fetched.

    Callers must fall back to manual paste ingestion (DESIGN.md §9 risk 1).
    """
