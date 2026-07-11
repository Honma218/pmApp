"""AI 要約の抽象化層（公開 API）。

呼び出し側はここから Summarizer / get_summarizer / SummarizerError のみを使う。
具体プロバイダの実装は providers/ 配下に隔離されており、直接 import しないこと。
"""

from .base import Summarizer, SummarizerError
from .factory import get_summarizer
from .parsing import parse_questions, parse_summary

__all__ = [
    "Summarizer",
    "SummarizerError",
    "get_summarizer",
    "parse_summary",
    "parse_questions",
]
