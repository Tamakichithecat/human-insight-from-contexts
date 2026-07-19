from __future__ import annotations

import pytest
from pydantic import ValidationError

from hifc.extract import extract_evidence
from hifc.llm import MockBackend
from hifc.prompts.persona.extract_prompt import ExtractedEvidenceItem, ExtractionResult


def test_extracted_evidence_item_rejects_unknown_theory_tag():
    with pytest.raises(ValidationError):
        ExtractedEvidenceItem(
            quote="テスト",
            locator="paragraph:1",
            directness="direct_statement",
            stance="supports",
            theory_tags=["not_a_real_tag"],
        )


def test_extract_evidence_maps_items_and_assigns_ids(sample_sources):
    source = sample_sources[0]
    response = ExtractionResult(
        items=[
            ExtractedEvidenceItem(
                quote=source.raw_text,
                locator="paragraph:1",
                directness="direct_statement",
                stance="supports",
                theory_tags=["schwartz:self_direction", "scarf:autonomy"],
                noted_bias=None,
            )
        ]
    )
    backend = MockBackend([response])

    evidence = extract_evidence(source, backend)

    assert len(evidence) == 1
    item = evidence[0]
    assert item.evidence_id == f"{source.source_id}-ev001"
    assert item.source_id == source.source_id
    assert item.theory_tags == ["schwartz:self_direction", "scarf:autonomy"]
    assert backend.calls[0]["prompt_version"] == "persona-extract-v1"


def test_extract_evidence_drops_items_with_unverifiable_quote(sample_sources):
    source = sample_sources[0]
    response = ExtractionResult(
        items=[
            ExtractedEvidenceItem(
                quote="この文章はソースに存在しない捏造引用です。",
                locator="paragraph:1",
                directness="inferred",
                stance="supports",
                theory_tags=["schwartz:self_direction"],
            ),
            ExtractedEvidenceItem(
                quote=source.raw_text,
                locator="paragraph:1",
                directness="direct_statement",
                stance="supports",
                theory_tags=["scarf:autonomy"],
            ),
        ]
    )
    backend = MockBackend([response])

    evidence = extract_evidence(source, backend)

    assert len(evidence) == 1
    assert evidence[0].theory_tags == ["scarf:autonomy"]
