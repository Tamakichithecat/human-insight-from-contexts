from __future__ import annotations

from hifc.ingest.chunking import locate_quote
from hifc.llm.backend import LLMBackend
from hifc.prompts.persona.extract_prompt import (
    EXTRACT_PROMPT_VERSION,
    ExtractionResult,
    build_extract_prompt,
)
from hifc.schemas.persona import Evidence
from hifc.schemas.source import SourceDocument
from hifc.storage.repository import quote_exists


def extract_evidence(source: SourceDocument, backend: LLMBackend) -> list[Evidence]:
    """Run one independent LLM extraction call for a single source (DESIGN.md §5).

    Items whose quote cannot be found verbatim in the source are dropped rather than
    saved, matching the "never silently persist broken data" principle in DESIGN.md §8.1.
    """
    prompt = build_extract_prompt(source)
    result = backend.complete(
        prompt, schema=ExtractionResult, prompt_version=EXTRACT_PROMPT_VERSION
    )

    evidence: list[Evidence] = []
    for item in result.items:
        if not quote_exists(item.quote, source.raw_text):
            continue
        locator = locate_quote(source.chunks, item.quote) or item.locator
        evidence.append(
            Evidence(
                evidence_id=f"{source.source_id}-ev{len(evidence) + 1:03d}",
                source_id=source.source_id,
                quote=item.quote,
                locator=locator,
                directness=item.directness,
                stance=item.stance,
                theory_tags=item.theory_tags,
                noted_bias=item.noted_bias,
            )
        )
    return evidence
