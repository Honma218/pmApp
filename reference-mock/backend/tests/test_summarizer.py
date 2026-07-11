"""AI 要約抽象化層のテスト（ステップ6 レビュー必須箇所）。

ネットワーク・API キー不要で決定的に回す。検証の核は次の3点:
1. 出力スキーマへの固定・正規化（原則3: 項目を増やさない・創作しない）
2. 設定駆動のプロバイダ差し替え（原則2/7）
3. プロンプトの「数値創作禁止」制約の存在（原則3 の回帰防止）
"""

from types import SimpleNamespace

import pytest

from app.schemas.summary import SUMMARY_FIELDS, ReportSummary
from app.services.summarizer import (
    Summarizer,
    SummarizerError,
    get_summarizer,
    parse_summary,
)
from app.services.summarizer.prompt import (
    NO_FABRICATION_RULE,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.services.summarizer.providers.stub import StubSummarizer


# --- 出力スキーマへの固定・正規化 -----------------------------------------


def test_parse_valid_dict_returns_schema():
    summary = parse_summary(
        {
            "incidents": ["障害対応"],
            "achievements": ["機能Aをリリース"],
            "issues": ["残課題あり"],
            "skills": ["Python", "FastAPI"],
        }
    )
    assert isinstance(summary, ReportSummary)
    assert summary.achievements == ["機能Aをリリース"]
    assert summary.skills == ["Python", "FastAPI"]


def test_parse_accepts_json_string():
    summary = parse_summary('{"achievements": ["x"]}')
    assert summary.achievements == ["x"]


def test_parse_missing_keys_become_empty_lists():
    summary = parse_summary({"achievements": ["x"]})
    assert summary.incidents == []
    assert summary.issues == []
    assert summary.skills == []


def test_parse_drops_unknown_keys():
    # スキーマ外キーは破棄され、出力に現れない（項目を勝手に増やさない）。
    summary = parse_summary({"achievements": ["x"], "evil_extra": ["y"], "score": 99})
    assert set(summary.model_dump().keys()) == set(SUMMARY_FIELDS)


def test_parse_strips_and_drops_empty_items():
    summary = parse_summary({"skills": [" Python ", "", "   "]})
    assert summary.skills == ["Python"]


def test_parse_non_list_field_raises():
    with pytest.raises(SummarizerError):
        parse_summary({"skills": "Python"})


def test_parse_non_string_item_raises():
    # 数値を要素に紛れ込ませる出力を拒否（創作・型崩れの混入を止める）。
    with pytest.raises(SummarizerError):
        parse_summary({"achievements": ["ok", 123]})


def test_parse_broken_json_raises():
    with pytest.raises(SummarizerError):
        parse_summary("{not json")


def test_parse_non_object_raises():
    with pytest.raises(SummarizerError):
        parse_summary("[1, 2, 3]")


# --- 設定駆動のプロバイダ差し替え ------------------------------------------


def _settings(provider=None, api_key=None, model=None):
    return SimpleNamespace(AI_PROVIDER=provider, AI_API_KEY=api_key, AI_MODEL=model)


def test_factory_defaults_to_stub_when_unset():
    assert isinstance(get_summarizer(_settings()), StubSummarizer)


def test_factory_selects_stub_explicitly():
    assert isinstance(get_summarizer(_settings(provider="stub")), StubSummarizer)


def test_factory_gemini_requires_api_key():
    with pytest.raises(SummarizerError):
        get_summarizer(_settings(provider="gemini"))


def test_factory_gemini_with_key_builds_provider():
    summarizer = get_summarizer(_settings(provider="gemini", api_key="k"))
    # 抽象化層の戻り値は Summarizer インターフェースを満たす。
    assert isinstance(summarizer, Summarizer)


def test_factory_unknown_provider_raises():
    with pytest.raises(SummarizerError):
        get_summarizer(_settings(provider="does-not-exist"))


# --- インターフェース実証（差し替え可能性） --------------------------------


def test_stub_is_deterministic_and_schema_compliant():
    stub = StubSummarizer()
    text = "機能Aをリリース\n\n障害対応をした"
    first = stub.summarize(text)
    second = stub.summarize(text)
    assert isinstance(first, ReportSummary)
    assert first == second  # 決定的
    assert first.achievements == ["機能Aをリリース", "障害対応をした"]


def test_caller_depends_only_on_interface():
    # 呼び出し側は Summarizer だけに依存する（具体プロバイダを知らない）。
    class FakeSummarizer:
        def summarize(self, raw_text: str) -> ReportSummary:
            return ReportSummary(issues=[raw_text])

    def run(s: Summarizer, text: str) -> ReportSummary:
        return s.summarize(text)

    result = run(FakeSummarizer(), "課題")
    assert result.issues == ["課題"]


# --- プロンプト制約の固定（原則3 の回帰防止） ------------------------------


def test_prompt_contains_no_fabrication_rule():
    assert NO_FABRICATION_RULE in SYSTEM_PROMPT
    assert "創作しない" in NO_FABRICATION_RULE


def test_user_prompt_embeds_raw_text():
    assert "本日の作業内容" in build_user_prompt("本日の作業内容")
