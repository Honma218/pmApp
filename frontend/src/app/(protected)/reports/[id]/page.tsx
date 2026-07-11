"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getReport, type Report } from "@/lib/api";
import { SummaryEditor, toEditable } from "@/components/SummaryEditor";

// 報告詳細（読み取り専用）。本文と要約をそのまま表示する。編集・確定はしない。
export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const reportId = params.id;

  const [report, setReport] = useState<Report | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await getReport(reportId);
        if (active) setReport(data);
      } catch {
        if (active) setLoadError(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [reportId]);

  return (
    <main className="container">
      <p>
        <Link href="/reports">← 過去の報告へ戻る</Link>
      </p>
      {loadError ? (
        <p className="muted">
          報告の読み込みに失敗しました。閲覧権限が無いか、存在しない可能性があります。
        </p>
      ) : !report ? (
        <p className="muted">読み込み中…</p>
      ) : (
        <>
          <h1>報告詳細（{report.report_date}）</h1>
          <section className="detail-section">
            <h2>本文</h2>
            <p className="previous-text">{report.raw_text || "（本文なし）"}</p>
          </section>
          <section className="detail-section">
            <h2>要約</h2>
            <SummaryEditor
              value={toEditable(report.ai_summary_json)}
              onChange={() => {}}
              disabled
            />
          </section>
        </>
      )}
    </main>
  );
}
