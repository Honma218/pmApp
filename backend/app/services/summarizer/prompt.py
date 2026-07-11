"""要約・追加質問のプロンプト（プロバイダ非依存）。

CLAUDE.md 原則3 の中核制約をプロンプトに明記する。具体プロバイダはこの定数を
共有し、出力は要約は SUMMARY_RESPONSE_SCHEMA、追加質問は QUESTION_RESPONSE_SCHEMA
に固定する。
"""

from collections.abc import Mapping

# 数値・事実を創作させない制約（原則3）。回帰防止のためテストでも参照する。
NO_FABRICATION_RULE = (
    "報告本文に書かれていない情報を創作しないこと。"
    "数値・固有名詞・日付・成果などの事実を推測や補完で追加してはならない。"
    "該当する内容が無いカテゴリは空配列にすること。"
)

SYSTEM_PROMPT = (
    "あなたは客先常駐スタッフの業務報告を構造化要約するアシスタントです。"
    "報告本文を読み、次の4カテゴリに分類して JSON で出力してください。\n"
    "- incidents: 発生した事象・対応した出来事\n"
    "- achievements: 達成したこと・完了した作業\n"
    "- issues: 課題・懸念・ブロッカー\n"
    "- skills: 使用した技術・スキル\n"
    f"{NO_FABRICATION_RULE}\n"
    "出力は指定されたスキーマの JSON のみとし、説明文や前置きは含めないこと。"
)


def build_user_prompt(raw_text: str) -> str:
    """報告本文を要約対象として提示するユーザープロンプトを組み立てる。"""
    return (
        "次の業務報告を、指定スキーマに従って要約してください。\n\n"
        "--- 業務報告ここから ---\n"
        f"{raw_text}\n"
        "--- 業務報告ここまで ---"
    )


# --- 追加質問（粒度判定スライス2） ---

# 質問生成の制約（原則3）。答えを創作・示唆せず、本人に書いてもらう誘導に徹する。
QUESTION_SYSTEM_PROMPT = (
    "あなたは客先常駐スタッフの業務報告を支援するアシスタントです。"
    "ある報告で、内容が薄い（具体性が不足している）カテゴリが見つかりました。"
    "各カテゴリについて、本人がもう少し具体的に書けるよう促す質問を1つだけ作ってください。\n"
    "- 質問は対象カテゴリごとに最大1つ。渡されたカテゴリ以外への質問は作らないこと。\n"
    "- 質問は本人に書いてもらうための誘導であり、答えを推測・提示・創作してはならない。\n"
    "- 報告に書かれていない事実（数値・固有名詞・日付・成果など）を質問文に混ぜないこと。\n"
    "- 尋問のように問い詰めず、一度で答えやすい簡潔な問いにすること。\n"
    "出力は指定されたスキーマの JSON のみとし、説明文や前置きは含めないこと。"
)

# カテゴリ名の日本語ラベル（プロンプト提示用。判定・スキーマには影響しない）。
_CATEGORY_LABELS = {
    "incidents": "発生した事象・対応した出来事",
    "achievements": "達成したこと・完了した作業",
    "issues": "課題・懸念・ブロッカー",
    "skills": "使用した技術・スキル",
}


def build_question_prompt(thin_by_category: Mapping[str, list[str]]) -> str:
    """薄いと判定されたカテゴリと項目を提示し、質問生成を促すプロンプトを組み立てる。

    thin_by_category: カテゴリ名 → そのカテゴリで薄いと検出された項目テキストの配列。
    具体プロバイダ非依存（ThinItem 等のドメイン型には依存しない）。
    """
    lines = [
        "次のカテゴリは内容が薄いと判定されました。",
        "各カテゴリにつき、本人がもう少し具体的に書けるよう促す質問を1つ作ってください。",
        "",
    ]
    for category, items in thin_by_category.items():
        label = _CATEGORY_LABELS.get(category, category)
        lines.append(f"## カテゴリ: {category}（{label}）")
        if items:
            lines.append("現在の（薄い）記述:")
            for item in items:
                shown = item.strip() or "（空）"
                lines.append(f"- {shown}")
        else:
            lines.append("現在の記述: （なし）")
        lines.append("")
    return "\n".join(lines).rstrip()
