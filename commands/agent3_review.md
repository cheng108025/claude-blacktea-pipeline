---
description: 執行 Agent 3 稽核員——四段獨立稽核（可對任何專案單獨使用）
argument-hint: [複審輪：僅增量掃描 | agent4 退回：增量複審變更範圍]
model: opus
---

<!-- ══════════ 給使用者的導讀（給人看的，不是執行指示）══════════
這是 /agent3_review 指令：門禁檢查 → 呼叫稽核員 subagent（agent3-review）→
完成後跟你摘要關卡判定。稽核員本人的檢查規則（四段檢查、嚴重度、關卡條件）
在 .claude/agents/agent3_review.md，想調整「稽核多嚴」去那裡改。
覺得稽核誤報 → 在 .pipeline/waivers.md 逐條記豁免，不要改鬆稽核規則。
═══════════════════════════════════════════════════════ -->

使用者附加指示：$ARGUMENTS
（上一行若為空 → 執行預設完整稽核；有內容 → 原樣轉達給稽核員。）

**門禁**（只在流水線模式檢查，即 `.pipeline/plan/02-workplan.md` 存在時）：工作單應全部 `[x]` 且 `03-build-log.md` 沒有未解的 BLOCKED，否則提示先完成 `/agent2_build`，然後停止。單獨模式（沒有 01/02）跳過此檢查。

請使用 agent3-review subagent 對本專案執行完整稽核。

稽核員完成後，讀 `.pipeline/04-verify-report.md`，向使用者摘要：

- 關卡判定（PASS／FAIL，已扣除 `.pipeline/waivers.md` 豁免項）
- Critical／High 清單
- 需求層級發現（如有 → 提示跑 `/agent1_plan` 走需求變更子流程，不退建造者）
- 環境問題（如有 → 提示使用者處理；這不是程式問題，不佔退回額度）
- FAIL 且為實作問題 → 提示執行 `/agent2_build 修復輪`。**輪數看報告檔首的「稽核輪次」，上限 3 輪**；檔首「觸發來源」是 agent4 退回的複審**不佔這 3 輪**。超過上限就停，改由使用者決定：waiver 豁免／改需求／人工處理
- PASS → 提示下一步執行 `/agent4_run`

摘要保持精簡：只講關卡結果、擋關項與去向；細節留在報告檔，**不整份重述**。
