---
name: agent3-quality-check
description: 稽核員技能 b「品質檢查」——檢查程式碼可讀性、可維護性、有沒有不必要的程式碼（工單外功能、死碼、未用相依、重複邏輯）；優先用工具當證據；只出 Medium/Low、不擋關。預載進 agent3-review。
user-invocable: false
---

<!-- ══════════════ 給使用者的導讀（此區塊是給人看的，不是執行指示）══════════════

這是稽核員的第二個技能：全案稽核的 E 段。它被預載進 ~/.claude/agents/agent3_review.md，
稽核員在全案稽核時照本檔做一次（首輪全專案、複審輪只看 diff）。
發現的問題只會是 Medium 或 Low，收進「已知限制」最後批量修，不會擋關——
這是設計者的決定：品質問題不該吃掉稽核的 3 輪額度。

🔧 = 可調整處：
  查哪些項目、各算什麼嚴重度 → ~/.claude/skills/agent3-quality-check/references/quality-checklist.md
  想讓某類品質問題擋關（例如工單外功能升 High）→ 改該檔的「嚴重度對照」表

═══════════════════════════════════════════════════════════════════════ -->

# 品質檢查：可讀、可維護、沒有多餘的程式碼

- **範圍**：呼叫方指定——全專案（全案稽核首輪）／`git diff` 範圍（複審輪、變更輪）／單票異動檔案（票級檢查順帶）。
- **產出**：發現表的列（併入 `04-verify-report.md`，V 編號接續），每條附證據。

## 怎麼做

1. Read `~/.claude/skills/agent3-quality-check/references/quality-checklist.md`，13 條逐條檢查，每條記：通過／發現／不適用。
2. **工具優先，感覺其次**——品質最容易變成口味之爭，工具輸出是客觀證據：
   - Python：`ruff check .`（未安裝 → `python -m pip install --user ruff` 試一次）、`vulture .`（死碼）。
   - JS／TS：`npx -y eslint .`、`npx -y ts-prune`（未用的 export）、`npx -y jscpd src`（重複程式碼）。
   - 其他語言：用該語言的標準 linter；沒有就用 `grep` 找未引用的符號、重複片段。
   - 工具裝不起來或跑不動 → 在報告標「**未執行工具掃描（原因）**」，改用人工檢查——不准默默跳過。
3. **工單外的功能**（清單第 9 條）要對照規格書「功能清單」與「本版不做」逐項看，不是憑印象。
4. 每個發現一列，格式同 04 報告：`| V-xxx | 實作問題 | Medium／Low | 檔案:行號 | 描述（≤400 字元） | 證據（工具輸出存 evidence/V-xxx-quality.log，只留路徑） | 建議修法（≤200 字元） |`。

## 規則

- **只能給 Medium 或 Low**（依 checklist 的對照表）；**不改變關卡條件**（關卡仍是 Critical=0 且 High=0）。想讓某類升級擋關，改 checklist 的對照表 🔧，不要在這裡自行升級。
- 零發現是有效結果；不為了證明有檢查而製造發現；個人偏好不能單獨成立發現。
- 發現照常收進 04 報告的「已知限制」節，由總指揮逐項抄進 FINAL-REPORT——最後批量修或由使用者決定接受。
