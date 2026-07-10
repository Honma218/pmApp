# メモリバンク（CLAUDE.md 昇格候補の隔離置き場）

`/flywheel` が作った「憲法（`CLAUDE.md`）に書きたいルール」の草案をここに `pending-<slug>.md` として置く。
**`CLAUDE.md` へ直接書き込むことはエージェント・hook の両方で禁止されている**（`.claude/hooks/protect-paths.sh`）。

## 運用

1. `/flywheel` が `pending-<slug>.md` を起票する（Harness-Keeper＝AIアーキ）。
2. **PM が承認**したものだけを `CLAUDE.md` 本体へ統合する（中身の正本は PM）。
3. 統合したら `pending-<slug>.md` を削除する。却下したら理由を1行残して削除する。

## 起票の基準（2ストライクルール）

- 同じ修正指示を **2回**したら起票する。1回では起票しない（肥大化防止）。
- **書いてあるのに破られた**ものは `CLAUDE.md` ではなく **hook / permissions / CI への昇格**を提案する。
  強制力の階段: 宣言 → 実行時強制 → 事後検証。飛び級しない。
- 1行足すなら1行削れないか見る。基準は「**この行を消したら Claude はミスをするか？**」——No なら消す。
