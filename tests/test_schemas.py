from __future__ import annotations

import pytest
from pydantic import ValidationError

from hifc.schemas import AnalysisReport, Claim, Interpretation, NextAction, Persona


def test_persona_round_trip(sample_persona):
    payload = sample_persona.model_dump_json()
    restored = Persona.model_validate_json(payload)
    assert restored == sample_persona
    assert restored.claims()[0].claim_id == "claim-1"


def test_claim_requires_evidence_ref(sample_persona):
    claim_payload = sample_persona.claims()[0].model_dump()
    claim_payload["evidence_refs"] = []
    with pytest.raises(ValidationError):
        Claim.model_validate(claim_payload)


def test_analysis_report_round_trip(sample_generator, sample_persona):
    report = AnalysisReport(
        person_id="person-1",
        persona_version=1,
        meeting_source_id="meeting-1",
        interpretations=[
            Interpretation(
                statement="検討します。",
                surface_meaning="内部で検討する。",
                inferred_intent="裁量を確保したい可能性がある。",
                supporting_claim_ids=["claim-1"],
                confidence=sample_persona.claims()[0].confidence,
                misread_risk="単なる先送りと誤読するリスク。",
            )
        ],
        overall_reading="自律性への配慮が必要。",
        next_actions=[
            NextAction(
                action="選択肢を提示する。",
                rationale="claim-1 と interpretation-1 に基づく。",
                interpretation_refs=["interpretation-1"],
                prediction_id="prediction-1",
                verifiable=True,
            )
        ],
        risk_alerts=["押し付けに見える表現を避ける。"],
        generated_at=sample_persona.generated_at,
        generator=sample_generator,
    )
    assert AnalysisReport.model_validate_json(report.model_dump_json()) == report

