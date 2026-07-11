# teamdev-test-runner（runner）

アプリ起動・監視の MCP。**このサーバーはアプリを起動するだけで、合否は出さない。**
採点はテストFW（`@playwright/test` 等）が行う。runner の出力を合否と読み違えないこと。

`harness_start` → ready 待ち → テスト実行、の順。

## 配置と配布

repo ルートの `.mcp.json`（project スコープ）から参照する。**clone = 入手**で、
下流は手設定ゼロ。初回だけ承認プロンプトが出る（正しい挙動）。

```
repo-root/
├── .mcp.json                       "uv run --project tools/teamdev-test-runner-mcp teamdev-test-runner"
├── tools/teamdev-test-runner-mcp/  ← ここ
├── backend/test-harness.runtime.json
└── frontend/test-harness.runtime.json
```

`.mcp.json` の `${workspaceFolder}` は **VS Code 記法で展開されない**。stdio サーバーは repo ルートを
cwd として起動されるので、`TEAMDEV_REPO_ROOT` 未設定時は **cwd から上へマーカー（`.mcp.json` / `.git` /
`CLAUDE.md`）を探して自動検出**する。`app_dir` が repo root の外を指したら **refuse** する。

## ツール（1ツール＝1操作）

| ツール | いつ使うか |
|---|---|
| `harness_start(app_dir)` | テストを実行する前に必ず。readyCheck が通るまで待つ |
| `harness_status(app_dir)` | 「落ちている」のか「まだ ready でない」のかを切り分ける |
| `harness_logs(app_dir, lines?, stream?)` | テストが赤いとき、**コードを直す前に**読む |
| `harness_stop(app_dir)` | 緑になったら停止する。ポートを掴んだまま次に進まない |

**1 app_dir = 1 プロセス。** 既に起動中の app_dir に `harness_start` を投げたら二重起動せず error を返す
（黙って二重起動すると、ポート衝突が「原因不明の赤」になる）。

## アプリ側の設定

`<app_dir>/test-harness.runtime.json` を置く。雛形は `examples/` にある。スキーマは `schema/runtime.schema.json`。
未知のキーは **黙って無視せず弾く**（`extra="forbid"`。`bootCommnad` のようなタイポを赤にする）。

`readyCheck` は4種:

| type | 判定 | 典型 |
|---|---|---|
| `http_200` | `path` に GET して 200 | Express `/health`・Next.js `/` |
| `http_status` | `path` の status が `expectStatus` | 認証必須の入口（401 を ready とみなす等） |
| `tcp_listen` | `port` が listen | HTTP を話さないサーバー |
| `text_in_response` | `path` の body に `contains` | 起動画面の文言で判定 |

## 開発

```bash
uv sync
uv run pytest              # 23 tests
uv run teamdev-test-runner # stdio。手で叩くなら MCP Inspector 推奨
npx @modelcontextprotocol/inspector uv run --project tools/teamdev-test-runner-mcp teamdev-test-runner
```

## 実装上の注意（踏むと痛い）

- **stdout に何も書かない。** stdio プロトコルが壊れる。ログは stderr へ。
- **ready 判定は `trust_env=False`。** `HTTP_PROXY` / `ALL_PROXY` のある開発機で、localhost への
  readyCheck がプロキシ経由になって必ず失敗する。
- **`shell=True` の孫プロセスまで殺す。** 取り残すとポートが解放されず、次の `harness_start` が
  「原因不明の赤」になる。Windows は `taskkill /F /T /PID`、POSIX は `killpg`。
- **プロセスが即死したら `bootTimeoutMs` を待たずに諦める。** 待つのは Pro 枠の無駄。
- クライアントが落ちても子プロセスを取り残さない（`stop_all()` を finally で呼ぶ）。
- バージョンは pin する（`uv.lock` をコミット）。全員同一版でないと接続がフラップする。
