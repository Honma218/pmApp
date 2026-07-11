"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  confirmReport,
  createOrGetDraft,
  getPrevious,
  patchDraft,
  summarizeReport,
  type AiSummary,
  type Report,
} from "@/lib/api";
import {
  SummaryEditor,
  toApiSummary,
  toEditable,
  type EditableSummary,
} from "@/components/SummaryEditor";

// 端末ローカルの「今日」を YYYY-MM-DD で返す（表示はローカル、report_date は日付のみ）。
function localToday(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

type SaveState = "idle" | "saving" | "saved" | "error";
const AUTOSAVE_DELAY_MS = 800;

export function ReportEditor() {
  const [report, setReport] = useState<Report | null>(null);
  const [previous, setPrevious] = useState<Report | null>(null);
  const [text, setText] = useState("");
  const [summary, setSummary] = useState<EditableSummary | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [summarizing, setSummarizing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const reportIdRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 初期ロード: 当日下書きの取得/作成 → 既存要約の復元 → 前回参照の取得。
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const draft = await createOrGetDraft(localToday());
        if (!active) return;
        applyReport(draft);
        const prev = await getPrevious(draft.id);
        if (!active) return;
        setPrevious(prev);
      } catch {
        if (active) setLoadError(true);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // サーバから受け取った報告を画面状態へ反映する（要約があれば編集用に復元）。
  const applyReport = (next: Report) => {
    setReport(next);
    reportIdRef.current = next.id;
    setText(next.raw_text);
    setSummary(next.ai_summary_json ? toEditable(next.ai_summary_json) : null);
  };

  const save = useCallback(async (value: string) => {
    const id = reportIdRef.current;
    if (!id) return;
    setSaveState("saving");
    try {
      await patchDraft(id, value);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }, []);

  const onChange = (value: string) => {
    setText(value);
    if (!reportIdRef.current) return;
    setSaveState("saving");
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      void save(value);
    }, AUTOSAVE_DELAY_MS);
  };

  // アンマウント時に保留中のタイマーを破棄。
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const onSummarize = async () => {
    const id = reportIdRef.current;
    if (!id) return;
    setActionError(null);
    setSummarizing(true);
    // 直前の編集が保存される前に要約しないよう、保留中の自動保存を先に確定させる。
    if (timerRef.current) clearTimeout(timerRef.current);
    try {
      await patchDraft(id, text);
      const updated = await summarizeReport(id);
      applyReport(updated);
    } catch {
      setActionError("要約に失敗しました。本文を確認して再度お試しください。");
    } finally {
      setSummarizing(false);
    }
  };

  const onConfirm = async () => {
    const id = reportIdRef.current;
    if (!id || !summary) return;
    setActionError(null);
    setConfirming(true);
    try {
      const confirmed = await confirmReport(id, toApiSummary(summary));
      applyReport(confirmed);
    } catch {
      setActionError("確定に失敗しました。入力内容を確認してください。");
    } finally {
      setConfirming(false);
    }
  };

  if (loadError) {
    return (
      <p className="muted">
        報告の読み込みに失敗しました。時間をおいて再読み込みしてください。
      </p>
    );
  }

  if (!report) {
    return <p className="muted">読み込み中…</p>;
  }

  const confirmed = report.status === "confirmed";
  const canSummarize = !confirmed && text.trim().length > 0 && !summarizing;

  return (
    <div className="report-editor">
      <div className="report-meta">
        <span className="muted">対象日: {report.report_date}</span>
        <SaveIndicator state={saveState} confirmed={confirmed} />
      </div>

      <textarea
        className="report-textarea"
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder="今日の業務内容を自由に記入してください。入力は自動で下書き保存されます。"
        disabled={confirmed}
        rows={12}
      />

      {!confirmed && (
        <div className="action-row">
          <button
            type="button"
            className="button"
            onClick={onSummarize}
            disabled={!canSummarize}
          >
            {summarizing ? "要約中…" : "要約する"}
          </button>
        </div>
      )}

      {actionError && <p className="save-error">{actionError}</p>}

      {summary && (
        <section className="summary-section">
          <h2>{confirmed ? "確定済みの要約" : "要約の確認・編集"}</h2>
          {!confirmed && (
            <p className="muted">
              内容を確認・編集してください。AIは本文にない事実を補完しません。
              空のカテゴリは「要確認」として表示されます。
            </p>
          )}
          <SummaryEditor
            value={summary}
            onChange={setSummary}
            disabled={confirmed}
          />
          {!confirmed && (
            <div className="action-row">
              <button
                type="button"
                className="button"
                onClick={onConfirm}
                disabled={confirming}
              >
                {confirming ? "確定中…" : "確定する"}
              </button>
              <span className="muted">確定すると以後は編集できません。</span>
            </div>
          )}
        </section>
      )}

      <PreviousReference previous={previous} />
    </div>
  );
}

function SaveIndicator({
  state,
  confirmed,
}: {
  state: SaveState;
  confirmed: boolean;
}) {
  if (confirmed) {
    return <span className="save-indicator save-confirmed">確定済み（編集不可）</span>;
  }
  const label: Record<SaveState, string> = {
    idle: "",
    saving: "保存中…",
    saved: "保存済み",
    error: "保存に失敗しました",
  };
  const cls = state === "error" ? "save-error" : "save-ok";
  return <span className={`save-indicator ${cls}`}>{label[state]}</span>;
}

function PreviousReference({ previous }: { previous: Report | null }) {
  if (!previous) {
    return (
      <details className="previous-ref">
        <summary>前回の報告を参照</summary>
        <p className="muted">過去の報告はまだありません。</p>
      </details>
    );
  }
  return (
    <details className="previous-ref">
      <summary>前回の報告を参照（{previous.report_date}）</summary>
      <section className="previous-body">
        <h3>前回の本文</h3>
        <p className="previous-text">{previous.raw_text || "（本文なし）"}</p>
      </section>
      <PreviousSummary summary={previous.ai_summary_json} />
    </details>
  );
}

function PreviousSummary({ summary }: { summary: AiSummary | null }) {
  if (!summary) {
    return (
      <section className="previous-summary">
        <h3>前回の要約</h3>
        <p className="muted">要約はまだありません。</p>
      </section>
    );
  }
  const groups: { label: string; items?: string[] }[] = [
    { label: "対応事項", items: summary.incidents },
    { label: "成果", items: summary.achievements },
    { label: "課題", items: summary.issues },
    { label: "スキル", items: summary.skills },
  ];
  return (
    <section className="previous-summary">
      <h3>前回の要約</h3>
      {groups.map((g) => (
        <div key={g.label} className="summary-group">
          <h4>{g.label}</h4>
          {g.items && g.items.length > 0 ? (
            <ul>
              {g.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">―</p>
          )}
        </div>
      ))}
    </section>
  );
}
