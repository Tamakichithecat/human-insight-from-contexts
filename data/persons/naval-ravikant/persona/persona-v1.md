# Persona: naval-ravikant (v1)

- generated_at: 2026-07-19T12:35:43.819189+00:00
- generator: claude (prompt_version=persona-extract-v1+persona-synthesize-v1, pipeline_version=0.1.0)
- sources: 2

## Core Values (Schwartz 基本価値)

### この人物は自己決定を中核的な価値として強く重視している。幸福を自ら選択・訓練するスキルと捉え、時間を切り売りせずエクイティを所有して経済的自由を得るべきと述べ、社会が訓練できない固有の知識(specific knowledge)を持つことで代替不可能な独立性を保つことを一貫して主張している。
- claim_id: `claim-core_values-001` / theory_tag: `schwartz:self_direction`
- confidence: **low** (score=0.09, n_evidence=4, n_sources=2, single_source=False, contradiction_present=False)
- evidence:
  - [supports/direct_statement] "Happiness is a choice you make and a skill you develop." (source: src-178fc46da3e78665, origin: paste, locator: sentence:1)
  - [supports/direct_statement] "The mind can be trained just like the body can be trained." (source: src-178fc46da3e78665, origin: paste, locator: sentence:1)
  - [supports/direct_statement] "You're not going to get rich renting out your time. You must own equity, a piece of a business, to gain your financial freedom." (source: src-99823848e336303d, origin: paste, locator: sentence:2)
  - [supports/direct_statement] "Specific knowledge is knowledge that you cannot be trained for. If society can train you, it can train someone else and replace you." (source: src-99823848e336303d, origin: paste, locator: sentence:4)

### この人物は快楽・欲望の追求を幸福の源泉とは見なしていない。欲望を「手に入れるまで不幸でいるという自分自身との契約」と定義しており、感覚的満足や欲求充足を重視する価値観(hedonism)を明確に否定する立場をとっている。
- claim_id: `claim-core_values-002` / theory_tag: `schwartz:hedonism`
- confidence: **low** (score=0.00, n_evidence=1, n_sources=1, single_source=True, contradiction_present=True)
- evidence:
  - [contradicts/direct_statement] "Desire is a contract you make with yourself to be unhappy until you get what you want." (source: src-178fc46da3e78665, origin: paste, locator: sentence:1)

### この人物は社会的地位や他者への優越を目的とすることを否定している。「金や地位ではなく富(wealth)を求めよ」と述べ、ステータス志向の権力価値とは距離を置き、地位よりも自由をもたらす資産の獲得を重視している。
- claim_id: `claim-core_values-003` / theory_tag: `schwartz:power`
- confidence: **low** (score=0.00, n_evidence=1, n_sources=1, single_source=True, contradiction_present=True)
- evidence:
  - [contradicts/direct_statement] "Seek wealth, not money or status." (source: src-99823848e336303d, origin: paste, locator: sentence:1)

### この人物は「社会が欲しているがまだ手に入れる方法を知らないものをスケールで提供することで豊かになる」と述べており、社会的に価値ある成果を大規模に生み出して成功することを重視する達成志向を持つ。ただし前述のとおり、その成功は地位や他者への優越のためではなく自由の獲得を目的としている。
- claim_id: `claim-core_values-004` / theory_tag: `schwartz:achievement`
- confidence: **low** (score=0.01, n_evidence=1, n_sources=1, single_source=True, contradiction_present=False)
- evidence:
  - [supports/direct_statement] "You will get rich by giving society what it wants but does not yet know how to get, at scale." (source: src-99823848e336303d, origin: paste, locator: sentence:3)

## Decision-Making Framework (制御焦点理論 + 行動経済学バイアス)

### この人物は、資産による不労所得・エクイティ所有・スケールする価値提供・複利的な蓄積といった「獲得と向上」を軸に意思決定を行う、明確な促進焦点(promotion focus)を持つ。ただし「欲望は満たされるまで不幸でいる契約だ」という発言(src-178fc46da3e78665-ev003)は欲望駆動の獲得志向と矛盾しており、目標追求そのものは肯定しつつも欲望への執着には批判的距離を置くという、内省を伴った攻めの動機と解釈できる。
- claim_id: `claim-decision_making-001` / theory_tag: `regulatory_focus:promotion`
- confidence: **low** (score=0.01, n_evidence=5, n_sources=2, single_source=False, contradiction_present=True)
- evidence:
  - [supports/direct_statement] "Wealth is having assets that earn while you sleep." (source: src-99823848e336303d, origin: paste, locator: sentence:1)
  - [supports/direct_statement] "You're not going to get rich renting out your time. You must own equity, a piece of a business, to gain your financial freedom." (source: src-99823848e336303d, origin: paste, locator: sentence:2)
  - [supports/direct_statement] "You will get rich by giving society what it wants but does not yet know how to get, at scale." (source: src-99823848e336303d, origin: paste, locator: sentence:3)
  - [supports/direct_statement] "All the returns in life, whether in wealth, relationships, or knowledge, come from compound interest." (source: src-99823848e336303d, origin: paste, locator: sentence:3)
  - [contradicts/direct_statement] "Desire is a contract you make with yourself to be unhappy until you get what you want." (source: src-178fc46da3e78665, origin: paste, locator: sentence:1)

## Behavioral Patterns (Big Five: 開放性・誠実性・情緒安定性)

### この人物は、心や幸福は鍛錬・実践によって形成できると捉えており、長期的な複利効果を重視して人間関係やキャリアを設計するなど、高い自己統制と計画性(誠実性)を示している。
- claim_id: `claim-behavioral_patterns-001` / theory_tag: `bigfive:conscientiousness`
- confidence: **low** (score=0.09, n_evidence=4, n_sources=2, single_source=False, contradiction_present=False)
- evidence:
  - [supports/direct_statement] "The mind can be trained just like the body can be trained." (source: src-178fc46da3e78665, origin: paste, locator: sentence:1)
  - [supports/direct_statement] "happiness is something you have to practice, it's a state that you have to learn to just be in" (source: src-178fc46da3e78665, origin: paste, locator: sentence:2)
  - [supports/direct_statement] "Pick an industry where you can play long-term games with long-term people." (source: src-99823848e336303d, origin: paste, locator: sentence:3)
  - [supports/direct_statement] "All the returns in life, whether in wealth, relationships, or knowledge, come from compound interest." (source: src-99823848e336303d, origin: paste, locator: sentence:3)

### この人物は、習慣や幸福の本質を問い直し、訓練では得られない独自の「特有の知識」を追求するなど、既存の枠組みにとらわれない考え方への開放性(開放性)が高い。
- claim_id: `claim-behavioral_patterns-002` / theory_tag: `bigfive:openness`
- confidence: **low** (score=0.05, n_evidence=2, n_sources=2, single_source=False, contradiction_present=False)
- evidence:
  - [supports/direct_statement] "I think most of our habits, good and bad, are just a proxy for happiness." (source: src-178fc46da3e78665, origin: paste, locator: sentence:2)
  - [supports/direct_statement] "Specific knowledge is knowledge that you cannot be trained for. If society can train you, it can train someone else and replace you." (source: src-99823848e336303d, origin: paste, locator: sentence:4)

## Needs & Concerns (SCARF)

### この人物は自律性(自己決定)への欲求が非常に強い。幸福を「自分で選び、練習によって身につけるスキル」と捉え、時間を切り売りするのではなく資産やエクイティの所有を通じて経済的自由を得るべきだと一貫して主張しており、人生・経済の両面で他者に依存しない自己決定の状態を最重要視している。
- claim_id: `claim-needs_concerns-001` / theory_tag: `scarf:autonomy`
- confidence: **low** (score=0.09, n_evidence=4, n_sources=2, single_source=False, contradiction_present=False)
- evidence:
  - [supports/direct_statement] "Happiness is a choice you make and a skill you develop." (source: src-178fc46da3e78665, origin: paste, locator: sentence:1)
  - [supports/direct_statement] "happiness is something you have to practice, it's a state that you have to learn to just be in" (source: src-178fc46da3e78665, origin: paste, locator: sentence:2)
  - [supports/direct_statement] "Wealth is having assets that earn while you sleep." (source: src-99823848e336303d, origin: paste, locator: sentence:1)
  - [supports/direct_statement] "You're not going to get rich renting out your time. You must own equity, a piece of a business, to gain your financial freedom." (source: src-99823848e336303d, origin: paste, locator: sentence:2)

### この人物は他者との相対的な地位(ステータス)への欲求を明示的に否定している。「富を求めよ、金や地位ではなく」と述べ、社会的地位の追求は富(自由をもたらす資産)の追求と区別すべき劣った動機と位置づけており、ステータスは主要な動機づけ要因ではない。
- claim_id: `claim-needs_concerns-002` / theory_tag: `scarf:status`
- confidence: **low** (score=0.00, n_evidence=1, n_sources=1, single_source=True, contradiction_present=True)
- evidence:
  - [contradicts/direct_statement] "Seek wealth, not money or status." (source: src-99823848e336303d, origin: paste, locator: sentence:1)

### この人物は長期的で信頼できる人間関係を重視しており、「長期的なゲームを長期的な仲間とプレイできる業界を選べ」と助言している。関係性への欲求は情緒的なつながりというより、持続的な信頼と協力関係が複利的な成果を生むという文脈で表れている。
- claim_id: `claim-needs_concerns-003` / theory_tag: `scarf:relatedness`
- confidence: **low** (score=0.01, n_evidence=1, n_sources=1, single_source=True, contradiction_present=False)
- evidence:
  - [supports/direct_statement] "Pick an industry where you can play long-term games with long-term people." (source: src-99823848e336303d, origin: paste, locator: sentence:3)

## Communication Style (Big Five: 外向性・協調性)

_(該当する claim なし)_

## Information Gaps

- 最新のソースでも90ヶ月前の情報であり、情報が古い可能性があります。
