#!/usr/bin/env bash
# PostCompact: compaction で消えた禁止事項を再注入する。
# 「compaction による指示忘れ」はコンテキスト汚染の代表的な失敗パターン（計画書 §6・R-5）。
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cat >/dev/null   # payload は使わないが読み捨てる

hook_log "PostCompact" "reinject" "禁止事項を再注入"

additional_context "PostCompact" "【compaction 後の再注入：M-team の禁止事項（CLAUDE.md §1）】
1. commit / push / DBマイグレーションを実行しない。実行者は統合役ただ1人。
2. acceptance/ 配下を変更しない。受け入れテスト＝仕様＝読み取り専用（ADR-0001）。
3. スライス指示書「3. 触ってよいファイル範囲」の外を変更しない。
4. main 上で作業しない。作業は feature/slice-xx のみ。
5. 実データを持ち込まない。dev は合成フィクスチャのみ。
6. シークレット・PII を出力や差分に混入させない。
7. 緑になったら停止して報告する。次に進まない。緑 ≠ 仕様充足。

自動停止トリガー: 同一エラー2回 / 5ファイル・Edit5回 / 同じテスト3回リトライ → 停止して報告。

なお、コンテキストが膨れている状態です。このまま続けるより、
セッションを捨てて /pickup <issue> から再開したほうが枠効率は良い（CLAUDE.md §4）。"
