from __future__ import annotations

from hashlib import sha256


def source_content_hash(raw_text: str) -> str:
    """Return the canonical SHA-256 content hash for a source document."""
    return sha256(raw_text.encode("utf-8")).hexdigest()

