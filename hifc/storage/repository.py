from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from hifc.schemas.analysis import AnalysisReport
from hifc.schemas.common import SAFE_ID_PATTERN
from hifc.schemas.persona import Evidence, Persona
from hifc.schemas.source import SourceDocument
from hifc.storage.hashing import source_content_hash


class StorageValidationError(ValueError):
    pass


_SAFE_ID_RE = re.compile(SAFE_ID_PATTERN)


class DataRepository:
    def __init__(self, root: Path | str = "data") -> None:
        self.root = Path(root)
        self._root_resolved = self.root.resolve(strict=False)

    def person_dir(self, person_id: str) -> Path:
        return self._root_path("persons", _safe_path_part(person_id, "person_id"))

    def initialize_person(self, person_id: str) -> Path:
        person_dir = self.person_dir(person_id)
        for subdir in ["sources", "evidence", "persona", "analyses"]:
            self._ensure_inside_root(person_dir / subdir).mkdir(parents=True, exist_ok=True)
        return person_dir

    def write_source(self, source: SourceDocument) -> Path:
        _validate_source_hash(source)
        self.initialize_person(source.person_id)
        source_id = _safe_path_part(source.source_id, "source_id")
        path = self._ensure_inside_root(
            self.person_dir(source.person_id) / "sources" / f"{source_id}.json"
        )
        _write_json_model(path, source)
        return path

    def read_sources(self, person_id: str) -> dict[str, SourceDocument]:
        source_dir = self._ensure_inside_root(self.person_dir(person_id) / "sources")
        if not source_dir.exists():
            return {}
        sources: dict[str, SourceDocument] = {}
        for path in sorted(source_dir.glob("*.json")):
            source = SourceDocument.model_validate_json(path.read_text(encoding="utf-8"))
            _validate_source_hash(source)
            if source.source_id != path.stem:
                raise StorageValidationError(
                    f"Source filename/id mismatch: {path.name} != {source.source_id}"
                )
            sources[path.stem] = source
        return sources

    def write_evidence(self, person_id: str, evidence: Iterable[Evidence]) -> Path:
        self.initialize_person(person_id)
        path = self._ensure_inside_root(
            self.person_dir(person_id) / "evidence" / "evidence.jsonl"
        )
        with path.open("w", encoding="utf-8") as f:
            for item in evidence:
                f.write(item.model_dump_json() + "\n")
        return path

    def read_evidence(self, person_id: str) -> dict[str, Evidence]:
        path = self._ensure_inside_root(
            self.person_dir(person_id) / "evidence" / "evidence.jsonl"
        )
        if not path.exists():
            return {}
        evidence: dict[str, Evidence] = {}
        with path.open(encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                item = Evidence.model_validate_json(line)
                if item.evidence_id in evidence:
                    raise StorageValidationError(
                        f"Duplicate evidence_id in {path}:{line_number}: {item.evidence_id}"
                    )
                evidence[item.evidence_id] = item
        return evidence

    def next_persona_version(self, person_id: str) -> int:
        persona_dir = self._ensure_inside_root(self.person_dir(person_id) / "persona")
        versions = []
        for path in persona_dir.glob("persona-v*.json"):
            match = re.fullmatch(r"persona-v(\d+)", path.stem)
            if match:
                versions.append(int(match.group(1)))
        return max(versions, default=0) + 1

    def write_persona(self, persona: Persona) -> Path:
        self.validate_persona(persona)
        self.initialize_person(persona.person_id)
        path = self._ensure_inside_root(
            self.person_dir(persona.person_id)
            / "persona"
            / f"persona-v{persona.persona_version}.json"
        )
        md_path = path.with_suffix(".md")
        if path.exists() or md_path.exists():
            raise StorageValidationError(
                f"Persona version already exists: persona-v{persona.persona_version}"
            )
        _write_json_model(path, persona, overwrite=False)
        return path

    def read_persona(self, person_id: str, version: int | None = None) -> Persona:
        if version is None:
            version = self.next_persona_version(person_id) - 1
        path = self._ensure_inside_root(
            self.person_dir(person_id) / "persona" / f"persona-v{version}.json"
        )
        return Persona.model_validate_json(path.read_text(encoding="utf-8"))

    def write_analysis(self, report: AnalysisReport, slug: str) -> Path:
        self.initialize_person(report.person_id)
        safe_slug = _safe_path_part(slug, "analysis slug")
        path = self._ensure_inside_root(
            self.person_dir(report.person_id) / "analyses" / f"{safe_slug}.json"
        )
        _write_json_model(path, report, overwrite=False)
        return path

    def validate_persona(self, persona: Persona) -> None:
        sources = self.read_sources(persona.person_id)
        evidence = self.read_evidence(persona.person_id)
        manifest_source_ids = {source.source_id for source in persona.source_manifest}
        missing_manifest_sources = manifest_source_ids - set(sources)
        if missing_manifest_sources:
            raise StorageValidationError(
                "Persona manifest references missing sources: "
                + ", ".join(sorted(missing_manifest_sources))
            )
        for source_ref in persona.source_manifest:
            actual_hash = sources[source_ref.source_id].content_hash
            if source_ref.content_hash != actual_hash:
                raise StorageValidationError(
                    f"Persona manifest content_hash mismatch for {source_ref.source_id}: "
                    f"expected {actual_hash}, got {source_ref.content_hash}"
                )

        for item in evidence.values():
            if item.source_id not in sources:
                raise StorageValidationError(
                    f"Evidence {item.evidence_id} references missing source {item.source_id}"
                )
            source = sources[item.source_id]
            if not quote_exists(item.quote, source.raw_text):
                raise StorageValidationError(
                    f"Evidence {item.evidence_id} quote not found in source {item.source_id}"
                )

        for claim in persona.claims():
            for ref in claim.evidence_refs:
                if ref not in evidence:
                    raise StorageValidationError(
                        f"Claim {claim.claim_id} references missing evidence {ref}"
                    )

    def _root_path(self, *parts: str) -> Path:
        return self._ensure_inside_root(self.root.joinpath(*parts))

    def _ensure_inside_root(self, path: Path) -> Path:
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(self._root_resolved)
        except ValueError as exc:
            raise StorageValidationError(f"Path escapes data root: {path}") from exc
        return path


def _safe_path_part(value: str, field_name: str) -> str:
    if not _SAFE_ID_RE.fullmatch(value):
        raise StorageValidationError(f"Unsafe {field_name}: {value!r}")
    return value


def _validate_source_hash(source: SourceDocument) -> None:
    expected = source_content_hash(source.raw_text)
    if source.content_hash != expected:
        raise StorageValidationError(
            f"Source {source.source_id} content_hash mismatch: "
            f"expected {expected}, got {source.content_hash}"
        )


def quote_exists(quote: str, raw_text: str) -> bool:
    normalized_quote = _normalize_text(quote)
    normalized_raw = _normalize_text(raw_text)
    return normalized_quote in normalized_raw


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _write_json_model(path: Path, model: BaseModel, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    try:
        with path.open(mode, encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))
    except FileExistsError as exc:
        raise StorageValidationError(f"Refusing to overwrite existing file: {path}") from exc
