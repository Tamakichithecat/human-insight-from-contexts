from __future__ import annotations

SCHWARTZ_VALUES: dict[str, str] = {
    "self_direction": "独立した思考・行動、選択・創造・探求の自由を重視する",
    "stimulation": "刺激・新奇性・挑戦を求める",
    "hedonism": "快楽・感覚的満足を重視する",
    "achievement": "能力を発揮し社会的基準に沿って成功することを重視する",
    "power": "社会的地位・優越、人や資源への統制を重視する",
    "security": "安全・調和・秩序の安定を重視する",
    "conformity": "他者を害したり社会的期待に反したりする言動を抑制する",
    "tradition": "伝統的な習慣・思想の尊重と受容を重視する",
    "benevolence": "身近な他者の幸福の維持・向上を重視する",
    "universalism": "すべての人々と自然の幸福の理解・尊重・寛容・保護を重視する",
}

BIG_FIVE: dict[str, str] = {
    "openness": "新しい経験・アイデア・美的感覚への開放性",
    "conscientiousness": "計画性・責任感・自己統制の高さ",
    "extraversion": "社交性・活発さ・刺激希求の高さ",
    "agreeableness": "協調性・思いやり・他者への信頼の高さ",
    "neuroticism": "情緒不安定さ・不安・ストレス反応の強さ",
}

SCARF: dict[str, str] = {
    "status": "他者との相対的な重要性・地位への感度",
    "certainty": "将来を予測できることへの欲求",
    "autonomy": "選択肢・自己決定の感覚への欲求",
    "relatedness": "他者との安全なつながりへの欲求",
    "fairness": "公正な交換への感度",
}

REGULATORY_FOCUS: dict[str, str] = {
    "promotion": "獲得・向上・理想の達成を志向する(攻めの動機)",
    "prevention": "損失回避・安全・義務の遵守を志向する(守りの動機)",
}

BIAS_CATALOG: dict[str, str] = {
    "loss_aversion": "損失を同等の利得より重く評価する",
    "status_quo": "現状維持を好み変化を避ける",
    "anchoring": "最初に提示された情報に判断が引きずられる",
    "sunk_cost": "既に投じた時間・資金を理由に非合理的に継続する",
    "confirmation": "既存の信念を支持する情報を優先的に集め解釈する",
    "overconfidence": "自身の判断の正確さを過大評価する",
}

_THEORY_GROUPS: dict[str, dict[str, str]] = {
    "schwartz": SCHWARTZ_VALUES,
    "bigfive": BIG_FIVE,
    "scarf": SCARF,
    "regulatory_focus": REGULATORY_FOCUS,
    "bias": BIAS_CATALOG,
}

_GROUP_LABELS: dict[str, str] = {
    "schwartz": "Schwartz 基本価値",
    "bigfive": "Big Five",
    "scarf": "SCARF モデル",
    "regulatory_focus": "制御焦点理論",
    "bias": "行動経済学バイアス(補助タグ、他の主タグと併用可)",
}


def _tag_set(prefix: str, keys: list[str]) -> set[str]:
    return {f"{prefix}:{key}" for key in keys}


ALL_THEORY_TAGS: set[str] = {
    f"{prefix}:{key}" for prefix, group in _THEORY_GROUPS.items() for key in group
}

# DESIGN.md §1.2: Big Five は Behavioral Patterns と Communication Style に分割する。
# extraversion/agreeableness は対人コミュニケーションに直結するため communication_style、
# openness/conscientiousness/neuroticism は状況横断的な行動一貫性のため behavioral_patterns とする。
DIMENSION_TAGS: dict[str, set[str]] = {
    "core_values": _tag_set("schwartz", list(SCHWARTZ_VALUES)),
    "decision_making": _tag_set("regulatory_focus", list(REGULATORY_FOCUS))
    | _tag_set("bias", list(BIAS_CATALOG)),
    "behavioral_patterns": _tag_set(
        "bigfive", ["openness", "conscientiousness", "neuroticism"]
    ),
    "needs_concerns": _tag_set("scarf", list(SCARF)),
    "communication_style": _tag_set("bigfive", ["extraversion", "agreeableness"]),
}

DIMENSION_LABELS: dict[str, str] = {
    "core_values": "Core Values (Schwartz 基本価値)",
    "decision_making": "Decision-Making Framework (制御焦点理論 + 行動経済学バイアス)",
    "behavioral_patterns": "Behavioral Patterns (Big Five: 開放性・誠実性・情緒安定性)",
    "needs_concerns": "Needs & Concerns (SCARF)",
    "communication_style": "Communication Style (Big Five: 外向性・協調性)",
}


def rubric_reference_text() -> str:
    lines: list[str] = []
    for prefix, group in _THEORY_GROUPS.items():
        lines.append(f"### {_GROUP_LABELS[prefix]}")
        for key, description in group.items():
            lines.append(f"- {prefix}:{key} — {description}")
    return "\n".join(lines)


def dimension_rubric_text(dimension: str) -> str:
    tags = DIMENSION_TAGS[dimension]
    lines = [f"### {DIMENSION_LABELS[dimension]}"]
    for prefix, group in _THEORY_GROUPS.items():
        for key, description in group.items():
            tag = f"{prefix}:{key}"
            if tag in tags:
                lines.append(f"- {tag} — {description}")
    return "\n".join(lines)
