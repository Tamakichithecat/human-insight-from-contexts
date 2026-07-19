from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hifc.prompts.persona.rubrics import ALL_THEORY_TAGS, rubric_reference_text
from hifc.schemas.persona import Directness, Stance
from hifc.schemas.source import SourceDocument

EXTRACT_PROMPT_VERSION = "persona-extract-v1"


class ExtractedEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    directness: Directness
    stance: Stance
    theory_tags: list[str] = Field(min_length=1)
    noted_bias: str | None = None

    @field_validator("theory_tags")
    @classmethod
    def tags_are_known(cls, value: list[str]) -> list[str]:
        unknown = [tag for tag in value if tag not in ALL_THEORY_TAGS]
        if unknown:
            raise ValueError(f"Unknown theory_tags (not in rubric vocabulary): {unknown}")
        return value


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExtractedEvidenceItem] = Field(default_factory=list)


def build_extract_prompt(source: SourceDocument) -> str:
    chunk_lines = (
        "\n".join(f"[{chunk.locator}] {chunk.text}" for chunk in source.chunks)
        or source.raw_text
    )
    return (
        "あなたは心理学理論に基づいてテキストから根拠(evidence)を抽出するアナリストです。\n"
        f"対象人物 ID: {source.person_id}\n"
        f"ソース種別: {source.source_type} / 発言視点: {source.author_perspective}\n\n"
        "以下のルーブリック(理論タグと指標)に厳密に従い、テキストから根拠となる引用を抽出してください。\n"
        "各根拠には次を含めてください:\n"
        "- quote: 原文からの逐語的な引用(意訳・要約は不可)\n"
        "- locator: 引用元のロケータ(下記テキストの [ロケータ] 表記をそのまま使う)\n"
        "- directness: direct_statement(本人の直接言明) / observed_behavior(観測された行動) / "
        "third_party(第三者の証言) / inferred(間接推論) のいずれか\n"
        "- stance: 各理論タグの指標を supports(支持) するか contradicts(矛盾) するか\n"
        "- theory_tags: 下記ルーブリックの語彙から該当するものを1つ以上選ぶ(語彙外のタグは禁止)\n"
        "- noted_bias: 編集・感情バイアス等の注記があれば記載、なければ null\n\n"
        "テキストに明記されていないことを推測で補わないでください。1つの引用に複数の理論タグを付けてよい。\n\n"
        "## ルーブリック(理論タグ一覧)\n"
        f"{rubric_reference_text()}\n\n"
        "## テキスト(チャンク単位、[ロケータ] 形式)\n"
        f"{chunk_lines}\n"
    )
