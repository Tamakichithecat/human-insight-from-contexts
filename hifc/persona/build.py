from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from hifc.extract.pipeline import extract_evidence
from hifc.llm.backend import LLMBackend, LLMBackendError, LLMOutputError
from hifc.persona.render import persona_to_markdown
from hifc.persona.synthesize import synthesize_dimension_claims
from hifc.prompts.persona.extract_prompt import EXTRACT_PROMPT_VERSION
from hifc.prompts.persona.rubrics import DIMENSION_TAGS
from hifc.prompts.persona.synthesize_prompt import SYNTHESIZE_PROMPT_VERSION
from hifc.schemas.common import GeneratorInfo, SourceRef
from hifc.schemas.persona import Evidence, Persona
from hifc.schemas.source import SourceDocument
from hifc.storage import DataRepository

_MAX_EVIDENCE_AGE_MONTHS = 24.0
_MIN_SOURCES_FOR_SINGLE_SOURCE_WARNING = 2


class PersonaBuildError(RuntimeError):
    pass


@dataclass
class PersonaBuildResult:
    persona: Persona
    json_path: Path
    md_path: Path


def build_persona(
    person_id: str,
    *,
    repo: DataRepository,
    backend: LLMBackend,
    model_id: str,
    pipeline_version: str = "0.1.0",
) -> PersonaBuildResult:
    """Run the full ingest→extract→synthesize→score→validate pipeline (DESIGN.md §5).

    Extraction is resumable: evidence is persisted after each source, so a source that
    already has evidence on disk is skipped on the next invocation, and only sources
    that failed on the previous run are retried (DESIGN.md §8.1 / §9 W2 completion condition).
    """
    sources = repo.read_sources(person_id)
    if not sources:
        raise PersonaBuildError(f"No sources ingested for person_id={person_id!r}")

    evidence_by_source = _group_by_source(repo.read_evidence(person_id))
    failures: dict[str, str] = {}

    for source_id in sorted(sources):
        if source_id in evidence_by_source:
            continue
        try:
            evidence_by_source[source_id] = extract_evidence(sources[source_id], backend)
        except (LLMBackendError, LLMOutputError) as exc:
            failures[source_id] = str(exc)
            continue
        repo.write_evidence(person_id, _flatten(evidence_by_source))

    if failures:
        details = "; ".join(f"{sid}: {msg}" for sid, msg in sorted(failures.items()))
        raise PersonaBuildError(
            f"Evidence extraction failed for {len(failures)} of {len(sources)} source(s): "
            f"{details}. Already-extracted sources were saved to evidence.jsonl; "
            "re-run `hifc persona build` to retry only the failed sources."
        )

    evidence_all = repo.read_evidence(person_id)
    generated_at = datetime.now(UTC)

    claims_by_dimension = {
        dimension: synthesize_dimension_claims(
            dimension, evidence_all, sources, backend, as_of=generated_at
        )
        for dimension in DIMENSION_TAGS
    }

    persona = Persona(
        person_id=person_id,
        persona_version=repo.next_persona_version(person_id),
        generated_at=generated_at,
        generator=GeneratorInfo(
            model_id=model_id,
            prompt_version=f"{EXTRACT_PROMPT_VERSION}+{SYNTHESIZE_PROMPT_VERSION}",
            pipeline_version=pipeline_version,
        ),
        source_manifest=[
            SourceRef(source_id=source.source_id, content_hash=source.content_hash)
            for source in sources.values()
        ],
        core_values=claims_by_dimension["core_values"],
        decision_making=claims_by_dimension["decision_making"],
        behavioral_patterns=claims_by_dimension["behavioral_patterns"],
        needs_concerns=claims_by_dimension["needs_concerns"],
        communication_style=claims_by_dimension["communication_style"],
        information_gaps=_information_gaps(sources, evidence_all, generated_at),
    )

    json_path = repo.write_persona(persona)
    md_path = json_path.with_suffix(".md")
    md_path.write_text(persona_to_markdown(persona, sources, evidence_all), encoding="utf-8")

    return PersonaBuildResult(persona=persona, json_path=json_path, md_path=md_path)


def _group_by_source(evidence: dict[str, Evidence]) -> dict[str, list[Evidence]]:
    grouped: dict[str, list[Evidence]] = {}
    for item in evidence.values():
        grouped.setdefault(item.source_id, []).append(item)
    return grouped


def _flatten(evidence_by_source: dict[str, list[Evidence]]) -> list[Evidence]:
    return [item for items in evidence_by_source.values() for item in items]


def _information_gaps(
    sources: dict[str, SourceDocument],
    evidence: dict[str, Evidence],
    as_of: datetime,
) -> list[str]:
    gaps: list[str] = []

    if len(sources) < _MIN_SOURCES_FOR_SINGLE_SOURCE_WARNING:
        gaps.append(
            f"ソース数が{len(sources)}件と少なく、単一ソースバイアスのリスクがあります"
            "(推奨: 2件以上の独立ソース)。"
        )

    missing_published_at = sorted(s.source_id for s in sources.values() if s.published_at is None)
    if missing_published_at:
        gaps.append(
            "published_at が未指定のため取得日で代替したソースがあります"
            "(confidence の経年減衰計算が不正確になる可能性): " + ", ".join(missing_published_at)
        )

    newest = _newest_reference_date(sources)
    if newest is not None:
        age_months = (as_of.date() - newest).days / 30.4375
        if age_months > _MAX_EVIDENCE_AGE_MONTHS:
            gaps.append(
                f"最新のソースでも{age_months:.0f}ヶ月前の情報であり、情報が古い可能性があります。"
            )

    if not evidence:
        gaps.append("抽出された evidence が0件でした。")

    return gaps


def _newest_reference_date(sources: dict[str, SourceDocument]):
    dates = [source.published_at or source.retrieved_at.date() for source in sources.values()]
    return max(dates) if dates else None
