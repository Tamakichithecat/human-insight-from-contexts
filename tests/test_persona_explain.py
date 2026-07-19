from __future__ import annotations

import pytest

from hifc.persona import ClaimNotFoundError, explain_claim, format_claim_explanation
from hifc.storage import DataRepository


def test_explain_claim_traces_claim_to_evidence_and_source(
    tmp_path, sample_persona, sample_sources, sample_evidence
):
    repo = DataRepository(root=tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence(sample_persona.person_id, sample_evidence)
    repo.write_persona(sample_persona)

    claim_id = sample_persona.core_values[0].claim_id
    explanation = explain_claim(sample_persona.person_id, claim_id, repo=repo)

    assert explanation.claim.claim_id == claim_id
    assert len(explanation.evidence) == len(sample_evidence)
    assert all(item.source is not None for item in explanation.evidence)

    text = format_claim_explanation(explanation)
    assert claim_id in text
    assert sample_evidence[0].quote in text


def test_explain_claim_raises_for_unknown_claim_id(
    tmp_path, sample_persona, sample_sources, sample_evidence
):
    repo = DataRepository(root=tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence(sample_persona.person_id, sample_evidence)
    repo.write_persona(sample_persona)

    with pytest.raises(ClaimNotFoundError):
        explain_claim(sample_persona.person_id, "does-not-exist", repo=repo)
