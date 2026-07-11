import { ReportEditor } from "@/components/ReportEditor";

// 報告入力画面（保護ルート）。当日下書きの自動保存と前回参照を提供する。
// 要約生成（ステップ6）・確認/確定（ステップ7）は後続で追加する。
export default function ReportPage() {
  return (
    <main className="container">
      <h1>業務報告の入力</h1>
      <ReportEditor />
    </main>
  );
}
