// ブラウザから業務 API を呼ぶ薄いクライアント。
// next.config.mjs の rewrites により /api/* は同一オリジン経由で FastAPI に届き、
// httpOnly セッション Cookie がファーストパーティで同送される（credentials: same-origin）。

// バックエンドの ReportOut に対応。
export type Report = {
  id: string;
  user_id: string;
  report_date: string; // YYYY-MM-DD
  raw_text: string;
  ai_summary_json: AiSummary | null;
  status: "draft" | "confirmed";
  created_at: string;
};

// Phase 1 の要約スキーマ（表示のみ）。
export type AiSummary = {
  incidents?: string[];
  achievements?: string[];
  issues?: string[];
  skills?: string[];
};

// 一覧用の軽量表現（バックエンドの ReportListItem に対応）。
export type ReportListItem = {
  id: string;
  report_date: string; // YYYY-MM-DD
  status: "draft" | "confirmed";
  created_at: string;
};

async function jsonOrThrow(res: Response): Promise<unknown> {
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

/** 指定日の自分の下書きを取得（無ければ作成）する。 */
export async function createOrGetDraft(reportDate: string): Promise<Report> {
  const res = await fetch("/api/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_date: reportDate }),
    cache: "no-store",
  });
  return (await jsonOrThrow(res)) as Report;
}

/** 下書き本文を保存する（自動保存）。 */
export async function patchDraft(
  reportId: string,
  rawText: string,
): Promise<Report> {
  const res = await fetch(`/api/reports/${reportId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText }),
    cache: "no-store",
  });
  return (await jsonOrThrow(res)) as Report;
}

/** 当日より前の直近の報告（前回参照）を取得する。無ければ null。 */
export async function getPrevious(reportId: string): Promise<Report | null> {
  const res = await fetch(`/api/reports/${reportId}/previous`, {
    cache: "no-store",
  });
  const data = await jsonOrThrow(res);
  return (data as Report | null) ?? null;
}

/** 下書き本文を抽象化層で要約し、結果を draft に保存して返す。 */
export async function summarizeReport(reportId: string): Promise<Report> {
  const res = await fetch(`/api/reports/${reportId}/summarize`, {
    method: "POST",
    cache: "no-store",
  });
  return (await jsonOrThrow(res)) as Report;
}

/** 自分の確定済み報告を新しい順に一覧する（閲覧用）。 */
export async function listReports(): Promise<ReportListItem[]> {
  const res = await fetch("/api/reports", { cache: "no-store" });
  return (await jsonOrThrow(res)) as ReportListItem[];
}

/** 報告1件の詳細（本文・要約を含む）を取得する。所有者のみ（他人は 403）。 */
export async function getReport(reportId: string): Promise<Report> {
  const res = await fetch(`/api/reports/${reportId}`, { cache: "no-store" });
  return (await jsonOrThrow(res)) as Report;
}

/** 編集後の要約で報告を確定する（status=confirmed、以後不変）。 */
export async function confirmReport(
  reportId: string,
  summary: AiSummary,
): Promise<Report> {
  const res = await fetch(`/api/reports/${reportId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ summary }),
    cache: "no-store",
  });
  return (await jsonOrThrow(res)) as Report;
}
