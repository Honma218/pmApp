import { redirect } from "next/navigation";

// ルートは入力画面へ送る。未ログインの場合は (protected) のガードが /login へ回す。
export default function Home() {
  redirect("/report");
}
