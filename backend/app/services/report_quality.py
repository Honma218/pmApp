"""粒度判定（スライス1）：薄い項目の検出（決定的・AIを呼ばない）。

設計文書 docs/report-quality-design.md の 3.1・3.3 に対応する。判定の引き金は
「管理者が選んだ対象カテゴリ × ルール検出（空・極端に短い）」。対象カテゴリと
しきい値は設定値として読み（原則7：分岐を埋めない）、AI は一切呼ばない（決定的）。

このスライスでは「薄い項目を検出する関数」を提供するだけで、追加質問の生成・表示や
呼び出しの配線は行わない（後続スライス）。検出するだけで、出力を創作・補完しない
（原則3：マスターに無い事実を作らない／不足は空欄のまま）。
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.schemas.questions import FollowupQuestion
from app.schemas.summary import SUMMARY_FIELDS
from app.services.summarizer import Summarizer, SummarizerError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThinItem:
    """薄いと判定された項目1件。どのカテゴリの何番目の項目かと、その本文を保持する。"""

    category: str
    index: int
    text: str


def detect_thin_items(
    summary: Mapping[str, object],
    settings: Settings | None = None,
) -> list[ThinItem]:
    """要約結果から「薄い項目」を決定的に検出して返す。

    入力 ``summary`` は ai_summary_json 相当（カテゴリ名 → 項目（文字列）の配列）。
    対象カテゴリ（設定値）に属する項目のうち、前後空白を除いた文字数が
    ``REPORT_QUALITY_MIN_CHARS`` 未満のもの（空・空白のみを含む）を薄いとみなす。

    - 設定は引数で差し替え可能（既定は get_settings()）。テスト容易性のため。
    - カテゴリ名は SUMMARY_FIELDS を唯一の出どころとし、固定順で走査する（決定的）。
    - 値が配列でない／要素が文字列でないものは安全に無視する（堅牢性）。
    """
    settings = settings or get_settings()
    targets = settings.REPORT_QUALITY_TARGET_CATEGORIES
    min_chars = settings.REPORT_QUALITY_MIN_CHARS

    thin: list[ThinItem] = []
    # SUMMARY_FIELDS の固定順で走査することで、同入力なら必ず同順の結果になる。
    for category in SUMMARY_FIELDS:
        if category not in targets:
            continue
        items = summary.get(category)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, str):
                continue
            if len(item.strip()) < min_chars:
                thin.append(ThinItem(category=category, index=index, text=item))
    return thin


def generate_followup_or_none(
    summarizer: Summarizer,
    summary: Mapping[str, object],
    settings: Settings | None = None,
) -> list[FollowupQuestion]:
    """薄い項目があれば追加質問を生成して返す。生成失敗時は空リスト（degrade）。

    設計 10.3：質問生成が失敗しても追加質問なしで確定フローへ戻せるよう、ここで
    SummarizerError を吸収して空リストを返す（報告は必ず出せる＝10.1）。例外は
    プロバイダ側で握りつぶさず SummarizerError として上げ、degrade 判断はこの
    ドメイン層で行う（設計 10.7・教訓2：種別を失わない）。

    - 薄い項目が無ければ AI を呼ばずに空リストを返す。
    - 抽象化層へは ThinItem ではなく「カテゴリ → 薄い項目テキスト群」の素な形で渡す
      （レイヤーの向きを保つ）。detect_thin_items が SUMMARY_FIELDS 順なので、この
      マップも同じ順序になる。
    """
    settings = settings or get_settings()
    thin = detect_thin_items(summary, settings)
    if not thin:
        return []  # 薄い項目なし → AI を呼ばない

    thin_by_category: dict[str, list[str]] = {}
    for item in thin:
        thin_by_category.setdefault(item.category, []).append(item.text)

    try:
        result = summarizer.generate_questions(thin_by_category)
    except SummarizerError as exc:
        # degrade：質問なしで確定フローへ戻す（10.3）。失敗は種別だけ残す（10.7）。
        # メッセージに鍵などの秘匿値を載せない運用（原則10）。
        logger.warning("followup question generation failed: %s", type(exc).__name__)
        return []
    return list(result.questions)
