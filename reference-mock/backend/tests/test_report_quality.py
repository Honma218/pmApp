"""粒度判定（スライス1）の検出関数テスト（決定的・DB/.env 非依存）。

検証の核:
1. 対象カテゴリ × ルール検出で「薄い項目」を正しく拾う（短い・空・空白のみ）。
2. 薄くない項目は拾わない／対象外カテゴリは無視する（原則7：設定駆動）。
3. しきい値の境界・堅牢性（不正な値を無視）で決定的に振る舞う。

設定は SimpleNamespace を引数で渡し、.env や get_settings() に依存させない
（tests/test_users_service.py と同じ流儀）。
"""

from types import SimpleNamespace

from app.schemas.summary import SUMMARY_FIELDS
from app.services.report_quality import ThinItem, detect_thin_items


def _settings(*, min_chars=10, targets=None):
    """テスト用の設定スタブ。targets 未指定なら全カテゴリを対象にする。"""
    if targets is None:
        targets = frozenset(SUMMARY_FIELDS)
    return SimpleNamespace(
        REPORT_QUALITY_MIN_CHARS=min_chars,
        REPORT_QUALITY_TARGET_CATEGORIES=frozenset(targets),
    )


def test_detects_short_empty_and_whitespace_only():
    """短い・空文字・空白のみは薄いとして検出される。"""
    summary = {
        "incidents": ["短い", "", "   ", "これは十分に長い具体的な記述です"],
        "achievements": [],
        "issues": [],
        "skills": [],
    }
    thin = detect_thin_items(summary, settings=_settings(min_chars=10))

    # 0:「短い」(2字) / 1:空 / 2:空白のみ は薄い。3 は10字以上なので非薄。
    assert thin == [
        ThinItem(category="incidents", index=0, text="短い"),
        ThinItem(category="incidents", index=1, text=""),
        ThinItem(category="incidents", index=2, text="   "),
    ]


def test_long_items_are_not_thin():
    """min_chars 以上の項目は検出されない。"""
    summary = {
        "incidents": ["十分に長い具体的な内容を記述している"],
        "achievements": ["機能Aをリリースし負荷試験まで完了した"],
        "issues": [],
        "skills": [],
    }
    assert detect_thin_items(summary, settings=_settings(min_chars=10)) == []


def test_empty_category_yields_nothing():
    """空配列のカテゴリからは何も出ない。"""
    summary = {field: [] for field in SUMMARY_FIELDS}
    assert detect_thin_items(summary, settings=_settings()) == []


def test_non_target_categories_are_ignored():
    """対象カテゴリ以外は、薄い項目があっても無視される。"""
    summary = {
        "incidents": ["薄い"],  # 対象外
        "achievements": ["薄い"],  # 対象外
        "issues": ["薄い"],  # 対象（issues のみ）
        "skills": ["薄い"],  # 対象外
    }
    thin = detect_thin_items(summary, settings=_settings(targets={"issues"}))

    assert thin == [ThinItem(category="issues", index=0, text="薄い")]


def test_threshold_boundary():
    """境界：len==min_chars は非薄、min_chars-1 は薄。"""
    summary = {
        "incidents": ["x" * 10, "y" * 9],
        "achievements": [],
        "issues": [],
        "skills": [],
    }
    thin = detect_thin_items(summary, settings=_settings(min_chars=10))

    # 10字ちょうどは非薄、9字は薄い。
    assert thin == [ThinItem(category="incidents", index=1, text="y" * 9)]


def test_ignores_unknown_keys_and_malformed_values():
    """未知キー・配列でない値・文字列でない要素は安全に無視する（堅牢性）。"""
    summary = {
        "incidents": "これは配列ではない",  # list でない → 無視
        "achievements": [None, 123, "短い"],  # 非文字列は無視、"短い" のみ薄い
        "issues": None,  # None → 無視
        "skills": [],
        "unknown_category": ["薄い"],  # SUMMARY_FIELDS 外 → 無視
    }
    thin = detect_thin_items(summary, settings=_settings(min_chars=10))

    assert thin == [ThinItem(category="achievements", index=2, text="短い")]
