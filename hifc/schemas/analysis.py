from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from hifc.schemas.common import GeneratorInfo, SafeId, StrictBaseModel
from hifc.schemas.persona import Confidence


class Interpretation(StrictBaseModel):
    statement: str = Field(min_length=1)
    surface_meaning: str = Field(min_length=1)
    inferred_intent: str = Field(min_length=1)
    supporting_claim_ids: list[SafeId] = Field(min_length=1)
    confidence: Confidence
    misread_risk: str = Field(min_length=1)

    @field_validator("supporting_claim_ids")
    @classmethod
    def supporting_claim_ids_are_non_empty(cls, value: list[str]) -> list[str]:
        if any(not ref.strip() for ref in value):
            raise ValueError("supporting_claim_ids must not contain blank values")
        return value


class NextAction(StrictBaseModel):
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    interpretation_refs: list[SafeId] = Field(min_length=1)
    prediction_id: SafeId
    verifiable: bool


class AnalysisReport(StrictBaseModel):
    person_id: SafeId
    persona_version: int = Field(ge=1)
    meeting_source_id: SafeId
    interpretations: list[Interpretation] = Field(min_length=1)
    overall_reading: str = Field(min_length=1)
    next_actions: list[NextAction] = Field(default_factory=list)
    risk_alerts: list[str] = Field(default_factory=list)
    generated_at: datetime
    generator: GeneratorInfo
