from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from hifc.llm import MockBackend
from hifc.schemas import (
    Chunk,
    Claim,
    Confidence,
    Evidence,
    GeneratorInfo,
    Persona,
    SourceDocument,
    SourceRef,
)
from hifc.storage import source_content_hash


@pytest.fixture
def sample_generator() -> GeneratorInfo:
    return GeneratorInfo(
        model_id="mock-model",
        prompt_version="test-v1",
        pipeline_version="0.1.0",
    )


@pytest.fixture
def sample_sources() -> list[SourceDocument]:
    return [
        SourceDocument(
            source_id="src-blog",
            person_id="person-1",
            content_hash=source_content_hash(
                "私は自分で選び、未知の挑戦を続けることを大切にしている。"
            ),
            source_type="blog",
            origin="paste",
            title="Self direction",
            author_perspective="first_person",
            published_at=date(2026, 1, 1),
            retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
            language="ja",
            raw_text="私は自分で選び、未知の挑戦を続けることを大切にしている。",
            chunks=[
                Chunk(
                    chunk_id="src-blog-c1",
                    text="私は自分で選び、未知の挑戦を続けることを大切にしている。",
                    locator="paragraph:1",
                )
            ],
        ),
        SourceDocument(
            source_id="src-interview",
            person_id="person-1",
            content_hash=source_content_hash("新しい企画では、裁量があると一番力を出せます。"),
            source_type="interview",
            origin="https://example.test/interview",
            title="Interview",
            author_perspective="first_person",
            published_at=date(2026, 2, 1),
            retrieved_at=datetime(2026, 2, 2, tzinfo=UTC),
            language="ja",
            raw_text="新しい企画では、裁量があると一番力を出せます。",
            chunks=[],
        ),
    ]


@pytest.fixture
def sample_evidence() -> list[Evidence]:
    return [
        Evidence(
            evidence_id="ev-1",
            source_id="src-blog",
            quote="私は自分で選び、未知の挑戦を続けることを大切にしている。",
            locator="paragraph:1",
            directness="direct_statement",
            stance="supports",
            theory_tags=["schwartz:self_direction", "scarf:autonomy"],
            noted_bias=None,
        ),
        Evidence(
            evidence_id="ev-2",
            source_id="src-interview",
            quote="裁量があると一番力を出せます",
            locator="paragraph:3",
            directness="direct_statement",
            stance="supports",
            theory_tags=["scarf:autonomy"],
            noted_bias=None,
        ),
    ]


@pytest.fixture
def sample_persona(sample_generator, sample_sources, sample_evidence) -> Persona:
    confidence = Confidence(
        score=0.5,
        band="medium",
        n_evidence=2,
        n_sources=2,
        single_source=False,
        contradiction_present=False,
    )
    claim = Claim(
        claim_id="claim-1",
        statement="自律性と自己決定を重視する。",
        theory_tag="scarf:autonomy",
        confidence=confidence,
        evidence_refs=[item.evidence_id for item in sample_evidence],
        temporal_note=None,
    )
    return Persona(
        person_id="person-1",
        persona_version=1,
        generated_at=datetime(2026, 3, 1, tzinfo=UTC),
        generator=sample_generator,
        source_manifest=[
            SourceRef(source_id=source.source_id, content_hash=source.content_hash)
            for source in sample_sources
        ],
        core_values=[claim],
        information_gaps=[],
    )


@pytest.fixture
def mock_backend(sample_persona) -> MockBackend:
    return MockBackend([sample_persona])
