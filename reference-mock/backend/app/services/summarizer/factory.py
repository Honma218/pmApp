"""プロバイダ解決（設定駆動、CLAUDE.md 原則7）。

AI_PROVIDER に応じて Summarizer 実装を返す。呼び出し側はこの関数だけを使い、
具体プロバイダのクラスや SDK を直接 import しない。コード分岐は増やさず、
プロバイダ追加はここの対応表に1行追加するだけにする。
"""

from app.core.config import Settings, get_settings

from .base import Summarizer, SummarizerError
from .providers.gemini import GeminiSummarizer
from .providers.stub import StubSummarizer


def get_summarizer(settings: Settings | None = None) -> Summarizer:
    """設定から Summarizer 実装を解決して返す。

    - 未設定 / "stub": 決定的 stub（鍵不要）
    - "gemini": Gemini Developer API（AI_API_KEY 必須）
    - "vertex": Vertex AI（資格情報は ADC / 環境変数で解決）
    - それ以外: SummarizerError
    """
    settings = settings or get_settings()
    provider = (settings.AI_PROVIDER or "stub").strip().lower()

    if provider == "stub":
        return StubSummarizer()

    if provider == "gemini":
        if not settings.AI_API_KEY:
            raise SummarizerError("gemini プロバイダには AI_API_KEY が必要です")
        return GeminiSummarizer(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)

    if provider == "vertex":
        return GeminiSummarizer(
            api_key=settings.AI_API_KEY, model=settings.AI_MODEL, use_vertex=True
        )

    raise SummarizerError(f"未知の AI_PROVIDER です: {provider}")
