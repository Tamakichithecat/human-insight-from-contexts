from __future__ import annotations

from datetime import date

import pytest

from hifc.ingest import build_source_from_paste
from hifc.llm import MockBackend
from hifc.persona import PersonaBuildError, build_persona
from hifc.prompts.persona.extract_prompt import ExtractedEvidenceItem, ExtractionResult
from hifc.prompts.persona.synthesize_prompt import SynthesisResult, SynthesizedClaimItem
from hifc.storage import DataRepository

SOURCE1_TEXT = (
    "私は常に新しいことに挑戦し、自分の裁量で意思決定することを大切にしている。"
    "将来のリスクよりも、まず一歩踏み出すことを優先する。"
)
SOURCE2_TEXT = (
    "会議では相手の意見をよく聞き、公平な合意を目指す。"
    "計画を綿密に立て、リスクを避けることを重視している。"
)


def _make_repo(tmp_path) -> DataRepository:
    return DataRepository(root=tmp_path / "data")


def _ingest_two_sources(repo: DataRepository):
    source1 = build_source_from_paste(
        person_id="taro",
        raw_text=SOURCE1_TEXT,
        source_type="blog",
        author_perspective="first_person",
        published_at=date(2026, 1, 1),
    )
    source2 = build_source_from_paste(
        person_id="taro",
        raw_text=SOURCE2_TEXT,
        source_type="interview",
        author_perspective="first_person",
        published_at=date(2026, 2, 1),
    )
    repo.write_source(source1)
    repo.write_source(source2)
    return source1, source2


def _extraction_result_for(source) -> ExtractionResult:
    if source.raw_text == SOURCE1_TEXT:
        return ExtractionResult(
            items=[
                ExtractedEvidenceItem(
                    quote="私は常に新しいことに挑戦し、自分の裁量で意思決定することを大切にしている。",
                    locator="paragraph:1",
                    directness="direct_statement",
                    stance="supports",
                    theory_tags=["schwartz:self_direction", "scarf:autonomy"],
                ),
                ExtractedEvidenceItem(
                    quote="将来のリスクよりも、まず一歩踏み出すことを優先する。",
                    locator="paragraph:1",
                    directness="direct_statement",
                    stance="supports",
                    theory_tags=["regulatory_focus:promotion", "bigfive:openness"],
                ),
            ]
        )
    return ExtractionResult(
        items=[
            ExtractedEvidenceItem(
                quote="会議では相手の意見をよく聞き、公平な合意を目指す。",
                locator="paragraph:1",
                directness="direct_statement",
                stance="supports",
                theory_tags=["scarf:fairness", "bigfive:agreeableness"],
            ),
            ExtractedEvidenceItem(
                quote="計画を綿密に立て、リスクを避けることを重視している。",
                locator="paragraph:1",
                directness="direct_statement",
                stance="supports",
                theory_tags=["regulatory_focus:prevention", "bigfive:conscientiousness"],
            ),
        ]
    )


def _synthesis_responses(source1_id: str, source2_id: str) -> list[SynthesisResult]:
    s1_ev1, s1_ev2 = f"{source1_id}-ev001", f"{source1_id}-ev002"
    s2_ev1, s2_ev2 = f"{source2_id}-ev001", f"{source2_id}-ev002"
    return [
        SynthesisResult(
            claims=[
                SynthesizedClaimItem(
                    statement="自律性と挑戦を重視する。",
                    theory_tag="schwartz:self_direction",
                    evidence_ids=[s1_ev1],
                )
            ]
        ),
        SynthesisResult(
            claims=[
                SynthesizedClaimItem(
                    statement="攻めの姿勢で行動する。",
                    theory_tag="regulatory_focus:promotion",
                    evidence_ids=[s1_ev2],
                ),
                SynthesizedClaimItem(
                    statement="慎重にリスクを避ける一面もある。",
                    theory_tag="regulatory_focus:prevention",
                    evidence_ids=[s2_ev2],
                ),
            ]
        ),
        SynthesisResult(
            claims=[
                SynthesizedClaimItem(
                    statement="新しい発想に開放的である。",
                    theory_tag="bigfive:openness",
                    evidence_ids=[s1_ev2],
                ),
                SynthesizedClaimItem(
                    statement="計画性が高い。",
                    theory_tag="bigfive:conscientiousness",
                    evidence_ids=[s2_ev2],
                ),
            ]
        ),
        SynthesisResult(
            claims=[
                SynthesizedClaimItem(
                    statement="自己決定の裁量を求める。",
                    theory_tag="scarf:autonomy",
                    evidence_ids=[s1_ev1],
                ),
                SynthesizedClaimItem(
                    statement="公平さを重視する。",
                    theory_tag="scarf:fairness",
                    evidence_ids=[s2_ev1],
                ),
            ]
        ),
        SynthesisResult(
            claims=[
                SynthesizedClaimItem(
                    statement="協調的なコミュニケーションを取る。",
                    theory_tag="bigfive:agreeableness",
                    evidence_ids=[s2_ev1],
                )
            ]
        ),
    ]


def test_build_persona_end_to_end_fixture_sources(tmp_path):
    repo = _make_repo(tmp_path)
    source1, source2 = _ingest_two_sources(repo)

    extraction_by_id = {
        source1.source_id: _extraction_result_for(source1),
        source2.source_id: _extraction_result_for(source2),
    }
    ordered_ids = sorted(extraction_by_id)
    extraction_responses = [extraction_by_id[sid] for sid in ordered_ids]
    synthesis_responses = _synthesis_responses(source1.source_id, source2.source_id)

    backend = MockBackend([*extraction_responses, *synthesis_responses])

    result = build_persona("taro", repo=repo, backend=backend, model_id="mock-model")

    persona = result.persona
    assert persona.persona_version == 1
    assert result.json_path.exists()
    assert result.md_path.exists()

    assert len(persona.core_values) == 1
    assert len(persona.decision_making) == 2
    assert len(persona.behavioral_patterns) == 2
    assert len(persona.needs_concerns) == 2
    assert len(persona.communication_style) == 1
    assert persona.information_gaps == []

    all_evidence = repo.read_evidence("taro")
    for claim in persona.claims():
        for ref in claim.evidence_refs:
            assert ref in all_evidence, f"claim {claim.claim_id} references missing evidence {ref}"

    md_text = result.md_path.read_text(encoding="utf-8")
    assert "Core Values" in md_text
    assert "Decision-Making" in md_text
    assert "Behavioral Patterns" in md_text
    assert "Needs & Concerns" in md_text
    assert "Communication Style" in md_text

    assert not backend.responses


def test_build_persona_resumes_after_partial_extraction_failure(tmp_path):
    repo = _make_repo(tmp_path)
    source1, source2 = _ingest_two_sources(repo)
    ordered_ids = sorted([source1.source_id, source2.source_id])
    first_id, second_id = ordered_ids

    sources_by_id = {source1.source_id: source1, source2.source_id: source2}
    only_first_response = [_extraction_result_for(sources_by_id[first_id])]
    backend = MockBackend(only_first_response)

    with pytest.raises(PersonaBuildError, match=second_id):
        build_persona("taro", repo=repo, backend=backend, model_id="mock-model")

    persisted = repo.read_evidence("taro")
    assert persisted, "evidence for the successful source must be persisted for resume"
    assert all(item.source_id == first_id for item in persisted.values())

    remaining_extraction = [_extraction_result_for(sources_by_id[second_id])]
    synthesis_responses = _synthesis_responses(source1.source_id, source2.source_id)
    resume_backend = MockBackend([*remaining_extraction, *synthesis_responses])

    result = build_persona("taro", repo=repo, backend=resume_backend, model_id="mock-model")

    assert resume_backend.calls[0]["prompt_version"] == "persona-extract-v1"
    assert len(resume_backend.calls) == 1 + len(synthesis_responses)
    assert result.persona.persona_version == 1


def test_build_persona_raises_when_no_sources(tmp_path):
    repo = _make_repo(tmp_path)
    backend = MockBackend([])
    with pytest.raises(PersonaBuildError, match="No sources"):
        build_persona("nobody", repo=repo, backend=backend, model_id="mock-model")
