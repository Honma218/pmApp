#!/usr/bin/env bash
# PreToolUse(Edit|Write|NotebookEdit): 読み取り専用にすべきパスへの書き込みをブロック。
# ADR-0001「acceptance/ は下流変更禁止」を、宣言・hook・CI の三層で張る唯一の対象。
# 2026-07-11 改修（playbook 未実装 #2・#5）: 書込権をブランチ名で判定（ADR-0004）。
#   spec/*    → acceptance/・docs/spec/ 書込可。backend/・frontend/ は不可
#   feature/* → その逆（acceptance/・docs/spec/ は read-only）
#   reference-mock/ は全ブランチ read-only（ADR-0005。vendor 更新は統合役が手動）
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PAYLOAD="$(cat)"
FILE="$(json_field "$PAYLOAD" "d.get('tool_input',{}).get('file_path') or d.get('tool_input',{}).get('notebook_path')")"
[[ -z "$FILE" ]] && FILE="$PAYLOAD"

# プロジェクトルートからの相対パスに正規化
REL="${FILE#$PROJECT_DIR/}"

# 現在ブランチ（ADR-0004 の判定キー）。git 不在・detached は unknown ＝ fail-closed。
BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

case "$REL" in
  acceptance/*|*/acceptance/*)
    if [[ "$BRANCH" != spec/* ]]; then
      block "PreToolUse:protect-paths" "BLOCKED: acceptance/ への書き込みは spec/* ブランチのみ（ADR-0001・ADR-0004。現在: $BRANCH）。
受け入れテスト＝仕様。テストが赤いのはテストが悪いのではなく実装が足りないからです。
実装側（backend/ frontend/）を直して緑にしてください。
テスト自体に誤りがあると考える場合は、修正せずリーダーへ質問として出して停止すること。"
    fi
    ;;
  docs/spec/*)
    if [[ "$BRANCH" != spec/* ]]; then
      block "PreToolUse:protect-paths" "BLOCKED: docs/spec/（仕様表の正本）への書き込みは spec/* ブランチのみ（ADR-0004。現在: $BRANCH）。"
    fi
    ;;
  backend/*|frontend/*)
    if [[ "$BRANCH" == spec/* ]]; then
      block "PreToolUse:protect-paths" "BLOCKED: spec/* ブランチから backend/ frontend/ は変更できません（CLAUDE.md §1-4）。
実装が仕様ブランチに紛れ込みます。実装は feature/slice-NN で行うこと。"
    fi
    ;;
  reference-mock/*|*/reference-mock/*)
    block "PreToolUse:protect-paths" "BLOCKED: reference-mock/（answer key）は全ブランチで読み取り専用（ADR-0005）。
answer key を書き換えて緑にする経路は塞がれています。vendor 更新は統合役が手動で行います。"
    ;;
  .env|.env.*|*/.env|*/.env.*)
    block "PreToolUse:protect-paths" "BLOCKED: .env への書き込み。シークレットはエージェントが扱いません（CLAUDE.md §1-6）。"
    ;;
  CLAUDE.md|*/CLAUDE.md)
    block "PreToolUse:protect-paths" "BLOCKED: CLAUDE.md（憲法）の中身は PM の所有物です。
自律エージェントに憲法を書き換えさせません。変更提案は /flywheel で
docs/memory-bank/pending-<slug>.md に草案として隔離し、PM 承認を待ってください（CLAUDE.md §10）。"
    ;;
  docs/adr/*)
    block "PreToolUse:protect-paths" "BLOCKED: docs/adr/ は決定の正本。書き戻しは /flywheel の草案 → 人が確定します。"
    ;;
  *.sql|fixtures/real*|*/fixtures/real*)
    block "PreToolUse:protect-paths" "BLOCKED: 実データ / SQL ダンプ。dev は合成フィクスチャのみ（例外なし）。"
    ;;
esac

hook_log "PreToolUse:protect-paths" "allow" "$REL ($BRANCH)"
exit 0
