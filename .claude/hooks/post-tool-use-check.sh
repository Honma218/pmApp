#!/usr/bin/env bash
# PostToolUse(Edit|Write): 非ブロッキング feedback。
# 「ブロック型は少数の致命事項のみ、それ以外は feedback 注入」の使い分け（計画書 §6）。
# 型エラー・lint エラーをモデルに返すだけで、作業は止めない。
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PAYLOAD="$(cat)"
FILE="$(json_field "$PAYLOAD" "d.get('tool_input',{}).get('file_path')")"
REL="${FILE#$PROJECT_DIR/}"

# TS/TSX 以外は何もしない
case "$REL" in
  *.ts|*.tsx) ;;
  *) exit 0 ;;
esac

FEEDBACK=""

# 1. フォーマット（pre-commit と同じ整形をエージェント内でも回し、diff ノイズを減らす）
if [[ -f "${PROJECT_DIR}/node_modules/.bin/prettier" ]]; then
  "${PROJECT_DIR}/node_modules/.bin/prettier" --write "$FILE" >/dev/null 2>&1 || true
fi

# 2. 型チェック（プロジェクト全体。--noEmit）
if [[ -f "${PROJECT_DIR}/node_modules/.bin/tsc" ]]; then
  TSC_OUT="$("${PROJECT_DIR}/node_modules/.bin/tsc" --noEmit -p "${PROJECT_DIR}" 2>&1 | head -20)"
  if [[ -n "$TSC_OUT" ]]; then
    FEEDBACK="${FEEDBACK}
[tsc --noEmit] 型エラーが残っています。推測で any を入れず、原因の型を直してください。
${TSC_OUT}"
  fi
fi

# 3. lint（変更ファイルのみ）
if [[ -f "${PROJECT_DIR}/node_modules/.bin/eslint" ]]; then
  LINT_OUT="$("${PROJECT_DIR}/node_modules/.bin/eslint" "$FILE" 2>&1 | head -20)"
  if [[ -n "$LINT_OUT" ]]; then
    FEEDBACK="${FEEDBACK}
[eslint] ${LINT_OUT}"
  fi
fi

if [[ -n "$FEEDBACK" ]]; then
  hook_log "PostToolUse" "feedback" "tsc/eslint findings on $REL"
  additional_context "PostToolUse" "$FEEDBACK"
fi
exit 0
