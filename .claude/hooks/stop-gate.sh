#!/usr/bin/env bash
# Stop: 「受け入れテスト未通過なら完了扱いにしない」ゲート。
# 注意: Stop hook は 8 連続ブロックで override される仕様＝上限付きゲート。
# 完了の最終担保はあくまで統合役の runner 再検証（計画書 §6）。
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PAYLOAD="$(cat)"
ACTIVE="$(json_field "$PAYLOAD" "d.get('stop_hook_active')")"
# 既にこの hook 起因でループしている場合は素通しする（無限ループ防止）
[[ "$ACTIVE" == "True" || "$ACTIVE" == "true" ]] && exit 0

BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
# feature ブランチ以外（＝上流の作業）ではゲートしない
[[ "$BRANCH" == feature/slice-* ]] || exit 0

LAST_RUN="${PROJECT_DIR}/test-results/.last-run.json"

if [[ ! -f "$LAST_RUN" ]]; then
  block "Stop" "STOP GATE: 受け入れテストの実行結果が見つかりません（test-results/.last-run.json）。
完了を報告する前に、次を実行して生出力を提示してください:
  1. teamdev-test-runner の harness_start → ready 待ち
  2. 受け入れテストの実行（@playwright/test 等）
テストを実行せずに「できました」と報告しないこと（CLAUDE.md §2）。"
fi

STATUS="$(json_field "$(cat "$LAST_RUN")" "d.get('status')")"
if [[ "$STATUS" != "passed" ]]; then
  block "Stop" "STOP GATE: 受け入れテストが緑ではありません（status=${STATUS:-unknown}）。
緑になるまで /implement のループを続けてください。
ただし次のいずれかに当たる場合は押し切らず停止して報告すること:
  - 同一エラーが2回出た → 5 Whys を書く
  - 同じテストを3回リトライして赤 → ハーネスのバグとして報告
  - 5ファイル以上変更した → 影響範囲を報告
（CLAUDE.md §3）"
fi

hook_log "Stop" "allow" "acceptance tests passed"
exit 0
