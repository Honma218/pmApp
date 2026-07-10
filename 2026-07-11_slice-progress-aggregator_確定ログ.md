---
title: スライス進捗集計アプリ — 確定ログ（grill セッション成果）
date: 2026-07-11
tags: [m-team, ai駆動開発, タスク管理, 集計, projection, 確定ログ]
status: 確定（未決#1〜#5 解決済み・PM承認待ち8件）
入力: 2026-07-10_slice-progress-aggregator_作業ログ.md / M-team開発計画書_v2.md（v2.3）
前セッション: grill-me（2026-07-11）
---

# スライス進捗集計アプリ — 確定ログ

2026-07-10 の検討ログに残っていた未決 #1〜#5 を grill セッションで潰し、
その過程で派生した論点（pickup×再作成・issue紐付け・v0出力・作業者間突合・調整機能）まで着地させた確定版。

**大原則（作業ログ §1 から不変）**：集計器は Git への投影（projection / read model）。**読むだけ。**
唯一の書き込み経路は `/rescue`（救援有無）と、集計器自身が生成する派生物のみ。

---

## 1. 確定事項（#A〜#K）

### #A スライスの同一性
- 主キー = `slice_id`（指示書 frontmatter・**不変・再利用禁止・単調増加**）。
- ファイルパスは human-readable な別物。**集計器はパスを主キーにしない**。
- 分割（大きすぎと判明）= **親を破棄（`abandoned:split`）＋ 子を新規2件で起票**。番号は再利用しない。
- `spec/*` PR は複数指示書を含んでよい（分母は追加された `slice_id` の数）。
- 根拠：パス主キーは `git mv` で履歴が切れ移動平均が壊れる／番号再利用は fold の順序を破壊／分割を静かに数え直すと肥大の証拠が消える。

### #B 救援の記録（`/rescue`）
- リーダーが PR/issue コメントに `/rescue <理由>`（または `/rescue --slice <N> <理由>`）。
- **人が書くのは日本語1文だけ**。JSON 1行は GitHub Actions が生成し `docs/metrics/events/slice-NNNN.jsonl` に追記。
- `event_id = "gh-comment-" + comment.id`（**決定論的・冪等**。ULIDは再実行で二重化するため不採用）。
- `at` はコメントの `created_at`（実行時刻ではない）。打ち消しは `/unrescue`（`rescue_revoked` を追記、行は消さない）。
- slice_id 解決：①`--slice` 明示 ②PRヘッドブランチ `feature/slice-NNNN-*` ③issue本文の指示書リンク。**解決不能なら黙って記録せず返信で打ち直しを促す**（誤記録＞記録漏れの非対称性）。
- セキュリティ：`env` 経由でコメント本文を渡す（`${{ }}` 直挿し禁止＝script injection 対策）／投稿者を上流3名に allowlist（`vars.UPSTREAM_MEMBERS`）／`pull_request_target` は使わない。
- 応答：👀（受理）→ ✅（記録）／❌（失敗）でリーダーにその場で可視化。

### #C 書き込み権限 → ADR-0012
- metrics events への **bot 直コミット（main）を許可**。ADR-0012 として明文化。
- 正当化：allowlist＋schema検証＋パス限定（`docs/metrics/events/**`）＋append-only。ADR-0001 が守るのは不可逆操作で、追記は訂正イベントで打ち消せる。
- 副次効果：append-only 直コミットにより履歴が単調 → `(commit, as_of)` 単位の再現テスト（#後述）が成立する。ADR-0012 の理由付けにこれを含める。

### #D 破棄の扱い
- `abandoned` イベントは `reason` 必須：`split`（分解の欠陥）/ `descoped`（要らない）/ `failed`（緑に至らず断念＝ハーネスの欠陥）。
- 分類は **PR/issue クローズ時のラベル**（`abandoned:split` 等）。**未ラベル = `failed`**（沈黙は測る側に不利に倒す）。
- 移動平均の順序キー = `settled_at`（completed or abandoned の時刻。`created_at` ではない）。

### #E 分母とスプリント / NO-GO
- **集計器はスプリント概念を持たない**（境界が Git に無い＝持たせると投影原則が壊れる）。バーンダウンは MVP 全体に1本。
- NO-GO を2種に分割し `gates.md` に**必須記録**（ADR-0007 は記録を既に必須化済み → フィールド追加のみ）：
  - `NO-GO:rework`（修正で足りる・同一 slice_id 継続）→ **差し戻し率**の分子。
  - `NO-GO:redecompose`（分解し直し・新 slice_id 起票）→ **肥大率**側（分解の失敗）。
- 無指定は許さず、NO-GO 時のみ PM に区別を必須入力させる（月数回・既存の必須作業に1フィールド）。

### #F 肥大率
- 分子の代理指標 = **PR diff 行数 ＋ 起票→completed 所要日数**（＋事実としての `abandoned:split`）。
- **wip カウンタ（再作成回数の正確な計数）は不採用**。`/pickup`・`/submit` のスキル改修不要。集計器は Git を読むだけ。
- §1「セッション再作成2回超」閾値は**廃止**（肥大率は診断用テスターであり、精度よりも取得コストの低さが正義）。

### #G' pickup と再作成 / issue 任意化
- `/pickup` は**イベントを一切吐かない**（下流は GitHub 書き込み禁止＝ADR-0004 を無傷に保つ）。
- 再作成2回超トリガーは GitHub 計測をやめ、**`/pickup` の SKILL.md 冒頭の注意喚起文＋リーダー判断**で運用。発火の結果は `abandoned:split` として自然に記録される。
- §1 計測項目「再作成回数」は**廃止**。
- **`issue` は frontmatter の任意項目**（`slice_id` があればよい）。issue 無しスライスの救援は PR コメント（ブランチ名解決）または `--slice` 明示指定でカバー。

### #H issue ↔ slice_id 対応
- `docs/metrics/index/slice-map.json` は集計器が events から **fold して生成する派生物**（正本ではない）。
- 対応は**起票時に確定**：`spec/* merged` の webhook で集計器が指示書 frontmatter の `slice_id`（＋あれば `issue`）を読み、`issued` イベントに載せる。
- これで `/rescue`（issueコメント）の slice_id 解決が、救援到着前に必ず成立する。

### #I v0 の出力
- **① PR コメント1行**（速報・自分のPRにのみ）＋ **② 週次 Markdown `docs/status/weekly/YYYY-Www.md`**（Harness-Keeper が読む）。
- **GitHub Pages は v0 では作らない → v1 へ延期**。Pages が要るのは「Git の外の読み手（例：経営層）」が現れたときのみ。
- 副次効果：Pages publish ステップ削除で workflow が単純化、bot の書き込み先が `docs/metrics/**`・`docs/status/**` に絞られ攻撃面が縮小。

### #J 作業者間の突合回避
- events はスライス別ファイル＋append-only → **別スライスは別ファイル、突合しない**。
- 集約（slice-map / daily / weekly）は **日次 cron 1本だけが書く**（submit は集約を触らない）。書き手1つ＝突合が原理的に起きない。
- 保険：全書き込みジョブに `concurrency: { group: metrics-write, cancel-in-progress: false }`。
- トレードオフ：日中は集約が最大24h古い。集約を見るのは週次レビューのみなので許容。日中も最新が要る読み手が出たら v1 で submit契機更新＋直列化に切替。

### #K 調整機能（advisory のみ）
- 大原則：集計器は**提案・警告はするが、割当・指示（authority）は持たない**。誰がどれをやるかは PM/リーダーの順序決定が正本。
- **(A) スライス重複警告 → v0 で実装**。`/pickup` 時に open な `feature/*` ブランチのファイル範囲（指示書必須項目3）と交差検知して警告。read-only・下流の権限に触れない。**範囲交差＝独立縦切りの失敗＝分解の欠陥シグナル**として週次にも計上。強制は §4 ガード＋git-guardrails が担う（警告は早期注意）。
- **(B) 次スライス提案＋`depends_on` 新設 → v1 へ延期**。依存解決は GitHub Projects が得意な領域で差別化点（KPI4指標）ではない。v0 は slice 数が少なく順序は PM の issue 並び順で足りる。

---

## 2. 設計の背骨（全確定が依存する3点）

1. **events は append-only の NDJSON、状態は `fold(events)`。** 冪等性・再現テスト・突合回避・救援訂正の全てをこれが支える。
2. **人間の手が入るイベントは `/rescue` の1種類だけ。** 他は Git から導出（diff・ラベル・gates.md）。
3. **2指標が2原因に1:1対応。** 完走率(＋failed)=ハーネスの欠陥 / 肥大率(＋split)・重複警告=分解の欠陥。§1「2分類してから対策」が指標を見た瞬間に済む。

---

## 3. KPI 定義（確定後）

| 指標 | 分子 | 分母 | 変更点 |
|---|---|---|---|
| **AFK完走率**（北極星） | 救援0で完了 | 完了 ∪ `abandoned:failed` | 分母に failed を追加（生存者バイアス防止）。直近5の移動平均・順序キー`settled_at` |
| 差し戻し率 | 統合役NG ＋ `NO-GO:rework` | 完了 | NO-GO を rework のみに限定 |
| スライス肥大率 | (diff行数＋所要日数の代理) ∪ `abandoned:split` ∪ `NO-GO:redecompose` | 完了 ∪ `abandoned:split` | 代理指標化・分割を分子/分母に算入・「2回超」廃止 |
| 枠効率（$/task） | 破棄分を含む全消費 | 完了 | 分子に破棄分を算入（失敗の安さを計上しない）。取得元 未定→null 許容 |
| 指示書進捗 | 完了 | `spec/*` マージ済み − `abandoned:descoped` | 据え置き（バーンダウン率として正しく機能） |
| （観察）週次消化件数 | 直近の completed 件数 | — | KPI表外・Flywheel 観察項目 |

---

## 4. PM 承認待ちリスト（AIアーキ単独では変えられない）

1. **完走率**の分母に `abandoned:failed` を含める
2. **肥大率**の再定義（分子に split／diff＋日数代理／「2回超」廃止）
3. **枠効率**の分子＝破棄分を含む全消費
4. **差し戻し率**の分子＝`統合役NG ＋ NO-GO:rework` のみ
5. **§1 計測項目「再作成回数」の廃止**
6. `gates.md` に **NO-GO:rework/redecompose** 区別を必須化（**ADR-0007 改訂**）
7. **ADR-0012 新設**（metrics events への bot 直コミット）
8. `指示書進捗`据え置き＋`週次消化件数`を Flywheel 観察項目に追加

---

## 5. ADR ドラフト

### ADR-0012（新設）— metrics events への bot 直コミット

- **Status**: Proposed（PM承認待ち）
- **Context**: `/rescue` の救援記録を PR 経由でマージさせると、救援1件ごとに承認操作が発生し「面倒だから打たない」を誘発（過少申告＝北極星汚染）。層境ゲートという本来の HITL 判断も雑音に埋もれる。
- **Decision**: GitHub Actions（bot）が `docs/metrics/events/**` へ **append-only で main に直コミット**することを許可する。
- **Constraints**:
  - 投稿者を上流3名に allowlist（`vars.UPSTREAM_MEMBERS`）。
  - JSON Schema で全 events 行を CI 検証。
  - 書き込みパスは `docs/metrics/events/**`・`docs/metrics/index/**`・`docs/status/**` に限定。
  - コメント本文は `env` 経由で渡す（script injection 対策）。
- **Consequences**: ADR-0004（ブランチ名による書込権判定）に bot 例外が1本できる。ただし append-only 直コミットにより履歴が単調化し、`(commit, as_of)` 単位の再現テスト（集計器の非決定性検出）が成立するという副次的利益がある。
- **関連**: ADR-0001（不可逆操作の関所。追記は不可逆でない＝関所の対象外）。

### ADR-0007 改訂 — 層境ゲート記録への NO-GO 種別追加

- **Change**: `gates.md` の GO/NO-GO 記録に、NO-GO 時は `rework`（修正で足りる・同一 slice_id）/ `redecompose`（分解し直し・新 slice_id）の**区別を必須**とする。
- **Rationale**: 両者は原因が異なる（実装の雑さ vs 分解の雑さ）。同じ「差し戻し率」に混ぜると §1 の2分類原則（スライス設計の欠陥 or ハーネスの欠陥）に反し、原因切り分けが不能になる。
- **Cost**: NO-GO は月数回。PM は既に `gates.md` 記録が必須（ADR-0007）＝既存作業に1フィールド追加のみ。新規手入力イベントは発生しない。

---

## 6. 実装の初手（§8-2 に対応）

1. **JSON Schema を先に切る**（1イベント=1行の NDJSON）。§8-2「行フォーマットのスキーマ化」の正体。CI で全 `.jsonl` を検証し、欠損を集計時ではなく PR 時に弾く。
2. `fold` を純関数 `(commit, as_of) → status` として実装し、**過去7日スナップショット再現テスト**（不一致かつ入力ハッシュ一致 → CI fail）を日次に組む。drift ログは廃止（正常3種と異常1種を混ぜて誰も読まないため）。速報層の健全性は `reconciliation_delta_rate`（週次の数字1つ）のみ。
   - コスト注記：7日再計算は Actions/gh API を圧迫しうる。slice が増えたら「直近1日再計算」へ縮める（検出力↓・コスト1/7）。v0 は7日。
3. `/rescue` の Actions を script-injection 対策込みで実装。👀→✅/❌ の応答を焼く。
4. `/pickup` に (A) 重複警告（open ブランチのファイル範囲交差検知・advisory）と、再作成2回超の注意喚起文を SKILL.md 冒頭に追加。
5. slice-01 のドッグフーディングで v0 を回す。枠消費は §6 候補1（`~/.claude/projects/**/*.jsonl`）を AIアーキが実機検証、それまで `null`。

---

## 7. events スキーマ（ドラフト）

```jsonl
{"event_id":"gh-comment-2847193","type":"issued","slice_id":7,"at":"...","actor":"pm","spec_pr":141,"issue":42}
{"event_id":"...","type":"submitted","slice_id":7,"at":"...","pr":152,"diff_add":120,"diff_del":8,"usage_usd":null}
{"event_id":"gh-comment-2847193","type":"rescued","slice_id":7,"at":"...","actor":"leader-taro","note":"環境変数の置き場所が分からず","source":"https://github.com/.../pull/152#issuecomment-2847193"}
{"event_id":"...","type":"rejected","slice_id":7,"at":"...","by":"integrator","reason":"範囲外ファイル"}
{"event_id":"...","type":"gate","slice_id":7,"at":"...","verdict":"NO-GO","kind":"rework","by":"pm"}
{"event_id":"...","type":"abandoned","slice_id":7,"at":"...","reason":"split"}
{"event_id":"...","type":"completed","slice_id":7,"at":"...","pr":152}
```

- ファイル分割：`docs/metrics/events/slice-NNNN.jsonl`（スライス別・append-only）。
- 派生物：`docs/metrics/index/slice-map.json`（対応表）・`docs/status/daily/YYYY-MM-DD.json`・`docs/status/weekly/YYYY-Www.md`（すべて集計器生成・cron 1本が書く）。

---

## 参照
- `2026-07-10_slice-progress-aggregator_作業ログ.md`（検討ログ・処理フロー Mermaid 4図）
- `M-team開発計画書_v2.md`（v2.3）§1 成功基準 / §2 所有マップ / §4 開発フロー・必須6項目 / §9 スラッシュコマンド
- ADR-0001・0004・0006・0007（改訂）・0011・0012（新設）
