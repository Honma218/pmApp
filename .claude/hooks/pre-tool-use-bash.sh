#!/usr/bin/env bash
# PreToolUse(Bash): 不可逆・高コスト操作の deny-list。
# 「宣言と機械的強制のペア設計」の強制側。CLAUDE.md §1 と同じルールを機械で張る。
# 2026-07-11 改修（playbook 未実装 #1）: commit/push の全面ブロックを廃止し、
# 「main を進める操作のみ」ブロックに緩和。作業ブランチ（spec/* / feature/*）の commit/push は許可。
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PAYLOAD="$(cat)"
CMD="$(json_field "$PAYLOAD" "d.get('tool_input',{}).get('command')")"
[[ -z "$CMD" ]] && CMD="$PAYLOAD"   # python3 が無い環境では生 JSON を対象にする（fail-closed 側）

deny() { block "PreToolUse:Bash" "$1"; }

# --- main を進める操作: 統合役の専権（CLAUDE.md §1-1） ---
# 現在ブランチで判定する。git 不在・detached 等は unknown ＝ fail-closed（ブロック側に倒す）。
# symbolic-ref は unborn HEAD（commit 0件の新規ブランチ）でもブランチ名を返せる。
# rev-parse --abbrev-ref HEAD は unborn HEAD で失敗するため、フォールバックとしてのみ使う。
BRANCH="$(git -C "$PROJECT_DIR" symbolic-ref -q --short HEAD 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

if [[ "$CMD" =~ (^|[[:space:];&|])git[[:space:]]+commit ]]; then
  case "$BRANCH" in
    feature/*|spec/*) : ;;  # 作業ブランチの commit は許可（CLAUDE.md §1-1）
    *)
      deny "BLOCKED: ブランチ '$BRANCH' 上での git commit。commit は作業ブランチ（feature/slice-NN / spec/slice-NN）でのみ許可。
main を進める操作は統合役ただ1人（CLAUDE.md §1-1）。"
      ;;
  esac
fi

if [[ "$CMD" =~ (^|[[:space:];&|])git[[:space:]]+push ]]; then
  # ① force push は全ロール禁止
  if [[ "$CMD" =~ --force ]] || [[ "$CMD" =~ push[[:space:]]+-[a-zA-Z]*f ]] || [[ "$CMD" =~ push[[:space:]]+[^[:space:]]+[[:space:]]+\+ ]]; then
    deny "BLOCKED: force push。履歴を書き換える操作は全ロール禁止（CLAUDE.md §1-1）。"
  fi
  # ② main/master 宛の push（refspec 明示 or main 上からの push）は統合役のみ
  if [[ "$CMD" =~ push[[:space:]].*[[:space:]:](main|master)([[:space:]]|$) ]] \
  || [[ "$BRANCH" == "main" || "$BRANCH" == "master" || "$BRANCH" == "unknown" ]]; then
    deny "BLOCKED: main を進める push。main へのマージ・push は統合役ただ1人（CLAUDE.md §1-1）。
作業ブランチ（feature/* / spec/*）の push は許可されている。/submit で PR を作り、統合役 → 層境ゲートへ渡すこと。"
  fi
fi

# --- 破壊的 git ---
if [[ "$CMD" =~ git[[:space:]]+reset[[:space:]]+--hard ]] \
|| [[ "$CMD" =~ git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f ]] \
|| [[ "$CMD" =~ git[[:space:]]+branch[[:space:]]+-D ]] \
|| [[ "$CMD" =~ git[[:space:]]+checkout[[:space:]]+(--[[:space:]])?\. ]]; then
  deny "BLOCKED: 破壊的な git 操作。作業結果を消す前に人に相談すること。
やり直したい場合はセッションを捨てて /pickup から再開する（CLAUDE.md §4）。"
fi

# --- ファイル破壊 ---
if [[ "$CMD" =~ rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*-[a-zA-Z]*r[a-zA-Z]*f ]] \
|| [[ "$CMD" =~ rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*-[a-zA-Z]*f[a-zA-Z]*r ]]; then
  deny "BLOCKED: rm -rf。不可逆操作。削除が必要ならリーダーへ質問として出して停止すること。"
fi

# --- DB マイグレーション / スキーマ変更 ---
if [[ "$CMD" =~ (prisma[[:space:]]+migrate|typeorm[[:space:]]+migration|knex[[:space:]]+migrate|run[[:space:]]+migrate|flyway|liquibase) ]] \
|| [[ "$CMD" =~ (DROP|TRUNCATE|ALTER)[[:space:]]+TABLE ]] \
|| [[ "$CMD" =~ (DROP|TRUNCATE|ALTER)[[:space:]]+table ]]; then
  deny "BLOCKED: DB マイグレーション / スキーマ変更。層境（不可逆変更）の操作。
実行は統合役、GO/NO-GO 判断は上流リーダー（CLAUDE.md §7）。差分に必要性を書いて停止すること。"
fi

# --- main ブランチ上での作業（高速フェイル。正本は GitHub ブランチ保護） ---
if [[ "$CMD" =~ git[[:space:]]+(checkout|switch)[[:space:]]+(main|master)([[:space:]]|$) ]]; then
  deny "BLOCKED: main への checkout。作業は feature/slice-<issue> のみ（CLAUDE.md §1）。"
fi

# --- 実データ・DBダンプの持ち込み（合成フィクスチャのみ。§6 機密データ） ---
if [[ "$CMD" =~ (pg_dump|mysqldump) ]] \
|| [[ "$CMD" =~ fixtures/real ]]; then
  deny "BLOCKED: 実データ / DB ダンプの持ち込み。dev は合成フィクスチャのみ（例外なし）。
バグ再現も合成データで作ること（CLAUDE.md §1-5）。"
fi

# --- 権限バイパス（暴走対策の第一則） ---
if [[ "$CMD" =~ bypassPermissions ]] || [[ "$CMD" =~ --dangerously-skip-permissions ]]; then
  deny "BLOCKED: permission バイパスは全ロールで禁止（CLAUDE.md §1-7）。"
fi

hook_log "PreToolUse:Bash" "allow" "ok"
exit 0
