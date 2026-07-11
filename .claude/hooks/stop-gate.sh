#!/usr/bin/env bash
# Stop: 「対象コードの検証未通過なら完了扱いにしない」ゲート（CLAUDE.md §2）。
# 注意: Stop hook は 8 連続ブロックで override される仕様＝上限付きゲート。
# 完了の最終担保はあくまで統合役の再検証（playbook「スライス単位の関所」）。
#
# 2026-07-11 改修: スコープ変更（業務アプリ再実装 → スライス進捗集計アプリのみ）に伴い、
# 実装パスを backend/frontend → tools/slice-aggregator に修正。
# 現行スコープは runner（teamdev-test-runner-mcp）を使わず pytest で検証するため
# （CLAUDE.md §6）、test-results/.last-run.json 参照から「hook 自身が pytest を実行して
# 判定する」方式に変更した。修正前は backend/frontend が存在しないディレクトリになった
# ため IMPL_CHANGED が常に空になり、ゲートが無言で常に無効化されていた（P6ドッグフーディング
# で発覚）。
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PAYLOAD="$(cat)"
ACTIVE="$(json_field "$PAYLOAD" "d.get('stop_hook_active')")"
# 既にこの hook 起因でループしている場合は素通しする（無限ループ防止）
[[ "$ACTIVE" == "True" || "$ACTIVE" == "true" ]] && exit 0

BRANCH="$(git -C "$PROJECT_DIR" symbolic-ref -q --short HEAD 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
# feature ブランチ以外（＝上流の作業）ではゲートしない
[[ "$BRANCH" == feature/slice-* ]] || exit 0

# main との分岐点（main が未生成なら empty tree）からの差分で
# tools/slice-aggregator の実装ファイルが変わっていない（＝git設定やdocsのみ等）なら
# 検証対象が存在しないためゲートしない。
EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MERGE_BASE="$(git -C "$PROJECT_DIR" merge-base main HEAD 2>/dev/null || echo "$EMPTY_TREE")"
CHANGED_FILES="$( {
  git -C "$PROJECT_DIR" diff --name-only "$MERGE_BASE" HEAD 2>/dev/null
  git -C "$PROJECT_DIR" diff --name-only HEAD 2>/dev/null
  git -C "$PROJECT_DIR" diff --name-only --cached 2>/dev/null
} | sort -u)"
IMPL_CHANGED="$(printf '%s\n' "$CHANGED_FILES" | grep -E '^tools/slice-aggregator/' | grep -vE 'README\.md$' || true)"
[[ -z "$IMPL_CHANGED" ]] && exit 0

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  block "Stop" "STOP GATE: python が見つからず pytest を実行できません。
tools/slice-aggregator/ に変更があるため検証が必須です（CLAUDE.md §2）。環境を確認してください。"
fi
PY="$(command -v python3 || command -v python)"

TEST_OUTPUT="$("$PY" -m pytest "${PROJECT_DIR}/tools/slice-aggregator/tests/" -q 2>&1)"
TEST_RC=$?

if [[ $TEST_RC -ne 0 ]]; then
  block "Stop" "STOP GATE: tools/slice-aggregator/ の pytest が緑ではありません（exit ${TEST_RC}）。
緑になるまで /implement のループを続けてください。生ログ:

${TEST_OUTPUT}

ただし次のいずれかに当たる場合は押し切らず停止して報告すること:
  - 同一エラーが2回出た → 5 Whys を書く
  - 同じテストを3回リトライして赤 → ハーネスのバグとして報告
  - 5ファイル以上変更した → 影響範囲を報告
（CLAUDE.md §3）"
fi

hook_log "Stop" "allow" "pytest passed"
exit 0
