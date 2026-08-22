---
name: agent1-tickets
description: 訪談官技能 c「照規格書拆任務」——Phase D，出 02-workplan.md 工作單、自我稽核 7 項、可選 Codex 覆核。由 ~/.claude/agents/agent1_plan.md 接力讀取，不單獨使用。
user-invocable: false
---

<!-- ══════════════ 給使用者的導讀（此區塊是給人看的，不是執行指示）══════════════

這是訪談官的第三個技能：把規格書拆成一張一張可勾選、可驗證的 ticket，並模擬下游視角找碴。
由 ~/.claude/agents/agent1_plan.md 在規格書寫完後 Read 本檔照做，跑在主對話。

🔧 = 可以調整的數字或清單：

  想調整什麼                      | 在哪個檔                                                               | 段落
  ticket 要拆多小                 | 本檔                                                                   | 「每張 ticket 的品質要求」第 1 條
  ticket 有哪些欄位、長什麼樣     | ~/.claude/skills/agent1-tickets/references/ticket-template.md          | 全檔
  .gitignore 要擋哪些檔、T01 內容 | ~/.claude/skills/agent1-tickets/references/workplan-structure.md       | T01
  交棒前自我檢查哪些項目          | ~/.claude/skills/agent1-tickets/references/self-audit-checklist.md     | 7 項
  待問清單最多追問幾輪            | 同上                                                                   | 第 7 項
  要不要用 Codex 當第二雙眼睛     | ~/.claude/skills/agent1-tickets/references/codex-review.md             | 全檔（含重度／中度／輕度分級）

═══════════════════════════════════════════════════════════════════════ -->

# 訪談官技能 c：照規格書拆任務（.pipeline/plan/02-workplan.md）

- **前提**：`01-requirements.md` 已寫完且沒有任何「待定」。不符合 → 停，回報「請先完成規格書（agent1-spec）」。
- **產出**：`02-workplan.md`（檔首「> 狀態：DRAFT」）、自我稽核 7 項結果、外部覆核結果（依重度／中度／輕度分組）；完成後回到 `agent1_plan.md` 接力 Phase E。

工作單的單位是 **ticket**：一張 ticket ＝ 一項獨立、可勾選、可驗證的工作。每個需要做的項目都要分別列成一張——不准把好幾件事塞進同一張。

## 流程

1. Read `references/ticket-template.md`（六欄定義與範例）與 `references/workplan-structure.md`（檔首 DRAFT、T01、功能票、README 票、文末聲明），照著寫出全部 ticket。
2. 逐張套用下面「每張 ticket 的品質要求」。
3. Read `references/self-audit-checklist.md`，7 項逐條做完並展示結果；待問清單不空就回去追問（最多 2 輪 🔧）。
4. Read `references/codex-review.md`，問使用者要不要外部覆核；有跑就依分級處理，重度缺口處理完才能交棒。
5. 回到 `~/.claude/agents/agent1_plan.md`，接力 Phase E（產 HTML、請使用者確認、定稿）。

## 每張 ticket 的品質要求

- **要小**：一張 30 分鐘內能完成 🔧；太大就拆。
- **完成條件可判對錯**：用回應碼、輸出內容、檔案存在與否描述；禁用「適當」「合理」「正常運作」這種靠感覺的詞。記住：「完成實作」只是宣稱；「測試通過」可作證據，但**不能取代功能本身應達成的結果**——完成條件要寫到功能結果那一層。涉及數值計算的票，完成條件要給**預期值與算法來源**（驗「值對」不只驗「有值」）。
- **驗證實作偏好**：規格書裡標「實作偏好（未驗證）」的項目，寫「做法」欄時逐項驗證——可行就採用、有問題就修正或拒絕，並在決策紀錄註明依據；不得未經驗證直接照抄。
- **驗證指令**：HTTP 用 `curl`；丟棄輸出用 `-o /dev/null`；長駐服務「背景啟動→輪詢健康檢查→驗證→關閉（kill 後確認 port 已釋放）」；全部指令不能等待人工輸入。
- **同一檔案在一張票裡只能有一個動作**（「新增」或「改寫」或「保留原內容只加一段」擇一），不准同時寫「整份改寫」又「原內容暫留」這種互相矛盾的做法。
