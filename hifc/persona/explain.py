from __future__ import annotations

from dataclasses import dataclass

from hifc.schemas.persona import Claim, Evidence
from hifc.schemas.source import SourceDocument
from hifc.storage import DataRepository


class ClaimNotFoundError(LookupError):
    pass


@dataclass
class EvidenceExplanation:
    evidence: Evidence
    source: SourceDocument | None


@dataclass
class ClaimExplanation:
    claim: Claim
    evidence: list[EvidenceExplanation]


def explain_claim(
    person_id: str,
    claim_id: str,
    *,
    repo: DataRepository,
    version: int | None = None,
) -> ClaimExplanation:
    persona = repo.read_persona(person_id, version=version)
    claim = next((c for c in persona.claims() if c.claim_id == claim_id), None)
    if claim is None:
        raise ClaimNotFoundError(
            f"claim_id {claim_id!r} not found in persona {person_id} v{persona.persona_version}"
        )

    evidence_all = repo.read_evidence(person_id)
    sources = repo.read_sources(person_id)
    explanations = []
    for evidence_id in claim.evidence_refs:
        item = evidence_all.get(evidence_id)
        if item is None:
            continue
        explanations.append(
            EvidenceExplanation(evidence=item, source=sources.get(item.source_id))
        )
    return ClaimExplanation(claim=claim, evidence=explanations)


def format_claim_explanation(explanation: ClaimExplanation) -> str:
    claim = explanation.claim
    lines = [
        f"claim_id: {claim.claim_id}",
        f"theory_tag: {claim.theory_tag}",
        f"statement: {claim.statement}",
        f"confidence: {claim.confidence.band} (score={claim.confidence.score:.2f})",
    ]
    if claim.temporal_note:
        lines.append(f"temporal_note: {claim.temporal_note}")
    lines.append("evidence:")
    for item in explanation.evidence:
        origin = item.source.origin if item.source else "unknown"
        lines.append(
            f'  - [{item.evidence.stance}/{item.evidence.directness}] '
            f'"{item.evidence.quote}" (source: {item.evidence.source_id}, origin: {origin}, '
            f"locator: {item.evidence.locator})"
        )
    return "\n".join(lines)
