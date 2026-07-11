---
status: proposed（PM承認待ち。GO 後に accepted へ）
関連: ADR-0001（不可逆操作の関所）/ ADR-0004（ブランチ層が書込権を決める）/ ADR-0007（層境ゲート）
---

# metrics events への bot 直コミットを許可する（append-only・パス限定）

`/rescue`（救援記録）を通常の PR 経由でマージさせると、救援1件ごとに承認操作が発生する。救援は月に何度も起きるため、「面倒だから打たない」を誘発する——これは**過少申告となり北極星（AFK完走率）を汚染する**。しかも承認の山に埋もれて、本来 HITL で見るべき層境ゲートの判断まで雑音化する。

よって、**GitHub Actions（bot）が `docs/metrics/events/**` へ append-only で main に直コミットすることを許可する**。これは ADR-0004（ブランチ名で書込権を判定する）に bot 例外を1本開けることを意味するため、無条件では認めず、下の制約とセットで正当化する。

## 何を許可し、何を許可しないか

| | 許可する | 許可しない |
|---|---|---|
| 書き込み主体 | GitHub Actions の bot（`/rescue` ワークフロー） | 人間・下流エージェントの直コミット |
| パス | `docs/metrics/events/**`・`docs/metrics/index/**`・`docs/status/**` | それ以外（`backend/`・`acceptance/` 等は従来どおり） |
| 操作 | 追記（append-only） | 既存行の書き換え・削除 |
| 起票者 | `vars.UPSTREAM_MEMBERS`（上流3名）の allowlist | allowlist 外のコメント |

## なぜ関所（ADR-0001）を壊さないか

ADR-0001 の関所が守るのは**不可逆操作**（migration・認可・`acceptance/` 変更）である。metrics events は **append-only なので不可逆でない**——誤記録は打ち消しイベント（`rescue_revoked`）で訂正でき、行は消さない。したがって「不可逆操作は統合役の1点に集約する」という原則に抵触しない。関所の対象は不可逆操作であって「main への全書き込み」ではない、という区別がこの ADR の要諦。

## 機械的強制（宣言だけでは守られない）

| 層 | 実体 |
|---|---|
| 宣言 | 本 ADR・`CLAUDE.md` の禁止事項（bot 例外を明記） |
| 実行時強制 | ワークフローの `permissions` を `contents:write` の最小に絞る／`env` 経由でコメント本文を渡す（`${{ }}` 直挿し禁止＝script injection 対策）／`pull_request_target` を使わない |
| 事後検証 | JSON Schema で全 events 行を CI 検証（`validate-events.yml`）／書き込みパスを CI で events/index/status に限定 |

`event_id = "gh-comment-" + comment.id`（**決定論的・冪等**。同一 webhook 再実行が二重行を生まない）。`at` はコメントの `created_at`（実行時刻ではない）。

## 帰結

- **副次的利益**：append-only 直コミットにより履歴が単調化し、`(commit, as_of)` 単位の再現テスト（集計器の非決定性検出）が成立する。バグ検出の土台がタダで手に入る。
- ADR-0004 に「bot・パス限定・append-only」の例外が1本増える。人間・下流の書込権判定は従来どおり無変更。
- `/rescue` の応答は 👀（受理）→ ✅（記録）／❌（失敗）でリーダーにその場で可視化する。
- **却下時の代替**：bot 直コミットを認めない場合、救援は PR 経由となり承認1回が毎回乗る。過少申告リスクを許容するか、別の低摩擦経路を用意する必要がある。
