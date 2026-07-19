from __future__ import annotations

import pytest

from hifc.schemas import SourceDocument
from hifc.storage import DataRepository, StorageValidationError


def test_repository_writes_and_reads_persona(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence("person-1", sample_evidence)

    assert repo.next_persona_version("person-1") == 1
    path = repo.write_persona(sample_persona)
    restored = repo.read_persona("person-1", version=1)

    assert path.name == "persona-v1.json"
    assert restored == sample_persona
    assert repo.next_persona_version("person-1") == 2


def test_repository_rejects_missing_evidence_ref(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence("person-1", sample_evidence[:-1])

    with pytest.raises(StorageValidationError, match="missing evidence"):
        repo.write_persona(sample_persona)


def test_repository_rejects_quote_not_in_source(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    broken = sample_evidence[0].model_copy(update={"quote": "存在しない引用"})
    repo.write_evidence("person-1", [broken, sample_evidence[1]])

    with pytest.raises(StorageValidationError, match="quote not found"):
        repo.write_persona(sample_persona)


def test_repository_rejects_person_id_path_traversal(tmp_path):
    repo = DataRepository(tmp_path / "data")

    with pytest.raises(StorageValidationError, match="Unsafe person_id"):
        repo.initialize_person("../outside")


def test_repository_rejects_analysis_slug_path_traversal(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
    sample_generator,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence("person-1", sample_evidence)
    repo.write_persona(sample_persona)
    report = _sample_report(sample_persona, sample_generator)

    with pytest.raises(StorageValidationError, match="Unsafe analysis slug"):
        repo.write_analysis(report, "../outside")


def test_repository_refuses_existing_persona_version(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence("person-1", sample_evidence)
    repo.write_persona(sample_persona)

    with pytest.raises(StorageValidationError, match="already exists"):
        repo.write_persona(sample_persona)


def test_repository_refuses_persona_when_markdown_version_exists(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence("person-1", sample_evidence)
    persona_dir = repo.person_dir("person-1") / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "persona-v1.md").write_text("existing", encoding="utf-8")

    with pytest.raises(StorageValidationError, match="already exists"):
        repo.write_persona(sample_persona)


def test_repository_rejects_content_hash_mismatch(tmp_path, sample_sources):
    repo = DataRepository(tmp_path / "data")
    broken = sample_sources[0].model_copy(
        update={
            "content_hash": "0" * 64,
        }
    )

    with pytest.raises(StorageValidationError, match="content_hash mismatch"):
        repo.write_source(broken)


def test_repository_rejects_manifest_content_hash_mismatch(
    tmp_path,
    sample_sources,
    sample_evidence,
    sample_persona,
):
    repo = DataRepository(tmp_path / "data")
    for source in sample_sources:
        repo.write_source(source)
    repo.write_evidence("person-1", sample_evidence)
    broken_manifest = sample_persona.source_manifest[0].model_copy(
        update={"content_hash": "0" * 64}
    )
    broken = sample_persona.model_copy(
        update={"source_manifest": [broken_manifest, *sample_persona.source_manifest[1:]]}
    )

    with pytest.raises(StorageValidationError, match="manifest content_hash mismatch"):
        repo.write_persona(broken)


def test_source_document_rejects_unsafe_source_id(sample_sources):
    payload = sample_sources[0].model_dump()
    payload["source_id"] = "../outside"

    with pytest.raises(ValueError):
        SourceDocument.model_validate(payload)


def _sample_report(sample_persona, sample_generator):
    from hifc.schemas import AnalysisReport, Interpretation

    return AnalysisReport(
        person_id="person-1",
        persona_version=1,
        meeting_source_id="meeting-1",
        interpretations=[
            Interpretation(
                statement="検討します。",
                surface_meaning="内部で検討する。",
                inferred_intent="裁量を確保したい可能性がある。",
                supporting_claim_ids=["claim-1"],
                confidence=sample_persona.claims()[0].confidence,
                misread_risk="単なる先送りと誤読するリスク。",
            )
        ],
        overall_reading="自律性への配慮が必要。",
        generated_at=sample_persona.generated_at,
        generator=sample_generator,
    )
