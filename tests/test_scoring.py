from __future__ import annotations

from datetime import date

import pytest

from hifc.schemas import Evidence
from hifc.scoring import ScoringConfig, confidence_band, load_scoring_config, score_confidence


def test_confidence_band_boundaries():
    assert confidence_band(0.65) == "high"
    assert confidence_band(0.35) == "medium"
    assert confidence_band(0.3499) == "low"


def test_single_source_cannot_reach_high_band(sample_sources, sample_evidence):
    confidence = score_confidence(
        ["ev-1"],
        evidence=sample_evidence,
        sources=sample_sources,
        as_of=date(2026, 3, 1),
    )
    assert confidence.single_source is True
    assert confidence.n_sources == 1
    assert confidence.score < 0.65
    assert confidence.band != "high"


def test_multiple_sources_increase_confidence(sample_sources, sample_evidence):
    one = score_confidence(
        ["ev-1"],
        evidence=sample_evidence,
        sources=sample_sources,
        as_of=date(2026, 3, 1),
    )
    two = score_confidence(
        ["ev-1", "ev-2"],
        evidence=sample_evidence,
        sources=sample_sources,
        as_of=date(2026, 3, 1),
    )
    assert two.score > one.score
    assert two.n_sources == 2


def test_contradiction_penalty_reduces_score(sample_sources, sample_evidence):
    contradiction = Evidence(
        evidence_id="ev-3",
        source_id="src-interview",
        quote="新しい企画では、裁量があると一番力を出せます。",
        locator="paragraph:4",
        directness="direct_statement",
        stance="contradicts",
        theory_tags=["scarf:autonomy"],
        noted_bias=None,
    )
    without = score_confidence(
        ["ev-1", "ev-2"],
        evidence=sample_evidence,
        sources=sample_sources,
        as_of=date(2026, 3, 1),
    )
    with_contradiction = score_confidence(
        ["ev-1", "ev-2", "ev-3"],
        evidence=[*sample_evidence, contradiction],
        sources=sample_sources,
        as_of=date(2026, 3, 1),
    )
    assert with_contradiction.contradiction_present is True
    assert with_contradiction.score < without.score


def test_half_life_decay_reduces_old_evidence_score(sample_sources, sample_evidence):
    recent = score_confidence(
        ["ev-1"],
        evidence=sample_evidence,
        sources=sample_sources,
        as_of=date(2026, 3, 1),
    )
    old = score_confidence(
        ["ev-1"],
        evidence=sample_evidence,
        sources=sample_sources,
        as_of=date(2029, 3, 1),
    )
    assert old.score < recent.score


def test_missing_source_type_weight_raises_clear_error(sample_sources, sample_evidence):
    base = load_scoring_config()
    config = ScoringConfig(
        source_type_weights={},
        directness_weights=base.directness_weights,
        half_life_months=base.half_life_months,
        contradiction_lambda=base.contradiction_lambda,
        saturation_k=base.saturation_k,
        high_threshold=base.high_threshold,
        medium_threshold=base.medium_threshold,
    )

    with pytest.raises(ValueError, match="No source_type weight"):
        score_confidence(
            ["ev-1"],
            evidence=sample_evidence,
            sources=sample_sources,
            as_of=date(2026, 3, 1),
            config=config,
        )
