"""追加質問生成（粒度判定スライス2）のテスト（決定的・DB/本物AI 非依存）。

検証の核:
1. parse_questions の検証・正規化（原則3: カテゴリ最大1問・対象外/空は破棄・型違反は例外）。
2. StubSummarizer.generate_questions の決定性。
3. degrade ラッパ generate_followup_or_none（10.3: 失敗時は空・薄い項目なしはAIを呼ばず空）。

設定は SimpleNamespace を引数で渡し、.env や get_settings() に依存させない。
本物の Gemini は呼ばない（要約テストと同方針）。
"""

from types import SimpleNamespace

import pytest

from app.schemas.questions import FollowupQuestion, FollowupQuestions
from app.schemas.summary import SUMMARY_FIELDS
from app.services.report_quality import generate_followup_or_none
from app.services.summarizer import SummarizerError, parse_questions
from app.services.summarizer.providers.stub import StubSummarizer


def _settings(*, min_chars=10, targets=None):
    if targets is None:
        targets = frozenset(SUMMARY_FIELDS)
    return SimpleNamespace(
        REPORT_QUALITY_MIN_CHARS=min_chars,
        REPORT_QUALITY_TARGET_CATEGORIES=frozenset(targets),
    )


# --- parse_questions: 正常 -------------------------------------------------


def test_parse_questions_valid():
    payload = {
        "questions": [
            {"category": "issues", "question": "課題を具体的に教えてください"},
            {"category": "skills", "question": "使った技術を教えてください"},
        ]
    }
    result = parse_questions(payload)
    assert isinstance(result, FollowupQuestions)
    assert result.questions == [
        FollowupQuestion(category="issues", question="課題を具体的に教えてください"),
        FollowupQuestion(category="skills", question="使った技術を教えてください"),
    ]


def test_parse_questions_accepts_json_string():
    result = parse_questions(
        '{"questions": [{"category": "issues", "question": "なぜ？"}]}'
    )
    assert result.questions == [FollowupQuestion(category="issues", question="なぜ？")]


# --- parse_questions: 中身の正規化（破棄） --------------------------------


def test_parse_questions_drops_unknown_category():
    payload = {"questions": [{"category": "unknown", "question": "x"}]}
    assert parse_questions(payload).questions == []


def test_parse_questions_drops_empty_question():
    payload = {"questions": [{"category": "issues", "question": "   "}]}
    assert parse_questions(payload).questions == []


def test_parse_questions_dedupes_category_keeps_first():
    payload = {
        "questions": [
            {"category": "issues", "question": "1つ目"},
            {"category": "issues", "question": "2つ目"},
        ]
    }
    assert parse_questions(payload).questions == [
        FollowupQuestion(category="issues", question="1つ目")
    ]


def test_parse_questions_trims_whitespace():
    payload = {"questions": [{"category": "issues", "question": "  詳しく  "}]}
    assert parse_questions(payload).questions == [
        FollowupQuestion(category="issues", question="詳しく")
    ]


def test_parse_questions_missing_questions_key_is_empty():
    assert parse_questions({}).questions == []


# --- parse_questions: 構造違反は例外 --------------------------------------


def test_parse_questions_non_dict_raises():
    with pytest.raises(SummarizerError):
        parse_questions("[]")


def test_parse_questions_questions_not_list_raises():
    with pytest.raises(SummarizerError):
        parse_questions({"questions": "x"})


def test_parse_questions_item_not_dict_raises():
    with pytest.raises(SummarizerError):
        parse_questions({"questions": ["x"]})


def test_parse_questions_non_string_fields_raise():
    with pytest.raises(SummarizerError):
        parse_questions({"questions": [{"category": 1, "question": "x"}]})


def test_parse_questions_invalid_json_string_raises():
    with pytest.raises(SummarizerError):
        parse_questions("not json")


# --- StubSummarizer.generate_questions: 決定性 ----------------------------


def test_stub_generate_questions_is_deterministic_and_ordered():
    stub = StubSummarizer()
    thin = {"skills": ["x"], "issues": ["y"]}  # 入力順は SUMMARY_FIELDS 順と異なる
    first = stub.generate_questions(thin)
    second = stub.generate_questions(thin)

    assert first == second  # 同入力 → 同出力
    # 出力は SUMMARY_FIELDS 順（issues が skills より先）。
    assert [q.category for q in first.questions] == ["issues", "skills"]


def test_stub_generate_questions_ignores_unknown_category():
    stub = StubSummarizer()
    result = stub.generate_questions({"unknown": ["x"], "issues": ["y"]})
    assert [q.category for q in result.questions] == ["issues"]


# --- degrade ラッパ generate_followup_or_none ------------------------------


class _FailingSummarizer:
    """generate_questions が必ず失敗するダミー（degrade 検証用）。"""

    def summarize(self, raw_text):  # pragma: no cover - 使わない
        raise AssertionError("summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):
        raise SummarizerError("生成失敗")


class _ExplodingSummarizer:
    """generate_questions が呼ばれたら失敗するダミー（呼ばれないことの検証用）。"""

    def summarize(self, raw_text):  # pragma: no cover - 使わない
        raise AssertionError("summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):
        raise AssertionError("薄い項目が無ければ呼ばれないはず")


class _RecordingSummarizer:
    """渡された thin_by_category を記録し、固定の質問を返すダミー。"""

    def __init__(self):
        self.received = None

    def summarize(self, raw_text):  # pragma: no cover - 使わない
        raise AssertionError("summarize は呼ばれないはず")

    def generate_questions(self, thin_by_category):
        self.received = dict(thin_by_category)
        return FollowupQuestions(
            questions=[FollowupQuestion(category="issues", question="詳しく？")]
        )


def test_followup_degrades_to_empty_on_failure():
    summary = {"incidents": [], "achievements": [], "issues": ["薄い"], "skills": []}
    result = generate_followup_or_none(
        _FailingSummarizer(), summary, settings=_settings()
    )
    assert result == []  # 生成失敗 → 質問なしで確定へ


def test_followup_skips_ai_when_no_thin_items():
    # すべて十分に長い → 薄い項目なし → AI を呼ばない（呼ばれたら AssertionError）。
    summary = {
        "incidents": ["十分に長い具体的な記述です"],
        "achievements": ["機能Aをリリースし確認まで完了"],
        "issues": [],
        "skills": [],
    }
    result = generate_followup_or_none(
        _ExplodingSummarizer(), summary, settings=_settings()
    )
    assert result == []


def test_followup_returns_questions_and_groups_by_category():
    summary = {
        "incidents": [],
        "achievements": [],
        "issues": ["薄い", "短"],
        "skills": [],
    }
    rec = _RecordingSummarizer()
    result = generate_followup_or_none(rec, summary, settings=_settings())

    # 同カテゴリの薄い項目はまとめて1カテゴリのテキスト群として渡る。
    assert rec.received == {"issues": ["薄い", "短"]}
    assert result == [FollowupQuestion(category="issues", question="詳しく？")]
