"""決定的スタブプロバイダ（オフライン / テスト / 鍵なし開発用）。

ネットワーク・API キーなしで動く決定的実装。AI 推論は行わず、本文の非空行を
そのまま achievements に写すだけ。事実の創作はしない（原則3）。
factory が AI_PROVIDER 未設定 / "stub" のときに選択する。実プロバイダと同じ
Summarizer インターフェースを満たし、差し替え可能性を担保する。
"""

from collections.abc import Mapping

from app.schemas.questions import FollowupQuestion, FollowupQuestions
from app.schemas.summary import SUMMARY_FIELDS, ReportSummary


class StubSummarizer:
    """本文の各行を achievements に写す、推論なしの決定的プロバイダ。"""

    def summarize(self, raw_text: str) -> ReportSummary:
        lines = [line.strip() for line in raw_text.splitlines()]
        achievements = [line for line in lines if line]
        return ReportSummary(achievements=achievements)

    def generate_questions(
        self, thin_by_category: Mapping[str, list[str]]
    ) -> FollowupQuestions:
        """薄いカテゴリごとに定型の質問を1つ返す（AI なし・決定的）。

        SUMMARY_FIELDS 順で安定させ、未知カテゴリは無視する。事実は創作しない。
        """
        questions = [
            FollowupQuestion(
                category=category,
                question=f"「{category}」について、もう少し具体的に書いていただけますか。",
            )
            for category in SUMMARY_FIELDS
            if category in thin_by_category
        ]
        return FollowupQuestions(questions=questions)
