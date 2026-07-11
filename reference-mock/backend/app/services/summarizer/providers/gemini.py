"""Gemini / Vertex AI プロバイダ実装（具体依存をここに隔離）。

CLAUDE.md 原則2: 具体プロバイダの SDK 依存はこのモジュールにのみ閉じ込める。
google-genai SDK は遅延 import し、未インストール環境でも抽象化層・stub の
読み込みを妨げない。構造化出力（response_schema）でスキーマを強制し、得た JSON は
parse_summary でさらに検証・正規化する（二重の防御）。

google-genai は API キー（Gemini Developer API）と Vertex AI の両方に対応する。
use_vertex=True のときは Vertex（プロジェクト/リージョンは ADC・環境変数で解決）。
"""

from collections.abc import Mapping

from app.schemas.questions import QUESTION_RESPONSE_SCHEMA, FollowupQuestions
from app.schemas.summary import SUMMARY_RESPONSE_SCHEMA, ReportSummary

from ..base import SummarizerError
from ..parsing import parse_questions, parse_summary
from ..prompt import (
    QUESTION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_question_prompt,
    build_user_prompt,
)

# Gemini の既定モデル（AI_MODEL 未設定時）。
DEFAULT_MODEL = "gemini-2.5-flash"

# Gemini / Vertex の response_schema は OpenAPI サブセットで additionalProperties を
# 受け付けず、含めると 400 INVALID_ARGUMENT で拒否される。これはプロバイダ固有の
# 制約なので共通スキーマ（schemas/summary.py）は変えず、ここで除去して隔離する
# （CLAUDE.md 原則2）。スキーマ外キーの抑止は出力側 parse_summary が担保済み。
_GEMINI_RESPONSE_SCHEMA = {
    k: v for k, v in SUMMARY_RESPONSE_SCHEMA.items() if k != "additionalProperties"
}


class GeminiSummarizer:
    """google-genai 経由で Gemini / Vertex を呼ぶ Summarizer 実装。"""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None = None,
        use_vertex: bool = False,
    ) -> None:
        self._api_key = api_key
        self._model = model or DEFAULT_MODEL
        self._use_vertex = use_vertex

    def summarize(self, raw_text: str) -> ReportSummary:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - 環境依存
            raise SummarizerError(
                "google-genai がインストールされていません（AI 要約には依存が必要）"
            ) from exc

        client = (
            genai.Client(vertexai=True)
            if self._use_vertex
            else genai.Client(api_key=self._api_key)
        )
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=build_user_prompt(raw_text),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_GEMINI_RESPONSE_SCHEMA,
                    temperature=0,
                ),
            )
        except Exception as exc:  # プロバイダ固有例外を抽象化層の例外に変換
            raise SummarizerError("要約プロバイダの呼び出しに失敗しました") from exc

        if not response.text:
            raise SummarizerError("要約プロバイダが空の応答を返しました")
        return parse_summary(response.text)

    def generate_questions(
        self, thin_by_category: Mapping[str, list[str]]
    ) -> FollowupQuestions:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - 環境依存
            raise SummarizerError(
                "google-genai がインストールされていません（AI 追加質問には依存が必要）"
            ) from exc

        client = (
            genai.Client(vertexai=True)
            if self._use_vertex
            else genai.Client(api_key=self._api_key)
        )
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=build_question_prompt(thin_by_category),
                config=types.GenerateContentConfig(
                    system_instruction=QUESTION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    # QUESTION_RESPONSE_SCHEMA は additionalProperties を含まないため
                    # そのまま渡せる（要約での 400 の教訓＝設計 10.8 を踏まえた設計）。
                    response_schema=QUESTION_RESPONSE_SCHEMA,
                    temperature=0,
                ),
            )
        except Exception as exc:  # プロバイダ固有例外を抽象化層の例外に変換
            raise SummarizerError("質問生成プロバイダの呼び出しに失敗しました") from exc

        if not response.text:
            raise SummarizerError("質問生成プロバイダが空の応答を返しました")
        return parse_questions(response.text)
