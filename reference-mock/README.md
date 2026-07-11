# 業務報告・スキルシート生成システム

客先常駐スタッフの業務報告を蓄積し、AIで要約・職務経歴書（スキルシート）を自動生成する Web システム。
要件・設計は [`docs/spec.md`](docs/spec.md)、開発計画は [`docs/phase1-plan.md`](docs/phase1-plan.md) を参照。

現在は **Phase 1**（認証＋テキスト報告＋AI要約・確認画面）の足場づくり段階。

## 構成（モノレポ）

- `backend/` … FastAPI アプリ
- `frontend/` … Next.js（React + TypeScript）アプリ
- `docs/` … 設計資料

## セットアップ

### 前提

- Python 3.11+
- Node.js 18+

### backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows は .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 値は各自で設定（.env はコミットしない）
uvicorn app.main:app --reload
```

起動後、ヘルスチェック:

```bash
curl http://localhost:8000/health   # {"status":"ok"} が返る
```

テスト:

```bash
cd backend && pytest
```

### frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

テスト:

```bash
cd frontend && npm test
```

## 環境変数

`backend/.env.example` をコピーして `backend/.env` を作成し、各値を設定する。
シークレット（OAuth 資格情報・API キー等）はコミットしないこと。
