from __future__ import annotations

from datetime import UTC, datetime

from hifc.llm import MockBackend
from hifc.persona.synthesize import synthesize_dimension_claims
from hifc.prompts.persona.synthesize_prompt import SynthesisResult, SynthesizedClaimItem
from hifc.schemas.persona import Evidence


def _evidence(evidence_id: str, source_id: str, theory_tags: list[str]) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        source_id=source_id,
        quote="サンプル引用",
        locator="paragraph:1",
        directness="direct_statement",
        stance="supports",
        theory_tags=theory_tags,
    )


def test_synthesize_dimension_claims_skips_llm_call_when_no_relevant_evidence(sample_sources):
    evidence = {"ev-1": _evidence("ev-1", sample_sources[0].source_id, ["scarf:autonomy"])}
    backend = MockBackend([])

    claims = synthesize_dimension_claims(
        "core_values",
        evidence,
        {s.source_id: s for s in sample_sources},
        backend,
        as_of=datetime.now(UTC),
    )

    assert claims == []
    assert backend.calls == []


def test_synthesize_dimension_claims_scores_and_drops_hallucinated_refs(sample_sources):
    source = sample_sources[0]
    evidence = {
        "ev-1": _evidence("ev-1", source.source_id, ["schwartz:self_direction"]),
        "ev-2": _evidence("ev-2", source.source_id, ["schwartz:achievement"]),
    }
    response = SynthesisResult(
        claims=[
            SynthesizedClaimItem(
                statement="自律性を重視する。",
                theory_tag="schwartz:self_direction",
                evidence_ids=["ev-1"],
            ),
            SynthesizedClaimItem(
                statement="存在しない根拠を参照する claim。",
                theory_tag="schwartz:achievement",
                evidence_ids=["ev-does-not-exist"],
            ),
        ]
    )
    backend = MockBackend([response])

    claims = synthesize_dimension_claims(
        "core_values",
        evidence,
        {source.source_id: source},
        backend,
        as_of=datetime.now(UTC),
    )

    assert len(claims) == 1
    claim = claims[0]
    assert claim.theory_tag == "schwartz:self_direction"
    assert claim.evidence_refs == ["ev-1"]
    assert claim.confidence.n_evidence == 1
    assert backend.calls[0]["prompt_version"] == "persona-synthesize-v1"
