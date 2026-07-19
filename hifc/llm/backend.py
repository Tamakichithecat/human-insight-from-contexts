from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from hifc.llm.json_utils import extract_json_text

T = TypeVar("T", bound=BaseModel)


class LLMBackendError(RuntimeError):
    pass


class LLMOutputError(LLMBackendError):
    pass


class LLMBackend(Protocol):
    def complete(self, prompt: str, *, schema: type[T], prompt_version: str) -> T:
        """Run a prompt and return a pydantic-validated model."""


class BaseCLIBackend:
    backend_name = "base"

    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: int = 300,
        max_retries: int = 2,
        log_path: Path | str = "data/logs/llm.jsonl",
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.log_path = Path(log_path)

    def complete(self, prompt: str, *, schema: type[T], prompt_version: str) -> T:
        schema_json = schema.model_json_schema()
        attempt_prompt = _prompt_with_schema(prompt, schema_json)
        last_error = ""
        started = time.monotonic()

        for attempt in range(self.max_retries + 1):
            if attempt:
                attempt_prompt = _retry_prompt(prompt, schema_json, last_error)
            stdout = self._run(attempt_prompt, schema_json)
            try:
                parsed = json.loads(extract_json_text(self._unwrap_stdout(stdout)))
                model = schema.model_validate(parsed)
                self._write_log(prompt_version, attempt, started, success=True)
                return model
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)

        self._write_log(prompt_version, self.max_retries, started, success=False, error=last_error)
        raise LLMOutputError(
            f"{self.backend_name} output failed schema validation after "
            f"{self.max_retries + 1} attempts: {last_error}"
        )

    def _run(self, prompt: str, schema_json: dict) -> str:
        raise NotImplementedError

    def _unwrap_stdout(self, stdout: str) -> str:
        return stdout

    def _write_log(
        self,
        prompt_version: str,
        retries: int,
        started: float,
        *,
        success: bool,
        error: str | None = None,
    ) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "backend": self.backend_name,
            "model": self.model,
            "prompt_version": prompt_version,
            "duration_seconds": round(time.monotonic() - started, 3),
            "retries": retries,
            "success": success,
            "error": error,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class ClaudeCodeBackend(BaseCLIBackend):
    backend_name = "claude"

    def _run(self, prompt: str, schema_json: dict) -> str:
        command = [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--tools",
            "",
            "--json-schema",
            json.dumps(schema_json),
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.append(prompt)
        return _run_command(command, self.timeout_seconds, self.backend_name)

    def _unwrap_stdout(self, stdout: str) -> str:
        data = json.loads(stdout)
        if isinstance(data, dict) and "result" in data:
            return str(data["result"])
        return stdout


class CodexBackend(BaseCLIBackend):
    backend_name = "codex"

    def __init__(
        self,
        *,
        effort: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.effort = effort

    def _run(self, prompt: str, schema_json: dict) -> str:
        with tempfile.TemporaryDirectory(prefix="hifc-codex-") as temp_dir:
            temp_path = Path(temp_dir)
            schema_path = temp_path / "schema.json"
            output_path = temp_path / "last-message.txt"
            schema_path.write_text(json.dumps(schema_json), encoding="utf-8")
            command = [
                "codex",
                "exec",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
            ]
            if self.model:
                command.extend(["--model", self.model])
            if self.effort:
                command.extend(["--config", f'model_reasoning_effort="{self.effort}"'])
            command.append(prompt)
            stdout = _run_command(command, self.timeout_seconds, self.backend_name)
            if output_path.exists():
                return output_path.read_text(encoding="utf-8")
            return stdout


class MockBackend:
    def __init__(self, responses: list[BaseModel | dict] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[dict[str, str]] = []

    def complete(self, prompt: str, *, schema: type[T], prompt_version: str) -> T:
        self.calls.append({"prompt": prompt, "prompt_version": prompt_version})
        if not self.responses:
            raise LLMOutputError("MockBackend has no queued responses")
        response = self.responses.pop(0)
        if isinstance(response, BaseModel):
            return schema.model_validate(response.model_dump())
        return schema.model_validate(response)


def backend_from_env() -> LLMBackend:
    backend = os.getenv("HIFC_LLM_BACKEND", "claude")
    timeout = int(os.getenv("HIFC_LLM_TIMEOUT_SECONDS", "300"))
    if backend == "claude":
        return ClaudeCodeBackend(model=os.getenv("HIFC_CLAUDE_MODEL"), timeout_seconds=timeout)
    if backend == "codex":
        return CodexBackend(
            model=os.getenv("HIFC_CODEX_MODEL"),
            effort=os.getenv("HIFC_CODEX_EFFORT"),
            timeout_seconds=timeout,
        )
    raise LLMBackendError(f"Unsupported HIFC_LLM_BACKEND: {backend}")


def _prompt_with_schema(prompt: str, schema_json: dict) -> str:
    return (
        f"{prompt}\n\n"
        "Return only one JSON object that conforms to this JSON Schema. "
        "Do not include Markdown fences or commentary.\n"
        f"{json.dumps(schema_json, ensure_ascii=False)}"
    )


def _retry_prompt(prompt: str, schema_json: dict, last_error: str) -> str:
    return (
        f"{prompt}\n\n"
        "The previous response failed validation. Return only corrected JSON.\n"
        f"Validation error: {last_error}\n"
        f"JSON Schema: {json.dumps(schema_json, ensure_ascii=False)}"
    )


def _run_command(command: list[str], timeout_seconds: int, backend_name: str) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise LLMBackendError(
            f"{backend_name} CLI is not installed or not on PATH. "
            "Install and log in to the local CLI before running real LLM calls."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise LLMBackendError(f"{backend_name} CLI timed out after {timeout_seconds}s") from exc
    except subprocess.CalledProcessError as exc:
        raise LLMBackendError(
            f"{backend_name} CLI failed with exit code {exc.returncode}: {exc.stderr.strip()}"
        ) from exc
    return result.stdout

