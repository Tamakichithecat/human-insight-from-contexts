# DESIGN.md — human-insight-from-contexts MVP 技術設計書

**Author:** Architect
**Date:** 2026-07-19(ユーザー承認反映: 同日)
**Input:** REQUIREMENTS_HANDOFF.md / ARCHITECTURE_INPUT.md / PROJECT_STATUS.md
**Status:** DESIGN_READY(2026-07-19 ユーザー承認済み。LLM 実行方式をローカル CLI に変更、倫理ガイドライン削除 — §11 の承認記録参照)

---

## 0. 設計サマリ

公人(著名人・YouTuber)を対象に、複数ソースのテキスト情報から理論ベースのペルソナを構築し、会議メモ(meeting notes)を入力して真意分析とネクストアクションを導出する **Python CLI アプリケーション** を MVP として構築する。

- **2つのパイプライン**: ①ペルソナ構築(ingest → evidence 抽出 → 理論ベース合成)、②会議メモ分析(persona + notes → 解釈 → 推奨アクション + リスク)
- **理論**: Schwartz 基本価値 / Big Five / SCARF / 制御焦点理論(+行動経済学バイアスカタログ)の4+1層構成
- **Confidence score**: LLM の主観でなく、evidence メタデータから決定論的に算出(コードで計算・単体テスト可能)
- **Source attribution**: 全 claim に evidence 参照必須(スキーマレベルで強制)
- **検証**: cutoff 日方式の retrospective back-testing。判定は VALID / INVALID / UNVERIFIABLE の3値
- **ストレージ**: git 管理可能なファイルベース(JSON + Markdown)。<100 persona 前提で DB 不要
- **LLM**: **ローカル CLI 実行**(Claude Code `claude -p` を既定バックエンド、Codex CLI `codex exec` を代替バックエンドとする抽象化)。API 直叩きはコスト理由で不採用(ユーザー決定)。スキーマ保証はプロンプト埋め込み JSON Schema + コード側 pydantic 検証 + 有限リトライで担保

---

## 1. 心理/サイコグラフィック理論の選定

### 1.1 選定方針

要件は「theory-based, not ad-hoc」。選定基準は (a) 学術的に確立され再現可能、(b) テキストからの推定に先行研究・運用実績がある、(c) 要求される5つのペルソナ次元に写像できる、(d) ビジネス文脈(交渉・営業)で actionable、の4点。

### 1.2 採用する理論(4層+1カタログ)

| 層 | 理論 | 採用理由 | 対応するペルソナ次元 |
|---|---|---|---|
| 価値観 | **Schwartz 基本価値理論**(10基本価値) | 価値観の分類として最も検証された枠組み。文化横断的に妥当性確認済み。テキストからの価値推定研究が存在 | Core Values |
| 性格特性 | **Big Five(五因子モデル)** | 心理測定学的に最も頑健な性格モデル。言語からの Big Five 推定は研究蓄積が厚い(LIWC 系、SNS 言語研究) | Behavioral Patterns / Communication Style |
| 社会的動機 | **SCARF モデル**(Status / Certainty / Autonomy / Relatedness / Fairness) | 対人・交渉場面での「脅威と報酬」を説明する実務向けモデル。会議メモ分析(真意・懸念の解釈)に直結 | Needs & Concerns / Risk Alert |
| 意思決定様式 | **制御焦点理論(Regulatory Focus: promotion / prevention)** | 「攻めの動機か守りの動機か」を判定でき、提案のフレーミング(獲得訴求 vs 損失回避訴求)に直接使える | Decision-Making Framework |
| 補助カタログ | **行動経済学バイアス集**(損失回避、現状維持、アンカリング、サンクコスト等の限定リスト) | 個別の意思決定の癖を注記する語彙として使用。独立の「層」ではなくタグ集 | Decision-Making Framework(注記) |

**明示的に不採用**: MBTI(心理測定学的信頼性が低く再現性要件を満たさない)、Maslow 欲求段階(実証支持が弱く操作化困難)。

### 1.3 推論メカニズム:ルーブリック誘導型 LLM 推論(ハイブリッド)

制約「No proprietary training data available」により教師あり ML は不可。純ルールベースは自然言語の解釈で破綻する。よって:

- 各理論次元ごとに **理論定義の指標(indicator)を列挙したルーブリック** をプロンプトとして固定(例: schwartz:self-direction の言語的兆候リスト)
- LLM の役割は「**evidence の抽出と分類**」(発言の引用、支持/矛盾の stance、直接性の分類、理論タグ付け)に限定
- **スコア計算・集約・閾値判定はすべて Python コードで決定論的に実施**(§3)
- 再現性の担保: プロンプトを版管理(`prompt_version` を全成果物に記録)し、出力 JSON Schema をプロンプトに埋め込んで指示、CLI の応答をコード側で pydantic 検証(不合格時はエラー内容をフィードバックして最大2回リトライ)。LLM 出力の揺らぎはスキーマ強制と決定論的後処理で吸収する

これにより「理論(ルーブリック)→ 信号抽出(LLM)→ 次元への写像と確信度(コード)」の各段が監査可能になる。

---

## 2. Persona schema と source attribution

### 2.1 データレイアウト(ファイルベース)

```text
data/
  persons/<person_id>/
    profile.yaml               # 氏名・別名・カテゴリ・作成日
    sources/<source_id>.json   # 正規化済みソース文書(§4)
    evidence/evidence.jsonl    # 抽出された evidence 単位
    persona/
      persona-v<N>.json        # 構造化ペルソナ(正)
      persona-v<N>.md          # 人間可読レンダリング
    analyses/<date>-<slug>.json / .md   # 会議メモ分析結果
benchmarks/
  cases/<case_id>.yaml         # ベンチマークケース定義
  results/results.jsonl        # 判定結果
```

- ペルソナは**イミュータブル版管理**(v1, v2, …)。ソース追加時は再合成して新版を作成(incremental 更新は Phase 3)
- git 管理でバージョン履歴・監査証跡を確保。将来 DB へ移行する場合も schema は pydantic なのでそのまま移せる

### 2.2 主要スキーマ(pydantic で定義、Developer1 所有)

```python
class Evidence(BaseModel):
    evidence_id: str
    source_id: str
    quote: str                    # 原文からの引用(必須・空不可)
    locator: str                  # チャンク位置/タイムスタンプ等
    directness: Literal["direct_statement", "observed_behavior",
                        "third_party", "inferred"]
    stance: Literal["supports", "contradicts"]
    theory_tags: list[str]        # 例 "schwartz:self_direction", "scarf:autonomy"
    noted_bias: str | None        # 編集バイアス・感情バイアス等の注記

class Confidence(BaseModel):
    score: float                  # 0.0–1.0、§3 の決定論的算出
    band: Literal["high", "medium", "low"]
    n_evidence: int
    n_sources: int
    single_source: bool
    contradiction_present: bool

class Claim(BaseModel):
    claim_id: str
    statement: str                # 推論内容(日本語)
    theory_tag: str               # 上記理論タグ(必須)
    confidence: Confidence
    evidence_refs: list[str]      # Evidence.evidence_id — min_length=1 で強制
    temporal_note: str | None     # 「2023年以前の情報のみ」等

class Persona(BaseModel):
    person_id: str
    persona_version: int
    generated_at: datetime
    generator: GeneratorInfo      # model_id, prompt_version, pipeline_version
    source_manifest: list[SourceRef]   # source_id + content_hash
    core_values: list[Claim]           # Schwartz
    decision_making: list[Claim]       # Regulatory Focus + バイアス注記
    behavioral_patterns: list[Claim]   # Big Five + 観測パターン
    needs_concerns: list[Claim]        # SCARF
    communication_style: list[Claim]   # Big Five + 言語スタイル観測
    information_gaps: list[str]        # 不足情報・次に収集すべきもの
```

### 2.3 Source attribution の強制方法

- `Claim.evidence_refs` は `min_length=1` — **evidence のない claim はスキーマ検証で保存不能**
- 保存時に参照整合性チェック: 全 `evidence_refs` が evidence.jsonl に実在し、全 `Evidence.source_id` が sources/ に実在すること(Dev1 の storage 層で検証)
- `quote` は原文引用必須。検証テストとして「quote が元ソース raw_text に部分一致するか」を自動チェック(fuzzy 許容)
- 「なぜこの結論?」への回答: claim_id → evidence → source と辿る `hifc persona explain <claim_id>` コマンドを提供(透明性要件)

---

## 3. Confidence score の客観算出モデル

**原則: LLM は分類のみ、スコアは純関数。** 同じ evidence 集合からは常に同じスコアが出る(単体テスト可能)。

### 3.1 算出式

claim c の支持 evidence 集合 E+、矛盾 evidence 集合 E− に対し:

```text
w_i    = w_type(source_type_i) × w_direct(directness_i) × decay(age_i)
decay  = exp(−ln2 × age_months / H)          # 半減期 H = 24ヶ月
S      = Σ_{i∈E+} w_i                        # 支持強度
C      = Σ_{j∈E−} w_j                        # 矛盾強度
raw    = max(0, S − λ·C)                     # λ = 1.5(矛盾を重く見る)
base   = 1 − exp(−k·raw)                     # k = 0.7(飽和曲線、上限1未満)
ind    = 1 − 2^(−n_sources)                  # 独立性係数: 1源=0.5, 2源=0.75, 3源=0.875
score  = base × ind
```

### 3.2 重みテーブル(設定ファイル `hifc/scoring/weights.yaml` で外部化)

| source_type | w_type | 根拠 |
|---|---|---|
| 一人称ブログ・note・自著 | 1.00 | 深い自己開示。感情バイアスは directness 側でなく注記で扱う |
| インタビュー・対談記事 | 0.90 | 本人発言だが聞き手の編集介在 |
| 動画・ポッドキャスト書き起こし | 0.70 | 編集・演出バイアス(要件明記) |
| 第三者報道・ニュース | 0.60 | 伝聞・要約 |
| SNS 投稿 | 0.50 | 断片的・文脈欠落 |

| directness | w_direct |
|---|---|
| direct_statement(本人の直接言明) | 1.00 |
| observed_behavior(観測された行動) | 0.80 |
| third_party(第三者の証言) | 0.60 |
| inferred(間接推論) | 0.40 |

### 3.3 バンドと制約

- **high ≥ 0.65 / medium 0.35–0.65 / low < 0.35**
- `n_sources == 1` の claim は `single_source=True` フラグ + score 上限は ind=0.5 により自動的に ≤0.5(=high に到達不可能)→ 単一ソースバイアス防止の要件を構造的に満たす
- 矛盾 evidence が存在する claim は `contradiction_present=True` とし、ペルソナ MD 出力で必ず両論併記
- 定数(H, λ, k, バンド閾値)はすべて weights.yaml に置き、ベンチマーク結果(§6 の calibration)を見て調整する。**初期値は上表の通りとし、調整は Tester/ベンチ結果に基づく**

---

## 4. Ingestion pipeline(URL / PDF / CSV / text)

### 4.1 正規化フォー

```python
class SourceDocument(BaseModel):
    source_id: str                # content_hash 由来(重複取り込み防止)
    person_id: str
    source_type: Literal["blog", "interview", "news", "video_transcript",
                         "sns", "book", "meeting_note", "other"]
    origin: str                   # URL or ファイルパス or "paste"
    title: str | None
    author_perspective: Literal["first_person", "third_party"]
    published_at: date | None     # confidence decay に使用。無指定は取得日で代替+警告
    retrieved_at: datetime
    language: str
    raw_text: str
    chunks: list[Chunk]           # 引用 locator 用の分割
```

### 4.2 入力経路別の処理

| 入力 | 処理 | ライブラリ |
|---|---|---|
| URL(記事・ブログ) | fetch → 本文抽出 → 正規化 | `httpx` + `trafilatura` |
| URL(YouTube) | 字幕/トランスクリプト取得。取得不可時は「手動貼り付けにフォールバック」を明示表示 | `youtube-transcript-api`(利用規約・可用性リスクあり — §9) |
| PDF | テキスト抽出 | `pdfplumber` |
| CSV | 1行=1スニペット(列: text, date, source_type, origin)としてバッチ取り込み。SNS エクスポートや手集めメモ用 | 標準 `csv` |
| テキスト貼り付け / .txt / .md | そのまま | — |

- メタデータ(source_type / published_at / author_perspective)は**ユーザー指定を基本**とし、LLM による自動推定はデフォルト値の提案まで(auto-detect は要件の Open Question のため保守的に)
- 情報が古い(最新 evidence が24ヶ月超)・少ない(ソース2件未満)場合、persona 合成時に `information_gaps` へ警告を出す(要件: warn if too old or too sparse)
- CLI: `hifc ingest url|file|csv|paste --person <id> --type <source_type> --date <published>`

---

## 5. ペルソナ構築パイプライン(Developer2)

```text
sources/*.json
  → [extract] ソースごとに LLM で Evidence 抽出(ルーブリック提示、構造化出力)
  → evidence.jsonl
  → [synthesize] 理論タグごとに evidence を集約し LLM で Claim 文を生成(構造化出力)
  → [score] Python で confidence 算出(§3)・低スコア claim の low バンド付与
  → [validate] スキーマ + 参照整合性 + quote 実在チェック
  → persona-vN.json + persona-vN.md
```

- extract は**ソース1件ずつ独立に**実行(コンテキスト汚染防止、リトライ容易)
- synthesize は理論次元ごとに evidence をグループ化して渡す。claim には LLM に evidence_id を明示的に選ばせ、コード側で整合検証
- LLM 呼び出しは Dev1 の `hifc/llm` ラッパー経由(ローカル CLI バックエンド §8.1、プロンプトは `hifc/prompts/` に版番号付きで格納、出力は pydantic 検証+リトライ)
- CLI: `hifc persona build <person_id>` / `hifc persona show <person_id> [--version N]` / `hifc persona explain <claim_id>`

---

## 6. Meeting notes analysis pipeline(Developer3)

### 6.1 処理フロー

```text
persona-vN + 会議メモ(text/URL/PDF — §4 の ingestion を再利用, source_type=meeting_note)
  → [segment] 対象者の発言・行動単位に分割(LLM)
  → [interpret] 発言ごとに persona の claim を文脈として解釈(LLM, 構造化出力)
       - surface_meaning(表面的な意味)
       - inferred_intent(真意の仮説)
       - supporting_claim_ids(根拠となる persona claim — 必須)
       - misread_risk(読み違えた場合のリスク)
  → [synthesize] 全体所見 + recommended_next_actions + risk_alerts
  → [score] 各解釈の confidence = min(参照 claim の confidence) × 解釈直接度係数
  → AnalysisReport(JSON + MD)
```

### 6.2 AnalysisReport スキーマ(Dev1 定義、Dev3 使用)

```python
class Interpretation(BaseModel):
    statement: str
    surface_meaning: str
    inferred_intent: str
    supporting_claim_ids: list[str]   # min_length=1 — persona に接地しない解釈は不可
    confidence: Confidence
    misread_risk: str

class NextAction(BaseModel):
    action: str
    rationale: str                    # どの解釈・claim に基づくか
    interpretation_refs: list[str]
    prediction_id: str                # ベンチマーク検証用 ID(§7)
    verifiable: bool                  # 公開情報で検証可能な予測か

class AnalysisReport(BaseModel):
    person_id: str
    persona_version: int              # どの版のペルソナで分析したか(検証・再現用)
    meeting_source_id: str
    interpretations: list[Interpretation]
    overall_reading: str
    next_actions: list[NextAction]
    risk_alerts: list[str]
    generated_at: datetime
    generator: GeneratorInfo
```

- 会話履歴の保持は MVP ではしない(各会議メモを独立分析)。ただし `analyses/` に蓄積されるため、Phase 3 で履歴文脈化に拡張可能
- persona 構築と同一理論(SCARF/制御焦点)のルーブリックを interpret プロンプトでも使用(要件: 同一理論の一貫性)
- CLI: `hifc analyze <person_id> --input <file|url|-> [--persona-version N]`

---

## 7. 評価フロー(妥当/不妥当/検証不能)と benchmark harness(Developer3)

### 7.1 3値判定

| 判定 | 意味 |
|---|---|
| `VALID`(妥当) | 予測・分析が公開情報(報道・本人発表・実際の行動)で裏付けられた |
| `INVALID`(不妥当) | 公開情報が予測と矛盾した |
| `UNVERIFIABLE`(検証不能) | 観測可能な結果が存在しない/まだ出ていない |

**UNVERIFIABLE を精度計算の分母に入れない**ことが要件(unknown accuracy の優雅な扱い)の実装。

### 7.2 Retrospective back-testing(公人向けの検証方法)

「過去のある時点までの情報でペルソナを作り、その後に実際に起きたことと突き合わせる」方式。

```yaml
# benchmarks/cases/<case_id>.yaml
case_id: yt-figure-001
person_id: <person_id>
cutoff_date: 2025-06-30          # この日以前のソースのみでペルソナ構築
input_source_ids: [...]           # cutoff 以前のソース(published_at で機械検証)
prediction_tasks:
  - task_id: t1
    prompt: "次の四半期における〇〇に関する公的行動を予測せよ"
    evaluation_window: 2025-07-01/2025-12-31
judge: human                      # MVP は人手判定。判定根拠 URL 必須
```

- ハーネスは `published_at > cutoff_date` のソース混入を**機械的に拒否**(リーク防止)
- 判定結果は `benchmarks/results/results.jsonl` に `{case_id, prediction_id, verdict, evidence_url, judge, judged_at}` で記録
- 会議メモ分析の検証にも同構造を使用: 公開対談・インタビュー動画の書き起こしを「会議メモ」に見立てて分析→その後の実行動で判定

### 7.3 メトリクス(`hifc bench score` が算出)

```text
decided        = VALID + INVALID
precision      = VALID / decided                    # 判定可能ケースでの的中率
coverage       = decided / total                    # 検証可能率
calibration    = precision(high 帯) − precision(low 帯)   # 正であるべき
```

**MVP 成功基準(提案 — ユーザー承認事項):**
- ペルソナ 5 名以上、予測 20 件以上を蓄積
- precision ≥ 60%(decided ベース)かつ coverage ≥ 40%
- calibration > 0(high confidence の claim ほど当たる)— confidence モデルの妥当性検証を兼ねる

### 7.4 自動品質ゲート(CI で常時実行、人手判定不要)

- スキーマ検証・attribution 完全性(全 claim に evidence)100%
- quote 実在チェック合格率 100%
- confidence 算出の決定論性(同一入力→同一スコア)

---

## 8. 技術スタック・共通基盤(Developer1)

| 項目 | 選定 | 理由 |
|---|---|---|
| 言語 | Python 3.12 | LLM/テキスト処理エコシステム、チーム内の既定 |
| パッケージ | `uv` + `pyproject.toml`(パッケージ名 `hifc`) | 高速・lockfile |
| スキーマ | pydantic v2 | 構造化出力(`client.messages.parse`)と直結 |
| CLI | Typer | サブコマンド分割が容易(Dev2/3 が独立に追加可能) |
| LLM | **ローカル CLI 実行**(Claude Code 既定 / Codex 代替、`subprocess` 経由) | API のコスト回避(ユーザー決定)。サブスクリプション枠内で実行 |
| ストレージ | ファイル(JSON/JSONL/YAML/MD)+ git | <100 persona、監査性、DB 運用コストゼロ |
| テスト | pytest(LLM 呼び出しは全てモック/fixture 化) | CI で CLI・ログイン不要 |
| Lint | ruff | — |

### 8.1 LLM バックエンド抽象(Developer1 所有 — 本設計の最重要インターフェース)

```python
class LLMBackend(Protocol):
    def complete(self, prompt: str, *, schema: type[BaseModel],
                 prompt_version: str) -> BaseModel:
        """プロンプトを実行し、schema で検証済みのモデルを返す。
        検証失敗時はエラー内容をフィードバックして最大2回リトライ。
        それでも失敗したら LLMOutputError を送出。"""
```

**バックエンド実装(選択は設定 `HIFC_LLM_BACKEND=claude|codex`、既定 `claude`):**

| 実装 | 呼び出し形 | 備考 |
|---|---|---|
| `ClaudeCodeBackend`(既定) | `claude -p <prompt> --output-format json` を `subprocess` で実行し、JSON envelope の `result` を取得 | `--model` でモデル指定可(既定はユーザーのプラン既定)。単発推論なのでツール実行・複数ターンは不要 — ターン/ツールを最小化するフラグ(`--max-turns 1` 等)の正確な指定は実装時に `claude --help` で確認して固定すること |
| `CodexBackend`(代替) | `codex exec <prompt>` を実行し stdout を取得 | `--model` / `model_reasoning_effort` 指定可(herdr/README の設定に準拠) |

**共通仕様(両バックエンド):**
- プロンプト末尾に出力 JSON Schema と「JSON のみを出力せよ」の指示を機械的に付加(Dev1 のラッパーが担当。Dev2/3 はプロンプト本文と pydantic モデルを渡すだけ)
- 応答からの JSON 取り出しはコードフェンス除去等の頑健なパーサを用意し、pydantic 検証 → 失敗時はエラーメッセージを添えてリトライ(最大2回)
- 呼び出しログ(バックエンド・モデル・プロンプト版・所要時間・リトライ回数)を `data/logs/llm.jsonl` に記録(成果物の `GeneratorInfo` にも記録)
- タイムアウト(既定 300 秒)と、CLI 未インストール/未ログイン時の明確なエラーメッセージ
- テストでは `MockBackend`(fixture 応答を返す)に差し替え。CI は実 CLI を一切呼ばない

**この方式の制約(設計上受容する):**
- API の構造化出力(`output_config.format`)は使えないため、スキーマ保証は「プロンプト指示+検証+リトライ」のベストエフォート。リトライ枯渇はエラーとして表面化させ、静かに壊れたデータを保存しない
- サブスクリプションのレート制限に当たると実行が遅延・失敗し得る。`hifc persona build` はソース単位で逐次実行+進捗表示+失敗ソースのみ再実行できる resume 機構を持つこと(Dev2)

### モジュール所有権(境界厳守)

```text
hifc/schemas/    Dev1   ← 全員が依存するインターフェース。変更は Dev1 のみ
hifc/scoring/    Dev1
hifc/storage/    Dev1
hifc/llm/        Dev1
hifc/cli/app.py  Dev1(骨格)
hifc/ingest/     Dev2
hifc/extract/    Dev2
hifc/persona/    Dev2
hifc/prompts/persona/   Dev2
hifc/analysis/   Dev3
hifc/bench/      Dev3
hifc/render/     Dev3
hifc/prompts/analysis/  Dev3
hifc/cli/ingest.py, persona.py     Dev2
hifc/cli/analyze.py, bench.py      Dev3
tests/           基盤 fixture は Dev1、各自のモジュールのテストは各自
```

Dev2/Dev3 が schemas の変更を必要とする場合は Dev1 に変更依頼を出す(直接編集禁止)。

---

## 9. 担当分担・着手順序・完了条件

### フェーズ 0(Dev1、他をブロックする)

**W1: 基盤構築 — Developer1**
1. `pyproject.toml` / `hifc` パッケージ骨格 / ruff / pytest / CI 設定。`herdr/` と本設計書のコミット
2. `hifc/schemas/`(§2, §4, §6 の全 pydantic モデル)
3. `hifc/scoring/`(§3 の決定論的算出 + weights.yaml + 網羅的単体テスト)
4. `hifc/storage/`(レイアウト §2.1 の read/write、参照整合性・quote 実在チェック、persona 版管理)
5. `hifc/llm/` ラッパー + `hifc/cli/app.py` 骨格 + LLM モック fixture

**完了条件(Dev1)**: 全スキーマの round-trip テスト green / scoring の単体テスト(境界値・単一ソース上限・矛盾ペナルティ・半減期)green / `hifc --help` が動く / fixture で Dev2・Dev3 が LLM なしに開発着手できる。→ `STATUS: DEV_DONE`

### フェーズ 1(Dev1 マージ後、Dev2 と Dev3 は並行)

**W2: ペルソナ構築 — Developer2**(§4, §5)
- ingest 4経路 + YouTube 字幕(フォールバック含む)、extract、synthesize、CLI `ingest` / `persona`
- **完了条件**: fixture ソースからの E2E(ingest→persona-v1 生成)テスト green / 生成 persona が attribution 完全性 100% / 実在の公人1名でローカル CLI 実行し persona-v1.md が §2 の全次元を持つこと / 失敗ソースのみ再実行できる resume 機構(§8.1)

**W3: 分析+ベンチマーク — Developer3**(§6, §7)
- analysis パイプライン、renderer、bench ハーネス(cutoff リーク防止含む)、CLI `analyze` / `bench`
- fixture persona(Dev1 提供)で開発開始できるため Dev2 の完了を待たない
- **完了条件**: fixture persona + サンプル会議メモで AnalysisReport 生成テスト green / 全 interpretation が claim_id に接地 / bench case 1件の run→score が動く / cutoff 後ソース混入がエラーになるテスト green

### フェーズ 2(統合)

- Dev2 の実 persona で Dev3 の analyze/bench を通す統合 E2E(担当: Dev3、Dev2 支援)
- 公人1名: ソース3件以上 ingest → persona v1 → 公開対談を会議メモとして分析 → bench case 登録、まで一気通貫
- → Reviewer レビュー → Tester → EndUser の UAT

### マージ順序

`Dev1(基盤) → Dev2(persona) → Dev3(analysis/bench)`。Dev2 と Dev3 の開発は並行、マージは上記順。コンフリクト面は `hifc/cli/app.py` のサブコマンド登録のみ(登録行を1行ずつに分離して衝突最小化)。

---

## 10. 注意点・リスク

※倫理ガイドライン(旧 §10-1: ETHICS.md・プロンプト制約・免責フッター)は**完全個人利用前提のため設けない**(2026-07-19 ユーザー決定)。ビジネス展開(Phase 2)に進む場合はこの決定を再検討すること。

1. **YouTube 字幕取得**: `youtube-transcript-api` は非公式で利用規約・可用性リスクあり。手動貼り付けフォールバックを一次経路と同格で用意(Dev2 完了条件に含む)
2. **ローカル CLI 依存**: 実行環境に Claude Code(または Codex)のインストールとログインが前提。CLI のバージョンアップで出力フォーマット(JSON envelope)が変わり得るため、パーサは頑健に作り、実装時点の CLI バージョンを README に記録する。サブスクリプションのレート制限で長時間ジョブが中断し得る → resume 機構(§8.1)で緩和
3. **スキーマ保証がベストエフォート**: API の構造化出力が使えないため、検証+リトライで担保(§8.1)。リトライ枯渇は明示的エラーとし、不正データを保存しない
4. **published_at 欠落**: decay 計算が崩れるため、欠落時は取得日代替+ low 方向への保守的扱い+警告
5. **ベンチ判定の人手依存**: MVP では human judge。判定根拠 URL の記録を必須にし、Phase 2 で LLM-assisted 判定を検討
6. **確度定数は仮値**: §3 の H/λ/k/閾値はベンチの calibration で調整する前提。ハードコードせず weights.yaml externalize(Dev1)

---

## 11. 承認記録(2026-07-19 ユーザー承認)

| # | 決定事項 | 結果 |
|---|---|---|
| 1 | 理論セット(§1: Schwartz + Big Five + SCARF + 制御焦点 + バイアスカタログ、MBTI/Maslow 不採用) | **承認** |
| 2 | 技術スタック(§8) | **修正のうえ承認**: API 直叩きは不採用。LLM 実行はローカル環境の Claude Code / Codex CLI 経由に変更(理由: API コスト)。§8.1 に反映済み |
| 3 | Confidence 算出モデルと初期定数(§3) | **承認** |
| 4 | MVP 成功基準の数値(§7.3: 5名/20予測/precision 60%/coverage 40%) | **承認** |
| 5 | 倫理ガイドライン | **削除**: 完全個人利用前提のため設けない。§10 冒頭に記録 |

本書は DESIGN_READY。Orchestrator 経由で Developer1(フェーズ0: 基盤構築)から着手する。
