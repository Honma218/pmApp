"""プロバイダ出力の検証・正規化（プロバイダ非依存の純関数）。

抽象化層の核。モデル出力（JSON 文字列 / dict）を固定スキーマに正規化する。
- スキーマ外キーは破棄（モデルが項目を増やしても増殖させない）
- 欠損キーは空配列に正規化
- 構造違反（非 dict / 非リスト / 非文字列要素）は SummarizerError
これにより「数値・項目を勝手に増やさない／創作しない」（原則3）をコードで担保する。
要約は parse_summary、追加質問は parse_questions が担当する。
"""

import json

from app.schemas.questions import FollowupQuestion, FollowupQuestions
from app.schemas.summary import SUMMARY_FIELDS, ReportSummary

from .base import SummarizerError


def parse_summary(payload: str | dict) -> ReportSummary:
    """モデル出力を検証・正規化して ReportSummary を返す。失敗時 SummarizerError。"""
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SummarizerError("要約出力が JSON として解釈できません") from exc
    else:
        data = payload

    if not isinstance(data, dict):
        raise SummarizerError("要約出力は JSON オブジェクトである必要があります")

    normalized: dict[str, list[str]] = {}
    for field in SUMMARY_FIELDS:
        value = data.get(field, [])
        if value is None:
            value = []
        if not isinstance(value, list):
            raise SummarizerError(f"フィールド {field} は配列である必要があります")
        items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise SummarizerError(f"{field} の要素は文字列である必要があります")
            stripped = item.strip()
            if stripped:
                items.append(stripped)
        normalized[field] = items

    # スキーマ外キーは normalized に含めない＝破棄される。
    return ReportSummary(**normalized)


def parse_questions(payload: str | dict) -> FollowupQuestions:
    """モデル出力を検証・正規化して FollowupQuestions を返す。失敗時 SummarizerError。

    正規化の方針（parse_summary と同じ思想）:
    - 構造違反（非 dict / questions が非リスト / 要素が非 dict）は SummarizerError。
    - 中身の妥当性は破棄で正規化：未知カテゴリ・空質問・カテゴリ重複（2件目以降）は捨てる。
    - これにより「カテゴリにつき最大1問」「対象カテゴリ以外は出さない」を出力側で担保する。
    """
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SummarizerError("質問出力が JSON として解釈できません") from exc
    else:
        data = payload

    if not isinstance(data, dict):
        raise SummarizerError("質問出力は JSON オブジェクトである必要があります")

    raw_questions = data.get("questions", [])
    if raw_questions is None:
        raw_questions = []
    if not isinstance(raw_questions, list):
        raise SummarizerError("questions は配列である必要があります")

    questions: list[FollowupQuestion] = []
    seen_categories: set[str] = set()
    for item in raw_questions:
        if not isinstance(item, dict):
            raise SummarizerError("questions の要素はオブジェクトである必要があります")
        category = item.get("category")
        question = item.get("question")
        if not isinstance(category, str) or not isinstance(question, str):
            raise SummarizerError("category / question は文字列である必要があります")
        # 未知カテゴリ・空質問・重複カテゴリは破棄（正規化）。
        if category not in SUMMARY_FIELDS:
            continue
        stripped = question.strip()
        if not stripped:
            continue
        if category in seen_categories:
            continue
        seen_categories.add(category)
        questions.append(FollowupQuestion(category=category, question=stripped))

    return FollowupQuestions(questions=questions)
