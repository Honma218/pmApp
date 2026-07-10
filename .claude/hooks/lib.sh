#!/usr/bin/env bash
# 共通ライブラリ。各 hook が source する。
# 設計原則（計画書 §6）:
#   - exit 2 = ブロック（stderr がモデルに返る）
#   - exit 1 = 非ブロッキング。ポリシー強制に exit 1 を使うのは典型的バグ
#   - ブロック時の stderr には「修正指示」を書く（良性のプロンプトインジェクション）

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_DIR="${PROJECT_DIR}/logs/hooks"

# jq_field <json> <python式> : python3 があれば使い、無ければ空を返す
json_field() {
  local payload="$1" expr="$2"
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
v = $expr
print(v if v is not None else '')
" 2>/dev/null
  fi
}

# hook_log <hook名> <decision> <理由>
# 何がいつブロックされたかを JSON Lines で永続化する（Harness-Keeper の監査証跡）。
# ブロック頻度の高いルールが「hook 昇格・スライス設計見直し」の観察データになる。
hook_log() {
  mkdir -p "$LOG_DIR" 2>/dev/null || return 0
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '{"ts":"%s","hook":"%s","decision":"%s","reason":"%s"}\n' \
    "$ts" "${1//\"/\'}" "${2//\"/\'}" "${3//\"/\'}" \
    >> "${LOG_DIR}/$(date -u +%Y-%m).jsonl" 2>/dev/null || true
}

# block <hook名> <モデルに返すメッセージ>
block() {
  hook_log "$1" "block" "$2"
  printf '%s\n' "$2" >&2
  exit 2
}

# additional_context <文字列> : 非ブロッキングでモデルに文脈を注入する
additional_context() {
  local ev="$1" text="$2"
  if command -v python3 >/dev/null 2>&1; then
    EV="$ev" TEXT="$text" python3 -c "
import json, os
print(json.dumps({'hookSpecificOutput': {
    'hookEventName': os.environ['EV'],
    'additionalContext': os.environ['TEXT'],
}}))
"
  else
    printf '%s\n' "$text"
  fi
  exit 0
}
