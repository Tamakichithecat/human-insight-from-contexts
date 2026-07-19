from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import BaseModel

from hifc.llm import (
    ClaudeCodeBackend,
    CodexBackend,
    LLMBackendError,
    LLMOutputError,
    MockBackend,
)
from hifc.llm.backend import BaseCLIBackend, _run_command
from hifc.llm.json_utils import extract_json_text
from hifc.schemas import Persona


class LLMFixture(BaseModel):
    answer: str


def test_extract_json_text_from_code_fence():
    assert extract_json_text("```json\n{\"ok\": true}\n```") == "{\"ok\": true}"


def test_mock_backend_validates_response_schema(sample_persona):
    backend = MockBackend([json.loads(sample_persona.model_dump_json())])
    result = backend.complete("build a persona", schema=Persona, prompt_version="test-v1")

    assert result == sample_persona
    assert backend.calls == [{"prompt": "build a persona", "prompt_version": "test-v1"}]


def test_claude_backend_builds_argv_schema_prompt_and_writes_log(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"result": json.dumps({"answer": "ok"})}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    log_path = tmp_path / "llm.jsonl"
    backend = ClaudeCodeBackend(model="sonnet", timeout_seconds=12, log_path=log_path)

    result = backend.complete("Say ok", schema=LLMFixture, prompt_version="prompt-v1")

    assert result.answer == "ok"
    command, kwargs = calls[0]
    assert command[:6] == [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--tools",
    ]
    assert command[6] == ""
    assert "--json-schema" in command
    schema_arg = command[command.index("--json-schema") + 1]
    assert json.loads(schema_arg)["properties"]["answer"]["type"] == "string"
    assert command[-3:] == ["--model", "sonnet", command[-1]]
    assert "Say ok" in command[-1]
    assert "Return only one JSON object" in command[-1]
    assert '"answer"' in command[-1]
    assert kwargs["timeout"] == 12
    assert kwargs["check"] is True

    [record] = _read_jsonl(log_path)
    assert record["backend"] == "claude"
    assert record["model"] == "sonnet"
    assert record["prompt_version"] == "prompt-v1"
    assert record["retries"] == 0
    assert record["success"] is True
    assert record["error"] is None


def test_codex_backend_builds_argv_writes_schema_file_and_reads_output(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        assert json.loads(schema_path.read_text(encoding="utf-8"))["properties"]["answer"][
            "type"
        ] == "string"
        output_path.write_text(json.dumps({"answer": "ok"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="ignored", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    backend = CodexBackend(
        model="gpt-5.5",
        effort="high",
        timeout_seconds=34,
        log_path=tmp_path / "llm.jsonl",
    )

    result = backend.complete("Say ok", schema=LLMFixture, prompt_version="prompt-v2")

    assert result.answer == "ok"
    command, kwargs = calls[0]
    assert command[:2] == ["codex", "exec"]
    assert "--output-schema" in command
    assert "--output-last-message" in command
    assert ["--model", "gpt-5.5"] == command[6:8]
    assert command[8:10] == ["--config", 'model_reasoning_effort="high"']
    assert "Say ok" in command[-1]
    assert "Return only one JSON object" in command[-1]
    assert kwargs["timeout"] == 34


def test_base_cli_backend_retries_invalid_json_and_validation_error_then_succeeds(tmp_path):
    backend = SequencedBackend(
        [
            "not json",
            json.dumps({"wrong": "shape"}),
            json.dumps({"answer": "ok"}),
        ],
        log_path=tmp_path / "llm.jsonl",
    )

    result = backend.complete("Say ok", schema=LLMFixture, prompt_version="prompt-v3")

    assert result.answer == "ok"
    assert len(backend.prompts) == 3
    assert "Return only one JSON object" in backend.prompts[0]
    assert "The previous response failed validation" in backend.prompts[1]
    assert "Validation error:" in backend.prompts[2]
    [record] = _read_jsonl(tmp_path / "llm.jsonl")
    assert record["backend"] == "sequence"
    assert record["retries"] == 2
    assert record["success"] is True


def test_base_cli_backend_raises_after_retry_exhaustion_and_logs_failure(tmp_path):
    backend = SequencedBackend(
        ["not json", "still not json", "nope"],
        log_path=tmp_path / "llm.jsonl",
    )

    with pytest.raises(LLMOutputError, match="failed schema validation"):
        backend.complete("Say ok", schema=LLMFixture, prompt_version="prompt-v4")

    assert len(backend.prompts) == 3
    [record] = _read_jsonl(tmp_path / "llm.jsonl")
    assert record["backend"] == "sequence"
    assert record["retries"] == 2
    assert record["success"] is False
    assert record["error"]


def test_run_command_wraps_cli_nonzero_with_stderr(monkeypatch):
    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(2, command, stderr="not logged in")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(LLMBackendError, match="failed with exit code 2: not logged in"):
        _run_command(["claude", "--print", "hi"], 10, "claude")


def test_run_command_wraps_missing_cli(monkeypatch):
    def fake_run(command, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(LLMBackendError, match="not installed or not on PATH"):
        _run_command(["claude", "--print", "hi"], 10, "claude")


class SequencedBackend(BaseCLIBackend):
    backend_name = "sequence"

    def __init__(self, outputs: list[str], **kwargs):
        super().__init__(**kwargs)
        self.outputs = outputs
        self.prompts: list[str] = []

    def _run(self, prompt: str, schema_json: dict) -> str:
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
