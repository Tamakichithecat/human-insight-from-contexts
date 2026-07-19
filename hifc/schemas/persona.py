from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from hifc.schemas.common import GeneratorInfo, SafeId, SourceRef, StrictBaseModel

Directness = Literal["direct_statement", "observed_behavior", "third_party", "inferred"]
Stance = Literal["supports", "contradicts"]
ConfidenceBand = Literal["high", "medium", "low"]


class Evidence(StrictBaseModel):
    evidence_id: SafeId
    source_id: SafeId
    quote: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    directness: Directness
    stance: Stance
    theory_tags: list[str] = Field(min_length=1)
    noted_bias: str | None = None

    @field_validator("theory_tags")
    @classmethod
    def theory_tags_are_non_empty(cls, value: list[str]) -> list[str]:
        if any(not tag.strip() for tag in value):
            raise ValueError("theory_tags must not contain blank values")
        return value


class Confidence(StrictBaseModel):
    score: float = Field(ge=0.0, le=1.0)
    band: ConfidenceBand
    n_evidence: int = Field(ge=0)
    n_sources: int = Field(ge=0)
    single_source: bool
    contradiction_present: bool


class Claim(StrictBaseModel):
    claim_id: SafeId
    statement: str = Field(min_length=1)
    theory_tag: str = Field(min_length=1)
    confidence: Confidence
    evidence_refs: list[SafeId] = Field(min_length=1)
    temporal_note: str | None = None

    @field_validator("evidence_refs")
    @classmethod
    def evidence_refs_are_non_empty(cls, value: list[str]) -> list[str]:
        if any(not ref.strip() for ref in value):
            raise ValueError("evidence_refs must not contain blank values")
        return value


class Persona(StrictBaseModel):
    person_id: SafeId
    persona_version: int = Field(ge=1)
    generated_at: datetime
    generator: GeneratorInfo
    source_manifest: list[SourceRef] = Field(min_length=1)
    core_values: list[Claim] = Field(default_factory=list)
    decision_making: list[Claim] = Field(default_factory=list)
    behavioral_patterns: list[Claim] = Field(default_factory=list)
    needs_concerns: list[Claim] = Field(default_factory=list)
    communication_style: list[Claim] = Field(default_factory=list)
    information_gaps: list[str] = Field(default_factory=list)

    def claims(self) -> list[Claim]:
        return [
            *self.core_values,
            *self.decision_making,
            *self.behavioral_patterns,
            *self.needs_concerns,
            *self.communication_style,
        ]
