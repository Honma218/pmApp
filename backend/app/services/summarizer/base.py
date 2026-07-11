"""要約抽象化層のインターフェース（CLAUDE.md 原則2）。

呼び出し側（ドメイン / 後段の API）はこの Summarizer インターフェースだけに依存する。
具体プロバイダ（Gemini / Vertex / Claude 等）の SDK・HTTP は providers/ 配下に隔離し、
ここには持ち込まない。差し替えは factory.get_summarizer の設定解決のみで行う。
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from app.schemas.questions import FollowupQuestions
from app.schemas.summary import ReportSummary


class SummarizerError(Exception):
    """要約・追加質問の生成・解釈に失敗したことを表す（プロバイダ非依存の例外）。"""


@runtime_checkable
class Summarizer(Protocol):
    """テキスト報告を固定スキーマの要約／追加質問に変換するインターフェース。"""

    def summarize(self, raw_text: str) -> ReportSummary:
        """報告本文を受け取り、ReportSummary（固定スキーマ）を返す。

        生成・解釈に失敗した場合は SummarizerError を送出する。
        """
        ...

    def generate_questions(
        self, thin_by_category: Mapping[str, list[str]]
    ) -> FollowupQuestions:
        """薄いカテゴリ（カテゴリ名→薄い項目テキスト群）から追加質問を生成する。

        カテゴリにつき最大1問。FollowupQuestions（固定スキーマ）を返す。
        生成・解釈に失敗した場合は SummarizerError を送出する（degrade は呼び出し側）。
        """
        ...
