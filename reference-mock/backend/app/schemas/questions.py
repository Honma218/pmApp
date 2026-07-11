"""AI 追加質問の固定出力スキーマ（CLAUDE.md 原則3）。

薄い項目が見つかったカテゴリごとに、追加質問を1つ生成する（カテゴリ単位で最大1問）。
AI 出力はこのスキーマに固定し、答えの創作・示唆をさせない（質問は本人に書いて
もらうための誘導）。カテゴリ名は SUMMARY_FIELDS を唯一の出どころとして共有する。
"""

from pydantic import BaseModel, Field

from app.schemas.summary import SUMMARY_FIELDS


class FollowupQuestion(BaseModel):
    """1カテゴリへの追加質問。カテゴリにつき最大1つ。"""

    category: str
    question: str


class FollowupQuestions(BaseModel):
    """追加質問の集合（カテゴリごとに最大1問）。該当なしは空配列。"""

    questions: list[FollowupQuestion] = Field(default_factory=list)


class FollowupAnswer(BaseModel):
    """追加質問への回答1件。質問文は3aが返したものをクライアントがエコーバックする
    （質問は保存しない設計＝別保存しない・本文に溶かす）。本文への追記体裁に用いる。"""

    category: str
    question: str
    answer: str


class FollowupAnswersIn(BaseModel):
    """回答の受け取り（スライス3b 入力）。本文末尾へ追記し要約を作り直す。"""

    answers: list[FollowupAnswer] = Field(default_factory=list)


# プロバイダにそのまま渡せる JSON スキーマ（構造化出力の強制に用いる）。
# additionalProperties は付けない（Gemini の response_schema が未対応＝10.8 の教訓。
# スキーマ外キーの抑止は出力側 parse_questions が担保する）。
QUESTION_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": list(SUMMARY_FIELDS)},
                    "question": {"type": "string"},
                },
                "required": ["category", "question"],
            },
        },
    },
    "required": ["questions"],
}
