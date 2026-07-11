---
name: flywheel
description: 層境ゲートの却下理由・Audit の指摘・ハーネスの摩擦を、リポジトリのチーム共有知（ADR / CONTEXT.md / hooks / CLAUDE.md 昇格候補）への書き戻し草案にする。Harness-Keeper（AIアーキ）が使う上流コマンド。Use when the user runs /flywheel after a slice is rejected or friction is observed.
disable-model-invocation: true
---

# /flywheel

Feedback Flywheel: 個別の対話で得た学びをチーム共有知へ書き戻し、次の対話を良くする。
**あなたは草案を作るだけ。** 確定（特に CLAUDE.md への昇格）は人間が行う。

## 入力

- 却下理由（層境ゲート NO-GO / 統合役の差し戻し）
- Audit の指摘（PR コメント）
- ハーネスの摩擦（同じ修正指示の繰り返し・hook のブロック頻度・セッション再作成回数）

## 手順

1. **原因を2分類する。** これを飛ばさない。

   | 分類 | 意味 | 行き先 |
   |---|---|---|
   | **スライス設計の欠陥** | 大きすぎ・受入基準過多・依存の見落とし | PM へ（issue 分解の見直し） |
   | **ハーネスの欠陥** | 枠・skills・hooks・エージェント定義の不足 | AIアーキへ（`.claude/` の修正） |

2. **強制力の階段を1段だけ上げる。** 飛び級しない。

   ```
   何も無い  →  宣言（CLAUDE.md / 指示書 / skills 本文）
              →  実行時強制（hooks exit 2 / permissions deny / tools 制限）
              →  事後検証（CI の path ガード / pre-commit / ブランチ保護）
   ```

   - **2ストライクルール**: 同じ修正指示を **2回**したら宣言に書く。1回では書かない。
   - **書いてあるのに破られた** → hook / permissions / CI へ昇格させる。
     （書いてあるのに従わない場合、ファイルが長すぎてルールが埋もれているのが典型原因。まず剪定を疑う。）

3. **書き戻し先ごとに草案を出す**

   | 対象 | 確定権限 |
   |---|---|
   | `docs/adr/NNNN-*.md`（新規決定） | Harness-Keeper 単独で確定してよい |
   | `CONTEXT.md`（用語のブレ） | Harness-Keeper 単独で確定してよい |
   | `acceptance/` のテスト観察（仕様の穴） | PM へ起票 |
   | `.claude/hooks/` / `settings.json` の deny | AIアーキ（＝Harness-Keeper）が確定 |
   | **`CLAUDE.md`（憲法）** | **PM 承認が必須。** 草案は `docs/memory-bank/` に隔離する |

4. **CLAUDE.md 昇格候補は本体に直接書かない。**
   `docs/memory-bank/pending-<slug>.md` に隔離し、PM 承認後に統合する。
   自律エージェントに憲法を書き換えさせない。

5. **剪定もセットで提案する。**
   1行足すなら1行削れないか見る。基準は「**この行を消したら Claude はミスをするか？**」——No なら消す。
   CLAUDE.md は目標 ~150行・上限 200行。**古いルールは欠落より有害。**

## 出力

```
## 観察: <何が起きたか（1〜2文）>
## 分類: スライス設計の欠陥 / ハーネスの欠陥
## 発生回数: <n>回目（2回目以降なら宣言化、宣言済みで再発なら昇格）

## 提案（強制力の階段を1段）
- 現在: <宣言 / なし>
- 提案: <hook / permissions / CI / 宣言> — <具体的な差分>

## 書き戻し草案
### docs/adr/ ... （あれば）
### CONTEXT.md ... （あれば）
### docs/memory-bank/pending-<slug>.md（CLAUDE.md 昇格候補・PM 承認待ち）

## 剪定提案
- CLAUDE.md の <行> は <理由> で削れる / 削れない
```
