---
type: playbook 追記案（工程0）
出典: docs/memory-bank/2026-07-11-harness-bootstrap-observations.md #(4)(5)
status: pending（本体は AIアーキ確定可）
---

# 初回スケルトン投入は用途別に複数 PR へ最初から分ける

## 提案

`docs/playbook.md` 工程0（`pending-repo-bootstrap-procedure.md` と共通化）に、
初回スケルトン投入の分割方針を明記する。

- `backend/` `frontend/` `tools/` `docs/` 用 → `feature/*`
- `acceptance/` `docs/spec/` 用 → `spec/*`（ADR-0001・ADR-0004）
- `reference-mock/` 用 → 統合役が直接 vendor（Bash 経由の git 操作。ADR-0005）。
  実施手順は `docs/memory-bank/2026-07-11-harness-bootstrap-observations.md` #(5) 参照

## 根拠

main が空の状態でスケルトン一式を1本の `feature/*` ブランチに一括投入したところ、
`acceptance/`・`docs/spec/` 配下のプレースホルダーが `guard-acceptance.yml` の path-guard に
検知されて fail した（ルール自体は正常動作）。PR分割（feature/spec）で回避したが、
「複数レイヤーにまたがる初回スケルトンをどう複数 PR に分割するか」が playbook／brief スキルの
どこにも書かれていなかった。

`reference-mock/` については別途、シード棚卸し → `git subtree add --squash` → 統合役直接 PR、
という手順で 2026-07-11 に初回投入を実施済み（対応自体は完了済みだが、手順の恒久文書化は
この提案に含める）。

## 判断待ちの点

PM／AIアーキが上記を `docs/playbook.md` 工程0の正本に統合するか。
`.claude/skills/brief/SKILL.md` への追記要否も合わせて判断。
