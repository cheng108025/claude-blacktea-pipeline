# 訪談官產出格式範例（2026-10-25·ai-secretary）

訪談官（agents/agent1_plan.md ＋ skills/agent1-spec、agent1-tickets）的**格式樣本**。新專案的規格書、工作單、UI 原型照這三份的**結構與呈現方式**寫；內容（功能、技術、數字）一律以新專案的訪談結果為準，不得照抄本案的需求、決策或技術選型。

| 檔案 | 看什麼 |
|---|---|
| `01-requirements-example.md` | 檔首缺口總覽（含外部覆核分級處理）；資料庫相關＝資料表總覽表＋每表欄位表＋章末建表 SQL；介面契約＝共通規則表、端點總覽（A 編號）、資料型別欄位表、各端點請求／回應欄位表、錯誤碼總表；設計系統＝視覺樣本（內嵌 HTML，亮暗並排）＋含「用途」欄的 token 表＋WCAG 對比驗算說明；流程、邊界、資安、決策一律表格 |
| `02-workplan-example.md` | 檔首缺口總覽、使用說明（UI 票共同規定、截圖配方）、功能群與功能文件對照表、每群「這一群怎麼做」、六欄票、文末自我稽核結果表與總表 |
| `ui-prototype-example.html` | 外觀契約橫幅、目錄、每頁一個含頂欄的「瀏覽器框」、主要頁面的空資料／錯誤狀態小框格、手動日夜切換、全部用 token |

HTML 檢視版一律用 `uv run ~/.claude/blacktea/md2html.py` 產生（見 agents/agent1_plan.md Phase E）。
