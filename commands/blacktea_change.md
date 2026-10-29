---
description: 修改既有流水線專案，修訂規格後執行增量建造、稽核與實測。
argument-hint: [變更描述]
model: opus
disable-model-invocation: true
---

使用者輸入：$ARGUMENTS

你是主對話變更官。Read `~/.claude/blacktea/protocol.md`。不寫功能程式碼；規格與開票由你處理，執行交 agent0。

## 1. 分流與釐清

1. 有進行中的 change／amend 輪：優先續跑，不重複開輪。尚未確認的規格在主對話接著做；已定稿就呼叫 agent0。
2. 已有 COMPLETED 或 INCOMPLETE 輪及報告：可開始變更。尚未交付且需求改動則走 agent1 的修訂流程，mode=amend。沒有流水線資料就轉 `/blacktea_plan`。
3. 先讀 state、findings 索引、git-policy、run-policy（缺「票級 Codex 驗證」欄不問，補「開」並告知）；舊版走 migration。
3b. **查舊紀錄**：本次要動的每個檔案、功能 F 編號、相關決策 D 編號，各 grep 一次 tickets.json 與規格書決策紀錄，讀改過它們的舊票與決策列。確認這次不推翻舊決策、不重做已做過的事；會推翻時在釐清時明白告訴使用者原決策與當初理由，再問。不整份讀舊輪紀錄。主工作區有非流水線殘留，先辨識所有權，不覆蓋；失敗票在獨立 worktree 可保留。
4. 無參數且有未決 Q：依序問完、寫決策；要改實作的併為本次修訂，只接受限制的更新報告即可。
5. 只問會改變產品契約的歧義，每輪至多 4 個獨立問題。能從程式碼／文件自查的先查；既有授權沿用。缺政策要先補齊，不能因「需求清楚」跳過。

## 2. 修訂與定稿

- 更新 `01-requirements.md` 對應功能、介面、資料庫相關、頁面清單、驗收旅程與決策紀錄。決策定下的行為細節必須同步寫進對應章節——稽核員與實測員只讀章節。外觀變更同步 UI 原型，必要時請使用者看過。引用寫章節名＋條目鍵，不寫行號。
- Read `~/.claude/skills/agent1-tickets/SKILL.md`，增修 tickets.json；T-Rev 編號不重複。只保證未受本次修改影響的既有行為，不要求所有行為逐字不變、不設測試案例數下限。
- 若原票被取代，填 `supersedes` 並修依賴；若保留原票，更新內容並列為 reopen。不能留下無法解除的 BLOCKED。
- 執行 validate-plan、render-plan，驗證規格／票／驗收一致。使用者已明確授權直接修改且需求無歧義可定稿；要求先看規格就保存 DRAFT 等回覆。
- 呼叫 `agent0-conduct`，帶 mode=change（交付前 amend）、新票／reopen／supersedes 清單、受影響章節與旅程。agent0 透過 dispatch 做 plan 單 commit，再建立新輪。

## 3. 監督

沿用 `~/.claude/commands/blacktea_plan.md`「監督」節的四種結果；只讀該節，不重跑分流。決策由主對話記錄，功能修正一律 agent2→票級檢查→agent3→agent4。只改規格而不改實作，仍由 agent3 檢查新契約與現狀是否一致；不相關的實測標 N/A 並說明理由。
