# Herdr Workspace Setup for human-insight-from-contexts

このリポジトリ用の Herdr workspace、tab、agent を一括作成し、agent ごとの初期プロンプトを送るためのセットアップです。

## 使い方

この script は clone 済みのこの repo から実行する前提です。repo root は script の場所から自動検出します。

```bash
cd /Users/okazakihayato/human-insight-from-contexts
./herdr/scripts/setup-herdr-workspace.sh
```

指定先に `.git` がない場合は停止します。

副作用なしで作成予定の内容だけ見る場合:

```bash
DRY_RUN=1 ./herdr/scripts/setup-herdr-workspace.sh
```

## ファイル構成

```text
herdr/
  README.md
  prompts/
    end_user.md
    orchestrator.md
    requirements.md
    architect.md
    developer1.md
    developer2.md
    developer3.md
    reviewer.md
    reviewer2.md
    reviewer3.md
    tester.md
  scripts/
    setup-herdr-workspace.sh
```

## 作成する Herdr 構成

- workspace: `<app-name>`
- tabs: `orchestrator`, `end-user`, `requirements`, `architecture`, `developer-1`, `developer-2`, `developer-3`, `review-1`, `review-2`, `review-3`, `testing`
- agents:
  - `Orchestrator`
  - `EndUser`
  - `Requirements`
  - `Architect`
  - `Developer1`
  - `Developer2`
  - `Developer3`
  - `Reviewer1`
  - `Reviewer2`
  - `Reviewer3`
  - `Tester`

## 編集する場所

- agent の役割指示: `prompts/*.md`
- provider、model、effort: `scripts/setup-herdr-new-app.sh`

`scripts/setup-herdr-new-app.sh` の上部にある `*_PROVIDER`、`*_MODEL`、`*_EFFORT` を編集すると、agent ごとにモデルと推論 effort を変えられます。

## デフォルトのモデル配分

| Agent | Provider | Model | Effort |
| --- | --- | --- | --- |
| Orchestrator | codex | gpt-5.5 | low |
| EndUser | claude | haiku | medium |
| Requirements | codex | gpt-5.5 | high |
| Architect | claude | fable | xhigh |
| Developer1 | codex | gpt-5.5 | high |
| Developer2 | claude | sonnet | high |
| Developer3 | claude | sonnet | high |
| Reviewer1 | codex | gpt-5.5 | xhigh |
| Reviewer2 | claude | sonnet | high |
| Reviewer3 | claude | haiku | medium |
| Tester | claude | haiku | medium |

例:

```bash
REVIEWER1_PROVIDER="${REVIEWER1_PROVIDER:-codex}"
REVIEWER1_MODEL="${REVIEWER1_MODEL:-gpt-5.5}"
REVIEWER1_EFFORT="${REVIEWER1_EFFORT:-xhigh}"

REVIEWER2_PROVIDER="${REVIEWER2_PROVIDER:-claude}"
REVIEWER2_MODEL="${REVIEWER2_MODEL:-sonnet}"
REVIEWER2_EFFORT="${REVIEWER2_EFFORT:-high}"

ARCHITECT_PROVIDER="${ARCHITECT_PROVIDER:-claude}"
ARCHITECT_MODEL="${ARCHITECT_MODEL:-fable}"
ARCHITECT_EFFORT="${ARCHITECT_EFFORT:-xhigh}"
```

実行時だけ変える場合:

```bash
REVIEWER1_MODEL="gpt-5.5" REVIEWER1_EFFORT="high" ./scripts/setup-herdr-new-app.sh my-new-app
```

Claude 側で特定モデル名を使う場合:

```bash
ARCHITECT_MODEL="sonnet" ARCHITECT_EFFORT="high" ./scripts/setup-herdr-new-app.sh my-new-app
```

Claude CLI は `--model` に `sonnet`、`fable`、`opus` などの alias、または CLI が受け付けるフルモデル名を指定できます。
Codex CLI は `--model` と `model_reasoning_effort` を使います。

## Prompt の流れ

1. `setup-herdr-new-app.sh` が workspace と tabs を作成する
2. 各 tab に agent を起動する
3. `prompts/*.md` の内容を対応する agent に `herdr agent send` で送る

## 基本の使い方

通常は `Orchestrator` と会話します。

`Orchestrator` は現在のフェーズ、次に動かす agent、人間の合意が必要な箇所を管理します。利用者が毎回 agent を切り替えると状態管理が人間側に戻るため、迷ったら `Orchestrator` に話してください。

専門的に深掘りしたい場合だけ、該当 agent と直接会話します。

例:

- 技術選定を深く相談する: `Architect`
- 利用シナリオや UAT 観点を出す: `EndUser`
- 特定ブランチを厳密に見る: `Reviewer1`
- 個別作業を実装させる: `Developer1` / `Developer2` / `Developer3`

直接 agent と話した後は、結果を `Orchestrator` に戻してください。

ここでいう結果は、会話全文ではなく、次に進むために必要な要約です。

- 決まったこと
- 決まらなかったこと
- 変更された前提
- agent が出した `STATUS`
- 次に動かすべき agent
- 人間の合意が必要な点

`Orchestrator` に戻す例:

```text
Architect と直接相談しました。

決定:
- フロントエンドは React
- バックエンドはまだ未定
- MVP ではログイン機能を後回し

未決:
- データ保存を SQLite にするか Supabase にするか

Architect の STATUS:
STATUS: NEEDS_USER_APPROVAL

次はこの設計案について合意確認してください。
```

運用ルール:

```text
迷ったら Orchestrator
専門的な深掘りは該当 agent
状態管理は Orchestrator に戻す
```

## STATUS ルール

各 agent は応答の最後の行に `STATUS:` を出します。Orchestrator はこの STATUS を見て、次に動かす agent と依頼内容を決めます。

主な STATUS:

- `STATUS: NEEDS_INPUT`
- `STATUS: NEEDS_USER_APPROVAL`
- `STATUS: REQUIREMENTS_READY`
- `STATUS: DESIGN_READY`
- `STATUS: DEV_DONE`
- `STATUS: REVIEW_PASS`
- `STATUS: REVIEW_FAIL: <理由>`
- `STATUS: TEST_PASS`
- `STATUS: TEST_FAIL: <理由>`
- `STATUS: UAT_PASS`
- `STATUS: UAT_FAIL: <理由>`
- `STATUS: DONE`
