# slice-aggregator（スライス進捗集計アプリ v0）

M-team のプロセスKPI（AFK完走率ほか）を **Git への投影（projection / read model）** として集計する
Harness-Keeper の道具。**読むだけ。** 唯一の書き込みは `/rescue`（bot 経由）と自身が生成する派生物のみ。

- 設計：`../../2026-07-11_slice-progress-aggregator_確定ログ.md`
- 着手計画：`../../2026-07-11_slice-progress-aggregator_実装ロードマップ.md`
- 承認ゲート：`../../2026-07-11_P0-承認パッケージ.md`（**P0 は8件すべてGO・2026-07-11 PM承認済み**）

## 現在の実装状況（P1：基盤スキーマ ／ P2：fold）

| 成果物 | 場所 | 役割 |
|---|---|---|
| イベントスキーマ | `schemas/slice-event.schema.json` | 1イベント=1行の NDJSON を検証（draft 2020-12） |
| バリデータ | `scripts/validate_events.py` | スキーマ＋event_id冪等＋append-only（時刻/slice_id整合） |
| CI（schema） | `../../.github/workflows/validate-events.yml` | PR 時に events を検証（事後検証層） |
| ゲートログ | `../../docs/metrics/gates.md` | NO-GO種別つき（ADR-0007 改訂の実体・本運用中） |
| テストデータ | `testdata/valid`・`testdata/invalid` | 正常=緑・異常=赤の回帰用 |
| `issued`イベント発火 | `scripts/emit_issued_event.py` ＋ `../../.github/workflows/emit-issued-event.yml` | `docs/slices/slice-NN.md` の merge を検知し起票イベントを記録 |
| **fold純関数** | `scripts/fold.py` | events → 状態（`SliceStatus`）＋KPI6指標を再構成する純関数（決定性あり） |
| **単体テスト** | `tests/test_fold.py`・`tests/test_handle_rescue_comment.py` | 状態機械・決定性・KPI算出・`/rescue`解決ロジックを網羅 |
| CI（test） | `../../.github/workflows/test-slice-aggregator.yml` | PR 時に pytest を実行 |
| **`/rescue`・`/unrescue`** | `scripts/handle_rescue_comment.py` ＋ `../../.github/workflows/rescue.yml` | 唯一の人手イベント。issue/PRコメントから救援を記録（確定ログ #B・P3） |
| **`/pickup` 重複警告** | `../../.claude/skills/pickup/SKILL.md` | open ブランチとのファイル範囲重複を advisory 警告（確定ログ #K-(A)・P4） |
| **① 速報** | `scripts/render_pr_status.py` ＋ `../../.github/workflows/pr-status-comment.yml` | スライスPRに現在地1行を投稿・更新（自分のPRにのみ・P5） |
| **② 日次集約** | `scripts/generate_daily_snapshot.py` ＋ `../../.github/workflows/daily-status-cron.yml` | `docs/metrics/index/slice-map.json`・`docs/status/daily/*.json` を生成（書き手はこの1本だけ・確定ログ #J） |
| **③ 週次レポート** | `scripts/generate_weekly_report.py`（同上 workflow） | `docs/status/weekly/YYYY-Www.md`。直近5スライス移動平均・Flywheel観察項目 |
| **`submitted`・`completed` 自動記録** | `scripts/emit_slice_pr_event.py` ＋ `../../.github/workflows/emit-slice-pr-events.yml` | `feature/slice-<N>-*` PRのopen/mergeから機械的に記録（P6準備） |
| **`/gate`・`/reject`・`/abandon`** | `scripts/handle_gate_comment.py` ＋ `../../.github/workflows/gate.yml` | PM限定のコメントコマンド。層境ゲート判定・統合役NG・破棄を記録（P6準備・`/abandon`はslice-01・issue #18） |

これで8イベント型（`issued`/`submitted`/`rescued`/`rescue_revoked`/`rejected`/`gate`/`abandoned`/`completed`）
すべてに記録経路が揃った。未実装（次フェーズ）：**P6 slice-01 のドッグフーディング完走のみ**。
日次での過去7日再計算による非決定性検出（P2の運用面）は、実データが増えてから
`daily-status-cron.yml` に追加する予定（現状は日次1回の単純再計算のみ）。

## `/rescue`（救援の記録）の使い方

リーダーが issue または PR のコメントに次のように書く（**人が書くのは日本語1文だけ**）。

```
/rescue --slice 7 環境変数の置き場所が分からず
```

- `--slice <N>` は省略可。省略時は PR のヘッドブランチ名（`feature/slice-<N>-*`）か、
  issue 本文中の `docs/slices/slice-<N>` 参照から自動解決する。**解決できない場合は記録せず、
  `--slice` を付けて打ち直すよう返信する**（誤記録より記録漏れを許容・確定ログ #B）。
- 打ち消しは `/unrescue --slice <N> <理由>`（`rescue_revoked` を追記。行は消さない）。
- 実行できるのは `UPSTREAM_MEMBERS`（リポジトリ変数。カンマ区切り）に登録されたユーザーのみ。
  **未設定時は現運用者 `Honma218` にフォールバック**する。チーム拡張時は
  `gh variable set UPSTREAM_MEMBERS --body "user1,user2,user3"` で上書きする。
- 応答は 👀（受理リアクション）→ コメント返信で ✅（記録）／❌（失敗理由）。

## `/gate`・`/reject`・`/abandon`（層境ゲート・統合役NG・破棄の記録。PM限定）

```
/gate GO --slice 7
/gate NO-GO --kind rework --slice 7
/gate NO-GO --kind redecompose --slice 7
/reject --slice 7 範囲外のファイルが含まれている
/abandon --reason split --slice 7
/abandon --reason descoped --slice 7
/abandon --reason failed --slice 7
```

- 実行できるのは `GATE_KEEPERS`（リポジトリ変数。カンマ区切り。`/rescue` の `UPSTREAM_MEMBERS` とは別）
  に登録されたユーザーのみ。**未設定時は現運用者 `Honma218` にフォールバック**する
  （CLAUDE.md §7「判定者はPM」を allowlist で強制。`/rescue` はリーダーも実行できるが `/gate`・`/reject`・
  `/abandon` はPM限定）。
- `NO-GO` は `--kind rework`（同一 slice_id 継続）か `--kind redecompose`（分解し直し）を**必須**で
  指定する。省略すると記録せず打ち直しを促す。
- `/abandon` の `--reason` は `split`（分解し直し。通常 `/gate NO-GO --kind redecompose` とセット）／
  `descoped`（要らないと判明）／`failed`（緑に至らず断念）の3値のみ許可。省略・不正値は記録せず
  打ち直しを促す。
- `docs/metrics/gates.md` は人間向けの任意ログとして残るが、**KPI計算が読むのは events。
  食い違えば events が正**。
- slice_id 解決・応答UXは `/rescue` と同じ（`--slice` 明示 > PRブランチ > issue本文、👀→✅/❌）。

## `submitted`・`completed` の自動記録

`feature/slice-<N>-*` ブランチのPRが **open された時点**で `submitted`（diff行数込み）、
**main へ merge された時点**で `completed` を bot が自動記録する。人の操作は不要。

## 三層集約（P5）の出力

- **① 速報**：`feature/slice-<N>-*` ブランチのPRを開く/更新するたびに、そのPRへ現在地1行を
  投稿・更新する（他スライスの状態は見せない）。
- **② 日次**：`daily-status-cron.yml`（毎日06:00 JST・`workflow_dispatch` でも起動可）が
  全 events を再計算し、`docs/metrics/index/slice-map.json`（現在の一覧）と
  `docs/status/daily/YYYY-MM-DD.json`（その日のKPIスナップショット）を生成する。
- **③ 週次**：同じcronが `docs/status/weekly/YYYY-Www.md` を生成・更新する
  （週の途中でも最新化される。ISO週が変わると新しいファイルになる）。
- **書き手は日次cron1本だけ**（`/submit`・`/rescue` は集約に触れない＝突合ゼロ・確定ログ #J）。
  全書き込みジョブは `concurrency: { group: metrics-write, cancel-in-progress: false }` で直列化。
- **GitHub Pages は作らない**（v0はJSON/Markdown出力のみ。確定ログ #I）。

**「スライス肥大率」の閾値は未確定。** `compute_kpis()` は diff行数・所要日数・split/redecompose件数の
生信号のみ返す。「何行・何日から肥大か」は新たな KPI 定義の決定であり PM 承認が要る
（旧 ADR-0008 golden 閾値と同じ「最初ゆるく→実データで較正」方針。P6 ドッグフーディングで数値が集まってから判断）。

## ローカル実行

```bash
pip install "jsonschema>=4.20" "pyyaml>=6.0" pytest

# events の検証（既定 glob: docs/metrics/events/**/*.jsonl）
python tools/slice-aggregator/scripts/validate_events.py

# 状態とKPIを見る
python tools/slice-aggregator/scripts/fold.py tools/slice-aggregator/testdata/valid/slice-0007.jsonl

# 三層集約を手動生成（as_ofは任意のISO8601。実行するとdocs/metrics/index・docs/status配下に書き込む）
python tools/slice-aggregator/scripts/generate_daily_snapshot.py --as-of "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python tools/slice-aggregator/scripts/generate_weekly_report.py --as-of "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 単体テスト
python -m pytest tools/slice-aggregator/tests/ -v
```

`validate_events.py` の終了コード：0=全緑 / 1=検証失敗 / 2=前提エラー（依存欠落・スキーマ不在）。

## イベント型（確定ログ §7）

`issued` `submitted` `rescued` `rescue_revoked` `rejected` `gate` `abandoned` `completed`。
共通必須は `event_id / type / slice_id / at`。型別の必須は schema の `allOf`（if/then）で強制。
`gate` は `verdict=NO-GO` のときのみ `kind`（`rework`/`redecompose`）必須。
