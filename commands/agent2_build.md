---
description: 執行 Agent 2 建造者——依 .pipeline/plan/02-workplan.md 實作全部任務（或執行修復輪）
argument-hint: [修復輪：依 04/05 報告退回清單 | 只做 T-Rev 任務]
model: opus
---

<!-- ══════════ 給使用者的導讀（給人看的，不是執行指示）══════════
這是 /agent2_build 指令：門禁檢查 → 呼叫建造者 subagent（agent2-build）→
完成後跟你摘要結果。建造者本人的行為規則在 .claude/agents/agent2_build.md，
想改「怎麼建造」去那裡改；這裡只管「什麼時候准開工、做完怎麼回報」。
═══════════════════════════════════════════════════════ -->

使用者附加指示：$ARGUMENTS
（上一行若為空 → 執行預設完整建造流程；有內容 → 原樣轉達給建造者，例如「修復輪：依 04-verify-report.md 的退回清單修復」或「只做 T-Rev 任務」。）

**門禁**：`.pipeline/plan/02-workplan.md` 必須存在且已定稿（檔首沒有 DRAFT 標記）。不符合 → 提示使用者先跑 `/agent1_plan` 完成最終確認，然後停止。

請使用 agent2-build subagent 執行建造。

建造者完成後，讀 `.pipeline/03-build-log.md`，向使用者摘要：

- 完成任務數／總數
- BLOCKED 清單（如有 → 說明各卡點；屬需求缺漏 → 提示跑 `/agent1_plan` 走需求變更子流程）
- 偏離事項數
- 整體檢查結果（install / build / test）
- 下一步建議：全數完成且無 BLOCKED → 執行 `/agent3_review`
