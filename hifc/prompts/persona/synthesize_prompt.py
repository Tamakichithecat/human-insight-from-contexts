from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hifc.prompts.persona.rubrics import DIMENSION_TAGS, dimension_rubric_text
from hifc.schemas.persona import Evidence

SYNTHESIZE_PROMPT_VERSION = "persona-synthesize-v1"


class SynthesizedClaimItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    theory_tag: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    temporal_note: str | None = None


class SynthesisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[SynthesizedClaimItem] = Field(default_factory=list)


def build_synthesize_claim_schema(dimension: str) -> type[SynthesisResult]:
    allowed_tags = DIMENSION_TAGS[dimension]

    class _DimensionSynthesizedClaimItem(SynthesizedClaimItem):
        @field_validator("theory_tag")
        @classmethod
        def theory_tag_in_dimension(cls, value: str) -> str:
            if value not in allowed_tags:
                raise ValueError(f"theory_tag {value!r} is not part of dimension vocabulary")
            return value

    class _DimensionSynthesisResult(SynthesisResult):
        claims: list[_DimensionSynthesizedClaimItem] = Field(default_factory=list)

    return _DimensionSynthesisResult


def build_synthesize_prompt(
    dimension: str,
    evidence_items: list[tuple[str, Evidence]],
) -> str:
    evidence_lines = "\n".join(
        f"- evidence_id={evidence_id} | theory_tags={evidence.theory_tags} | "
        f"stance={evidence.stance} | directness={evidence.directness} | quote: {evidence.quote}"
        for evidence_id, evidence in evidence_items
    )
    return (
        "あなたは複数の根拠(evidence)から、人物のペルソナ次元に関する結論(claim)を合成する"
        "アナリストです。\n\n"
        f"対象ペルソナ次元: {dimension}\n"
        "以下のルーブリックの理論タグの中から、各 claim に最も当てはまる1つを"
        " theory_tag として選んでください。\n"
        f"{dimension_rubric_text(dimension)}\n\n"
        "以下は、このペルソナ次元に関連付けられた根拠の一覧です。evidence_id は"
        "必ずこの一覧から選び、存在しない evidence_id を作らないでください。"
        "矛盾する根拠がある場合は無視せず、矛盾を踏まえた claim にするか、"
        "矛盾している旨を statement に含めてください。\n"
        f"{evidence_lines}\n\n"
        "各 claim には以下を含めてください:\n"
        "- statement: 日本語で、この人物についての結論を簡潔に記述する\n"
        "- theory_tag: 上記ルーブリックの語彙から1つ\n"
        "- evidence_ids: この claim を支持する evidence_id のリスト"
        "(上記一覧に存在するもののみ、1件以上)\n"
        "- temporal_note: 情報が特定の時期に限定される場合の注記"
        "(例: '2023年以前の情報のみ')。なければ null\n\n"
        "根拠が薄い場合でも無理に claim を作らず、"
        "十分な根拠がある場合のみ claim を出力してください。"
    )
