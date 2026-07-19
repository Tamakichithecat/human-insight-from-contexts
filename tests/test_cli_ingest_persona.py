from __future__ import annotations

from typer.testing import CliRunner

import hifc.cli.ingest as ingest_cli
import hifc.cli.persona as persona_cli
from hifc.cli.app import app
from hifc.ingest.errors import IngestError, YoutubeTranscriptUnavailable
from hifc.llm import MockBackend
from hifc.prompts.persona.extract_prompt import ExtractedEvidenceItem, ExtractionResult
from hifc.prompts.persona.synthesize_prompt import SynthesisResult, SynthesizedClaimItem
from hifc.storage import DataRepository

runner = CliRunner()


def test_ingest_paste_writes_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "ingest",
            "paste",
            "--person",
            "taro",
            "--type",
            "blog",
            "--perspective",
            "first_person",
            "--text",
            "自分の裁量で意思決定することを大切にしている。",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "wrote" in result.output

    sources = DataRepository().read_sources("taro")
    assert len(sources) == 1


def test_ingest_paste_without_text_or_stdin_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["ingest", "paste", "--person", "taro", "--type", "blog", "--perspective", "first_person"],
        input="",
    )
    assert result.exit_code == 1


def test_ingest_csv_writes_multiple_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text(
        "text,date,source_type,origin,author_perspective\n"
        "一行目。,2026-01-01,blog,https://example.test/1,first_person\n"
        "二行目。,2026-01-02,blog,https://example.test/2,first_person\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["ingest", "csv", str(csv_path), "--person", "taro"])
    assert result.exit_code == 0, result.output
    assert DataRepository().read_sources("taro").__len__() == 2


def test_ingest_url_reports_ingest_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_build_source_from_url(url, **kwargs):
        raise IngestError("boom")

    monkeypatch.setattr(ingest_cli, "build_source_from_url", fake_build_source_from_url)
    result = runner.invoke(
        app,
        [
            "ingest",
            "url",
            "https://example.test/article",
            "--person",
            "taro",
            "--type",
            "news",
        ],
    )
    assert result.exit_code == 1
    assert "ingest failed" in result.output


def test_ingest_youtube_suggests_paste_fallback_on_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_build_source_from_youtube(url, **kwargs):
        raise YoutubeTranscriptUnavailable("no captions")

    monkeypatch.setattr(ingest_cli, "build_source_from_youtube", fake_build_source_from_youtube)
    result = runner.invoke(
        app, ["ingest", "youtube", "https://youtu.be/dQw4w9WgXcQ", "--person", "taro"]
    )
    assert result.exit_code == 1
    assert "fallback" in result.output
    assert "hifc ingest paste" in result.output


def test_persona_show_without_existing_persona_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["persona", "show", "taro"])
    assert result.exit_code == 1
    assert "persona not found" in result.output


def test_persona_build_show_and_explain_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(
        app,
        [
            "ingest",
            "paste",
            "--person",
            "taro",
            "--type",
            "blog",
            "--perspective",
            "first_person",
            "--text",
            "自分の裁量で意思決定することを大切にしている。",
        ],
    )
    source = next(iter(DataRepository().read_sources("taro").values()))

    extraction = ExtractionResult(
        items=[
            ExtractedEvidenceItem(
                quote=source.raw_text,
                locator="paragraph:1",
                directness="direct_statement",
                stance="supports",
                theory_tags=["schwartz:self_direction"],
            )
        ]
    )
    synthesis = SynthesisResult(
        claims=[
            SynthesizedClaimItem(
                statement="自律性を重視する。",
                theory_tag="schwartz:self_direction",
                evidence_ids=[f"{source.source_id}-ev001"],
            )
        ]
    )
    mock_backend = MockBackend([extraction, synthesis])
    monkeypatch.setattr(persona_cli, "backend_from_env", lambda: mock_backend)

    build_result = runner.invoke(app, ["persona", "build", "taro"])
    assert build_result.exit_code == 0, build_result.output
    assert "information_gaps" in build_result.output

    show_result = runner.invoke(app, ["persona", "show", "taro"])
    assert show_result.exit_code == 0
    assert "Core Values" in show_result.output
    assert "自律性を重視する" in show_result.output

    persona = DataRepository().read_persona("taro")
    claim_id = persona.core_values[0].claim_id

    explain_result = runner.invoke(app, ["persona", "explain", "taro", claim_id])
    assert explain_result.exit_code == 0
    assert claim_id in explain_result.output

    explain_missing = runner.invoke(app, ["persona", "explain", "taro", "no-such-claim"])
    assert explain_missing.exit_code == 1
