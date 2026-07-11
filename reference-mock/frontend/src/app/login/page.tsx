// 公開ページ。Google ログインへの導線のみを提供する。
// リンク先 /auth/login は rewrites でバックエンドにプロキシされ、Google 同意画面へ遷移する。
export default function LoginPage() {
  return (
    <main className="container center">
      <h1>ログイン</h1>
      <p className="muted">
        業務報告システムを利用するにはログインしてください。
      </p>
      <p>
        <a className="button" href="/auth/login">
          Google でログイン
        </a>
      </p>
    </main>
  );
}
