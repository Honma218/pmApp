"use client";

import type { AiSummary } from "@/lib/api";

// 編集時は全カテゴリを確定した配列として扱う（欠損を空配列に正規化）。
export type EditableSummary = {
  incidents: string[];
  achievements: string[];
  issues: string[];
  skills: string[];
};

const CATEGORIES: { key: keyof EditableSummary; label: string }[] = [
  { key: "incidents", label: "対応事項" },
  { key: "achievements", label: "成果" },
  { key: "issues", label: "課題" },
  { key: "skills", label: "スキル" },
];

// API の AiSummary（各フィールド任意）を編集用の全カテゴリ配列に正規化する。
export function toEditable(summary: AiSummary | null): EditableSummary {
  return {
    incidents: summary?.incidents ?? [],
    achievements: summary?.achievements ?? [],
    issues: summary?.issues ?? [],
    skills: summary?.skills ?? [],
  };
}

export function SummaryEditor({
  value,
  onChange,
  disabled = false,
}: {
  value: EditableSummary;
  onChange: (next: EditableSummary) => void;
  disabled?: boolean;
}) {
  const updateItem = (key: keyof EditableSummary, index: number, text: string) => {
    const items = [...value[key]];
    items[index] = text;
    onChange({ ...value, [key]: items });
  };

  const removeItem = (key: keyof EditableSummary, index: number) => {
    const items = value[key].filter((_, i) => i !== index);
    onChange({ ...value, [key]: items });
  };

  const addItem = (key: keyof EditableSummary) => {
    onChange({ ...value, [key]: [...value[key], ""] });
  };

  return (
    <div className="summary-editor">
      {CATEGORIES.map(({ key, label }) => {
        const items = value[key];
        const needsReview = items.length === 0;
        return (
          <fieldset key={key} className="summary-category">
            <legend>
              {label}
              {needsReview && (
                <span className="review-badge">要確認: 未入力</span>
              )}
            </legend>
            {items.map((item, index) => (
              <div key={index} className="summary-item">
                <input
                  type="text"
                  value={item}
                  disabled={disabled}
                  onChange={(e) => updateItem(key, index, e.target.value)}
                />
                {!disabled && (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => removeItem(key, index)}
                    aria-label={`${label}の項目を削除`}
                  >
                    削除
                  </button>
                )}
              </div>
            ))}
            {!disabled && (
              <button
                type="button"
                className="link-button"
                onClick={() => addItem(key)}
              >
                ＋ 項目を追加
              </button>
            )}
          </fieldset>
        );
      })}
    </div>
  );
}

// 確定送信用に、空文字の項目を除いて API 形へ整える。
export function toApiSummary(value: EditableSummary): AiSummary {
  const clean = (items: string[]) =>
    items.map((s) => s.trim()).filter((s) => s.length > 0);
  return {
    incidents: clean(value.incidents),
    achievements: clean(value.achievements),
    issues: clean(value.issues),
    skills: clean(value.skills),
  };
}
