# human-insight-from-contexts
Youtube動画、記事、ブログ、SNSなど特定の人物に対する様々な主観・客観コンテクスト情報をもとに、対象者の深層心理まで理解したペルソナを作成する。作成したペルソナに新たなコンテクストをインプットすることで、その人の発言・記述の真意を分析し、受け手が取るべきネクストアクションを導出する

## MVP foundation

このリポジトリは Python 3.12+ / `uv` / pydantic v2 / Typer / pytest / ruff を前提にした CLI アプリケーションとして実装する。

```bash
uv sync --extra dev
uv run hifc --help
uv run pytest
uv run ruff check .
```

`uv` が未導入の環境では、Python 3.12+ の仮想環境に `.[dev]` をインストールして実行できる。

```bash
python -m pip install -e ".[dev]"
hifc --help
pytest
ruff check .
```

## Local LLM CLI assumptions

MVP の LLM 実行は API 直叩きではなくローカル CLI 経由に固定している。実装時点で確認した CLI は次の通り。

- Claude Code: `claude --version` = `2.1.205 (Claude Code)`
- Codex CLI exec: `codex exec --version` = `codex-cli-exec 0.144.5`

`hifc.llm` は `HIFC_LLM_BACKEND=claude|codex` でバックエンドを切り替える。既定は `claude`。

- Claude: `claude --print --output-format json --no-session-persistence --tools "" --json-schema <schema> <prompt>`
- Codex: `codex exec --output-schema <schema-file> --output-last-message <output-file> [--model <model>] [-c model_reasoning_effort="<effort>"] <prompt>`

テストでは実 CLI を呼ばず、`MockBackend` fixture を使う。

## Storage invariants

`SourceDocument.content_hash` と `Persona.source_manifest[].content_hash` は `raw_text` の UTF-8 bytes に対する SHA-256 hex digest とする。Python からは `hifc.storage.source_content_hash(raw_text)` で計算する。storage 層は書込・検証時に hash 不一致、危険な path ID、既存 persona 版の上書きを拒否する。
