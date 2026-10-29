---
description: 建立紅茶流水線專案，或從持久狀態續跑。
argument-hint: [需求描述 | 從階段 N 開始]
model: opus
disable-model-invocation: true
---

使用者輸入：$ARGUMENTS

你是主對話入口。先 Read `~/.claude/blacktea/protocol.md`；只處理使用者互動與 agent0 監督，不實作功能。

## 分流

| 專案狀態 | 執行方式 |
|---|---|
| 沒有工單／仍 DRAFT | Read `~/.claude/agents/agent1_plan.md`，在主對話完成訪談→規格→開票→確認 |
| 已定稿、尚未建造 | 核對 git-policy、run-policy，缺的在主對話補齊（run-policy 缺「票級 Codex 驗證」欄不問，直接補「開」並告知）；用 Agent 呼叫 `agent0-conduct`，mode=build |
| 執行中／中斷 | 讀 state.json（舊版先遷移），告知進度；同模式、同 run_id 呼叫 agent0 續跑 |
| NEEDS_USER | 問 state 記錄的問題；需求問題由主對話 agent1 修訂規格、開新輪；其他決策記錄後續跑 |
| COMPLETED／INCOMPLETE，報告存在 | 修改既有專案就 Read `~/.claude/commands/blacktea_change.md` 接手，不要求使用者重打一遍；全新專案先確認歸檔範圍 |
| state 已終止但報告缺少 | agent0 只補收尾，不重建 |

使用者指定階段 N（2 建造／3 稽核／4 實測／5 收尾）：交 agent0 檢查門禁。明說跳過稽核／實測可以記錄跳過，但結案必須 INCOMPLETE；票級檢查不可跳過。

## 訪談後直接交棒

規格、工單及必要 UI 外觀確認後，直接 spawn `agent0-conduct`。它有獨立 context，不強制換新對話。使用者要求稍後開工就保存狀態；context 確實不足才提示新對話續跑。

## 監督

Agent prompt 帶 project_root、mode、run_id（首次可無）、使用者已做的決策及指定階段。agent0 執行中只轉述進度，不改檔、不另派執行角色。

**同時只能有一隻 agent0**：每次 spawn 前用 ListAgents 確認前一隻 agent0 與它派出的角色都已結束。兩隻並存會各自派工、搶 port、互相覆寫報告；發現並存先停掉多餘的，再核對 Git 與 `.pipeline/` 有沒有被寫壞。

- `COMPLETED`／`INCOMPLETE`：讀本輪報告，摘要結果、限制與待辦，提醒 `/blacktea_retro`。
- `CONTINUE`：確認 state 已更新且無執行中的角色，重新 spawn 相同模式的 agent0；最多 10 次。
- `NEEDS_USER`：問具體問題；決策記 state，需求修訂由 agent1 處理，再派 agent0。
- 空回報／工具錯誤：核對 state 與 Git；不能確認進度就報告阻塞原因，不盲目重派。
