from __future__ import annotations

from datetime import date, datetime

from hifc.llm.backend import LLMBackend
from hifc.prompts.persona.rubrics import DIMENSION_TAGS
from hifc.prompts.persona.synthesize_prompt import (
    SYNTHESIZE_PROMPT_VERSION,
    build_synthesize_claim_schema,
    build_synthesize_prompt,
)
from hifc.schemas.persona import Claim, Evidence
from hifc.schemas.source import SourceDocument
from hifc.scoring import score_confidence


def synthesize_dimension_claims(
    dimension: str,
    evidence: dict[str, Evidence],
    sources: dict[str, SourceDocument],
    backend: LLMBackend,
    *,
    as_of: date | datetime,
) -> list[Claim]:
    """Synthesize claims for one persona dimension from its tagged evidence (DESIGN.md §5)."""
    allowed_tags = DIMENSION_TAGS[dimension]
    relevant = {
        evidence_id: item
        for evidence_id, item in evidence.items()
        if allowed_tags.intersection(item.theory_tags)
    }
    if not relevant:
        return []

    prompt = build_synthesize_prompt(dimension, list(relevant.items()))
    schema = build_synthesize_claim_schema(dimension)
    result = backend.complete(prompt, schema=schema, prompt_version=SYNTHESIZE_PROMPT_VERSION)

    claims: list[Claim] = []
    for claim_item in result.claims:
        valid_evidence_ids = [eid for eid in claim_item.evidence_ids if eid in relevant]
        if not valid_evidence_ids:
            continue
        confidence = score_confidence(
            valid_evidence_ids,
            evidence=relevant,
            sources=sources,
            as_of=as_of,
        )
        claims.append(
            Claim(
                claim_id=f"claim-{dimension}-{len(claims) + 1:03d}",
                statement=claim_item.statement,
                theory_tag=claim_item.theory_tag,
                confidence=confidence,
                evidence_refs=valid_evidence_ids,
                temporal_note=claim_item.temporal_note,
            )
        )
    return claims
