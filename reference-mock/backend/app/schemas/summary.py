"""AI 要約の固定出力スキーマ（CLAUDE.md 原則3）。

AI 出力はこのスキーマに固定する。マスターに無い数値・事実を創作させず、
不足は空配列のままにする。フロントの AiSummary 型と同一フィールド名で整合する。
後段で PROJECTS / INCIDENTS / SKILLS へ正規化しやすい最小構造に保つ。
"""

from pydantic import BaseModel, Field

# 要約のカテゴリ（reports.ai_summary_json のキーと一致）。
SUMMARY_FIELDS = ("incidents", "achievements", "issues", "skills")


class ReportSummary(BaseModel):
    """業務報告の構造化要約。各カテゴリは文字列の配列。該当なしは空配列。"""

    incidents: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


# プロバイダにそのまま渡せる JSON スキーマ（構造化出力の強制に用いる）。
# additionalProperties=false でスキーマ外キーの追加を抑止する。
SUMMARY_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        field: {"type": "array", "items": {"type": "string"}}
        for field in SUMMARY_FIELDS
    },
    "required": list(SUMMARY_FIELDS),
    "additionalProperties": False,
}
