# イベントログ（append-only NDJSON）

スライス進捗集計アプリの一次データ。**1ファイル1スライス**（`slice-NNNN.jsonl`）、**1行1イベント**、**追記専用**。
状態は `fold(events)` で再構成する（正本はこのイベント列。派生物は `../index/`・`../../status/` に生成）。

- **書き手**：GitHub Actions の bot のみ（`/rescue` ほか。ADR-0012・PM承認待ち #7）。人間・下流は直接書かない。
- **スキーマ**：`tools/slice-aggregator/schemas/slice-event.schema.json`。PR 時に `validate-events.yml` で全行検証。
- **訂正**：行は消さない。打ち消しは `rescue_revoked` など追記イベントで行う。
- **event_id**：決定論的・冪等（例 `gh-comment-<id>`）。同一 webhook 再実行で二重化しない。

現状はまだ実イベントなし（P6 の slice-01 ドッグフーディングで最初の実データが載る）。
形式の参考は `tools/slice-aggregator/testdata/valid/slice-0007.jsonl`。
