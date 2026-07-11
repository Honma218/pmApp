# Phase 1 タスク分解（着手順）

目的: **認証 → テキスト報告入力 → AI要約・確認 → 確定・格納** を縦に1本通し、
動くものを最短で作る。音声・通知・突合・Excel・グループ別設定は扱わない。

## スコープ

**含む**
- Google OAuth 2.0 ログイン（GWSアカウント）、ロール（staff / manager）
- 報告入力（自由文のみ）＋下書き自動保存
- 前回入力・前回AI要約の参照表示
- AI要約の抽象化層（1プロバイダ実装）＋ 構造化JSON出力
- AI要約の確認・編集画面 → 確定 → REPORTS 格納
- 権限境界の強制（スタッフは自分のみ）

**含まない（後フェーズ）**
- 音声入力 / STT、通知（Slack・メール）、突合・マスター元データ
- スキルシート(Excel)生成、設問テンプレート、グループ別設定、ウェルビーイング設問

## Phase 1 のデータモデル（最小）

```
users(id, google_sub, email, name, role, created_at)
reports(id, user_id, report_date, raw_text, ai_summary_json, status, created_at)
```
- status: draft / confirmed
- ai_summary_json: { incidents[], achievements[], issues[], skills[] }（Phase 1は表示・保存のみ）

## 着手順

各ステップは「完了条件(DoD)」を満たしてからコミットして次へ進む。

1. **足場づくり**
   - モノレポ作成、`CLAUDE.md` と `docs/spec.md` を配置
   - `.env.example` を用意（後述の環境変数）、`.gitignore` に `.env` 追加
   - DoD: frontend / backend がそれぞれ空のページ／ヘルスチェックで起動する

2. **バックエンド基盤 + DB**
   - FastAPI 雛形、PostgreSQL 接続、マイグレーションで users / reports 作成
   - DoD: `GET /health` が 200、マイグレーションが通る

3. **認証（Google OAuth）+ 権限**
   - OAuthログイン、セッション/トークン発行、users へのupsert、role 付与
   - 認可ミドルウェア（リクエストユーザー＝対象データの所有者かを検証）
   - 許可ドメイン/ホワイトリストの仕組み
   - DoD: ログインでき、他人の report_id へのアクセスが 403 になる

4. **フロント基盤**
   - Next.js 雛形、ログイン導線、共通レイアウト（モバイルファースト）
   - 認証状態に応じた画面ガード
   - DoD: 未ログインは入力画面に入れない、ログイン後に入力画面が表示

5. **報告入力（自由文）**
   - 本文テキストエリア、下書き自動保存（PATCH）、前回本文・前回要約の参照表示
   - DoD: 入力が draft として保存され、再訪時に下書きと前回参照が出る

6. **AI要約の抽象化層**
   - `Summarizer` インターフェース＋1プロバイダ実装（抽象化層の背後で呼ぶ）
   - 出力を JSONスキーマ（incidents/achievements/issues/skills）に固定
   - 「マスターに無い数値を創作しない」制約をプロンプトに明記
   - DoD: テキストを渡すとスキーマ準拠のJSONが返る（プロバイダ差し替え可能な形）

7. **要約確認・編集 → 確定**
   - 「要約する」で抽象化層を呼び、結果を編集可能なフォームで表示
   - 要確認フラグ（不足/不確実）の表示、全項目編集可
   - 「確定」で status=confirmed として REPORTS に格納
   - DoD: 編集した内容で確定でき、確定後は不変として保存される

8. **自分の報告閲覧**
   - 自分の過去報告一覧と詳細（確認のみ）
   - DoD: 自分の確定済み報告だけが一覧・閲覧できる

9. **最低限のテスト**
   - 権限境界（他人のデータに触れない）
   - 要約抽象化層のスキーマ準拠
   - DoD: 上記テストが通る

## レビューを厚くする箇所（丸投げしない）

- ステップ3の認可ミドルウェア（権限境界の強制）
- ステップ6の抽象化層（具体プロバイダへの直接依存が漏れていないか）
- ステップ6/7の出力スキーマ固定と「数値を創作しない」制約

## 環境変数（.env.example）

```
DATABASE_URL=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
OAUTH_REDIRECT_URI=
ALLOWED_EMAIL_DOMAIN=
SESSION_SECRET=
AI_PROVIDER=            # claude | gemini | vertex
AI_API_KEY=
```

## 次フェーズへの布石（Phase 1では作らないが意識しておく）

- reports は確定後不変にしておく（後の突合・再生成の前提）
- ai_summary_json のスキーマは、後で PROJECTS / INCIDENTS / SKILLS へ正規化しやすい形にする
- Summarizer 抽象化は、後で Vertex 等へ差し替えても呼び出し側を変えない設計にする
