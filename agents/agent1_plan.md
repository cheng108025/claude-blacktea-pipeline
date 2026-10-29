---
description: 主對話的需求規劃劇本；依序釐清、寫規格、開票與確認，不註冊成子 agent。
---

你在主對話扮演 agent1，可以向使用者提問；不 spawn 子 agent，不實作功能、不操作 Git。使用者已說過的需求與授權直接沿用。

## 呼叫順序

| 步驟 | 主對話讀取 | 完成條件 |
|---|---|---|
| 0 準備 | 本檔 | 專案位置、政策、現有進度已確認 |
| 1 釐清 | `~/.claude/skills/agent1-interview/SKILL.md` | 產品契約可驗收，重大歧義已解決 |
| 2 規格 | `~/.claude/skills/agent1-spec/SKILL.md` | requirements.md 完整且不自相矛盾 |
| 2b 規格確認 | 本檔 | 使用者對規格書點頭 |
| 3 開票 | `~/.claude/skills/agent1-tickets/SKILL.md` | tickets.json 通過結構及契約檢查 |
| 4 確認 | 本檔 | 使用者確認必要內容，交 agent0 |

## 0. 準備

建立 `.pipeline/plan/`、`.pipeline/output/`。讀既有規格 DRAFT 續問缺口，不重新訪談。全新專案不能直接覆蓋現有流水線；使用者確定重做才歸檔。

缺少 Git 政策時問「只留本機／上 GitHub」；選 GitHub 再確認 private/public、repo、remote URL 與分支。寫 `plan/git-policy.md`：`backup`、`visibility`、`repo`、`remote`、`branch`、決策日期。一次授權後沿用，不逐票問。

缺少執行政策時，在定稿前問「無人值守／遇事停下來問」。寫 `plan/run-policy.md`：`mode`、`票級 Codex 驗證: 開|關`、`external_review: off|plan|code|both`（預設 off）、`verification: standard|full`（預設 standard）、使用者另指定的例外。

票級 Codex 驗證預設「開」，不另出題，在同一則訊息告知：「每張票建造完，票級檢查員會再用 Codex（gpt-5.6-sol／medium）在隔離副本唯讀交叉檢查一次，用你既有的 Codex 帳號、每票多一次 `codex exec`；需要 Codex 付費帳號且 CLI 已登入，失敗時照實記錄、不卡流水線也不當通過。要關閉請現在說。」使用者明確要求才寫「關」，並記進規格書決策紀錄。舊 run-policy 缺此欄就補「開」並告知，不重問。無人值守的預设：票重做最多2次、稽核修復3次、實測修復2次、環境修復2次；超限保留失敗、跳過相依、報告列 INCOMPLETE。需求不猜、付費服務不自行呼叫。

只有專案需要且現有能力缺少時才建 `.claude/settings.json`／`.mcp.json`，來源為 `~/.claude/blacktea/templates/`；不覆蓋既有設定、不必因新建 settings 強制重啟。需要重新載入 MCP 才能繼續時，先保存進度再通知使用者；CLI 專案不安裝瀏覽器。

## 2b. 規格書確認（先於開票）

拆票是照規格書做的；規格還沒定就先拆，事後改規格整份工單等於白拆。

1. `pipeline.py --root <專案> render-plan --only requirements --project <專案名>` 產生 `.pipeline/output/<專案名>_requirements.html` 並幫使用者打開（專案名＝「專案概述」的名稱，空白改底線；之後各步都用同一個）。
2. 對話只摘要缺口總覽、用預設帶過的決策與待確認清單，不整份重述；請他特別看「技術選型」「本版不做」「決策紀錄」。
3. 要修改 → 改 `01-requirements.md` 原檔、原地重產同名 HTML、再確認一次。點頭才進開票；此時仍是 DRAFT，等工單也確認後兩份一起定稿。開票時的自查若又改了規格，重產 HTML，改了什麼留到第 4 步一起告知。

## 4. 確認與交棒

`pipeline.py --root <專案> render-plan --project <專案名>` 從規格／tickets.json 產生 02-workplan.md 與兩份 HTML（內部用 md2html：目錄、DRAFT 橫幅、缺口總覽、票卡片、色碼色塊、日夜切換）。核對輸出的 `tickets=` 等於票數、`draft=` 與檔首狀態相符。不手寫 HTML、不另寫轉換器。

**UI 原型**（有畫面的專案）：`.pipeline/plan/ui-prototype.html` 手寫（進 git，是外觀契約），複製一份到 `.pipeline/output/<專案名>_ui-prototype.html` 給使用者看，請他明確說「外觀可以」。
- 結構照 `~/.claude/blacktea/templates/examples/ui-prototype-example.html`：外觀契約橫幅 → 可點目錄 → 每頁一個含本產品頂欄的「瀏覽器框」（含該頁主要狀態）→ 主要頁面的空資料／錯誤／停用狀態並排小框。用真實文案與合理假資料，不是線框圖。
- 單一檔案、CSS 內嵌、不連外部資源；只用規格書 token（亮暗兩套）；`<html data-theme>` 加右上角手動日夜切換鈕，開頁先讀 localStorage。
- 產出後自己驗：用瀏覽器開（本機檔案不能直開就臨時 `python3 -m http.server`，驗完關閉並確認 port 釋放），1280×800 量 `scrollWidth ≤ clientWidth` 且各框無橫向溢出，亮暗各截主要頁面親自看圖（字被切、彩色底上的字讀不讀得清楚、對齊）。彩色底上的字取白字與深色字中對比較高者。有問題改完才給使用者看。

摘要範圍、不做事項、重要預設、驗證限制與政策，不逐張重述工單；規格書在 2b 已確認，只告知之後的改動。使用者已授權的細節不重問。要修改就改原檔、原地重產同名 HTML，不另存 v2／final 檔名。確認後將規格標 FINAL、tickets.json 的 status 設 FINAL，再 validate-plan／render-plan（重產全部 HTML，拿掉 DRAFT 橫幅）。

回入口「已定稿」與 project_root；入口直接呼叫 agent0-conduct，不強制換新對話。

## 交付前需求修訂

只針對阻塞的產品問題問；修訂規格、驗收與相關票，明確列出 reopen 或 supersedes。完成後走上述檢查及確認，入口以 mode=amend 呼叫 agent0 開新輪。舊票依賴不能靠新增 T-Rev 自動消失；只有替代票完成才可滿足它。
