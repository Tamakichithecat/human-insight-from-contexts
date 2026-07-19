from __future__ import annotations

from hifc.prompts.persona.rubrics import DIMENSION_LABELS
from hifc.schemas.persona import Claim, Evidence, Persona
from hifc.schemas.source import SourceDocument

_DIMENSION_FIELDS = (
    "core_values",
    "decision_making",
    "behavioral_patterns",
    "needs_concerns",
    "communication_style",
)


def persona_to_markdown(
    persona: Persona,
    sources: dict[str, SourceDocument],
    evidence: dict[str, Evidence],
) -> str:
    lines: list[str] = [
        f"# Persona: {persona.person_id} (v{persona.persona_version})",
        "",
        f"- generated_at: {persona.generated_at.isoformat()}",
        f"- generator: {persona.generator.model_id} "
        f"(prompt_version={persona.generator.prompt_version}, "
        f"pipeline_version={persona.generator.pipeline_version})",
        f"- sources: {len(persona.source_manifest)}",
        "",
    ]

    for field_name in _DIMENSION_FIELDS:
        claims: list[Claim] = getattr(persona, field_name)
        lines.append(f"## {DIMENSION_LABELS[field_name]}")
        lines.append("")
        if not claims:
            lines.append("_(該当する claim なし)_")
            lines.append("")
            continue
        for claim in claims:
            lines.append(f"### {claim.statement}")
            lines.append(
                f"- claim_id: `{claim.claim_id}` / theory_tag: `{claim.theory_tag}`"
            )
            confidence = claim.confidence
            lines.append(
                f"- confidence: **{confidence.band}** (score={confidence.score:.2f}, "
                f"n_evidence={confidence.n_evidence}, n_sources={confidence.n_sources}, "
                f"single_source={confidence.single_source}, "
                f"contradiction_present={confidence.contradiction_present})"
            )
            if claim.temporal_note:
                lines.append(f"- temporal_note: {claim.temporal_note}")
            lines.append("- evidence:")
            for evidence_id in claim.evidence_refs:
                item = evidence.get(evidence_id)
                if item is None:
                    continue
                source = sources.get(item.source_id)
                origin = source.origin if source else "unknown"
                lines.append(
                    f"  - [{item.stance}/{item.directness}] \"{item.quote}\" "
                    f"(source: {item.source_id}, origin: {origin}, locator: {item.locator})"
                )
            lines.append("")

    if persona.information_gaps:
        lines.append("## Information Gaps")
        lines.append("")
        for gap in persona.information_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    return "\n".join(lines)
