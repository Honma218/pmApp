---
status: superseded（スコープ変更・2026-07-11）
---

> **2026-07-11 追記：本 ADR はスコープ変更（業務アプリ再実装 → スライス進捗集計アプリのみの開発）
> により対象が消滅した。** vendor 済みだった `reference-mock/` は2026-07-11に完全削除済み
> （誤って `feature/slice-00-skeleton` にマージされた分も含む）。詳細・改訂判断は
> `docs/memory-bank/pending-scope-pivot-claude-md-and-adr.md` を参照。以下は当時の記録。

# 参照モックを `reference-mock/` として vendor し、`acceptance/` は `BASE_URL` で対象を切り替える

ADR-0001 は「参照モック（answer key）に先にスイートを流してテスト自体を検証する」ことを前提にしているが、参照モックは別リポにあり、runner は `app_dir` を repo root の内側に閉じ込める（外は refuse）ため、この工程は物理的に実行不能だった。解決として、参照モックを git subtree で `reference-mock/` に vendor し（`acceptance/` と同様 read-only）、`acceptance/` のテストは接続先を `ACCEPTANCE_BASE_URL` から受け取る。

同じスイートが、参照モックに対しては**緑**、実装前の `backend/` に対しては**赤**になる——この反転が「翻訳が正しい」ことの機械的な証明になる。Java/Spring 移行時もポートを変えるだけで同一スイートが流れるため、「受け入れテストは言語非依存の不変資産」という主張がここで初めて機械的に真になる。

## 考慮した代替案

- **各自ローカルに別 clone し、`TEAMDEV_REPO_ROOT` を切り替える**：clone がメンバーごとにドリフトし、CI で回せず、runner の閉じ込め（安全策）に穴を開ける必要がある。
- **参照モックを Docker 化して compose で起動**：分離としては最もきれいだが、初級者の環境に Docker 前提を足す。ハーネス段階導入の Step 3 候補として保留。

## 帰結

- `reference-mock/` は `acceptance/` と同じく protect-paths でブロックする。**answer key を書き換えて緑にする**経路を塞ぐため。
- vendor 前に**シードの棚卸し**が要る（Step 0）。既存モックのフィクスチャが実データ由来なら、vendor した瞬間に憲法 §1-5「dev は合成フィクスチャのみ」違反が repo に入る。
- CI に「`spec/*` PR では参照モックに対してスイートが緑」ジョブを足す。翻訳ミス（仕様表にない挙動を要求するテスト）が main に入るのを止める。
- subtree の pull は上流の明示操作。answer key が勝手にドリフトしない。
