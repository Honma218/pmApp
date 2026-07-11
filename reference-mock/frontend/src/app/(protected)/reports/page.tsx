"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listReports, type ReportListItem } from "@/lib/api";

// 確定済み報告の一覧（閲覧のみ）。詳細へのリンクを並べる。
export default function ReportsListPage() {
  const [reports, setReports] = useState<ReportListItem[] | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list = await listReports();
        if (active) setReports(list);
      } catch {
        if (active) setLoadError(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="container">
      <h1>過去の報告</h1>
      {loadError ? (
        <p className="muted">
          一覧の読み込みに失敗しました。時間をおいて再読み込みしてください。
        </p>
      ) : !reports ? (
        <p className="muted">読み込み中…</p>
      ) : reports.length === 0 ? (
        <p className="muted">確定済みの報告はまだありません。</p>
      ) : (
        <ul className="report-list">
          {reports.map((r) => (
            <li key={r.id} className="report-list-item">
              <Link href={`/reports/${r.id}`}>
                <span className="report-list-date">{r.report_date}</span>
                <span className="report-list-status">確定済み</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
