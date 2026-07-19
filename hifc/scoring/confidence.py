from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import exp, log
from pathlib import Path

import yaml

from hifc.schemas.persona import Confidence, Evidence
from hifc.schemas.source import SourceDocument

DEFAULT_WEIGHTS_PATH = Path(__file__).with_name("weights.yaml")


@dataclass(frozen=True)
class ScoringConfig:
    source_type_weights: dict[str, float]
    directness_weights: dict[str, float]
    half_life_months: float
    contradiction_lambda: float
    saturation_k: float
    high_threshold: float
    medium_threshold: float


def load_scoring_config(path: Path = DEFAULT_WEIGHTS_PATH) -> ScoringConfig:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ScoringConfig(
        source_type_weights=dict(data["source_type_weights"]),
        directness_weights=dict(data["directness_weights"]),
        half_life_months=float(data["half_life_months"]),
        contradiction_lambda=float(data["contradiction_lambda"]),
        saturation_k=float(data["saturation_k"]),
        high_threshold=float(data["bands"]["high"]),
        medium_threshold=float(data["bands"]["medium"]),
    )


def score_confidence(
    evidence_refs: list[str],
    *,
    evidence: dict[str, Evidence] | list[Evidence],
    sources: dict[str, SourceDocument] | list[SourceDocument],
    as_of: date | datetime | None = None,
    config: ScoringConfig | None = None,
) -> Confidence:
    """Calculate deterministic claim confidence from evidence metadata."""
    config = config or load_scoring_config()
    evidence_by_id = _index_by_id(evidence, "evidence_id")
    sources_by_id = _index_by_id(sources, "source_id")
    scoring_date = _as_date(as_of or datetime.now(UTC))

    selected = []
    for evidence_id in evidence_refs:
        try:
            selected.append(evidence_by_id[evidence_id])
        except KeyError as exc:
            raise ValueError(f"Unknown evidence ref: {evidence_id}") from exc

    support = 0.0
    contradiction = 0.0
    source_ids: set[str] = set()
    for item in selected:
        try:
            source = sources_by_id[item.source_id]
        except KeyError as exc:
            message = f"Missing source for evidence {item.evidence_id}: {item.source_id}"
            raise ValueError(message) from exc
        source_ids.add(item.source_id)
        weight = _evidence_weight(item, source, scoring_date, config)
        if item.stance == "supports":
            support += weight
        else:
            contradiction += weight

    raw = max(0.0, support - config.contradiction_lambda * contradiction)
    base = 1.0 - exp(-config.saturation_k * raw)
    independence = 1.0 - 2.0 ** (-len(source_ids)) if source_ids else 0.0
    score = base * independence

    return Confidence(
        score=score,
        band=confidence_band(score, config),
        n_evidence=len(selected),
        n_sources=len(source_ids),
        single_source=len(source_ids) == 1,
        contradiction_present=any(item.stance == "contradicts" for item in selected),
    )


def _evidence_weight(
    evidence: Evidence,
    source: SourceDocument,
    scoring_date: date,
    config: ScoringConfig,
) -> float:
    try:
        source_weight = config.source_type_weights[source.source_type]
    except KeyError as exc:
        raise ValueError(f"No source_type weight configured for {source.source_type}") from exc
    try:
        directness_weight = config.directness_weights[evidence.directness]
    except KeyError as exc:
        raise ValueError(f"No directness weight configured for {evidence.directness}") from exc
    age_months = _age_months(source.published_at or source.retrieved_at.date(), scoring_date)
    decay = exp(-log(2.0) * age_months / config.half_life_months)
    return source_weight * directness_weight * decay


def _age_months(published_at: date, scoring_date: date) -> float:
    days = max(0, (scoring_date - published_at).days)
    return days / 30.4375


def confidence_band(score: float, config: ScoringConfig | None = None) -> str:
    config = config or load_scoring_config()
    if score >= config.high_threshold:
        return "high"
    if score >= config.medium_threshold:
        return "medium"
    return "low"


def _as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _index_by_id(items, id_attr: str):
    if isinstance(items, dict):
        return items
    return {getattr(item, id_attr): item for item in items}
