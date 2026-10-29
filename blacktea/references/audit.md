# agent3 稽核程序

## 範圍

full：讀規格功能與驗收、必要票、所有第一方原始碼，排除依賴與生成檔。incremental：讀 baseline..HEAD 異動、相關呼叫端／共享契約、指定規格与先前 open 發現；影響範圍不明回報需升 full。

每次都核對本輪整合票有檢查 receipt、commit 與證據；單純找到 PASS 字樣不足。舊版缺紀錄標明歷史限制，這一輪不能偽補舊證據。

## 檢查項

1. 可運行性：依 verification reference 的驗證深度執行。缺工具／測試環境是 ENV_BLOCKED；確認實作導致啟動失敗才記 Critical。
2. 正確性：邏輯、邊界、例外、資源生命週期與相依整合；每個發現需具體觸發條件。
3. 資安：機密、注入、路徑、權限、錯誤洩漏、web 的 cookie／CORS、相依漏洞。適用才查；優先用專案既有工具，缺工具標未掃描，不為稽核改產品依賴。
4. 規格對照：功能／頁面／API／實體是否完成；被政策跳過的票列已知缺口，不重複開同症狀要求修復。
5. 品質：Read `~/.claude/skills/agent3-quality-check/SKILL.md`，列有證據的維護問題。
6. 舊發現：重現修正或反證後才 closed／withdrawn；不相關的舊 open 保留並註明未重測，不宣稱全案本輪驗證。

## 發現與判定

V ID 由 agent0 的 allocate 分配；可以先回臨時 ID 由它映射，但 report／findings 索引／waiver 引用必須一致。舊問題沿用 ID，跨輪不重新編號。

每列：ID、類型（implementation／requirement／environment）、嚴重度、狀態、檔案:行、症狀、重現證據路徑、修法摘要。

- Critical：不可運行、資料損失、可直接利用的安全漏洞。
- High：核心功能／權限錯誤、必要契約缺失、未經票級驗證的實作入庫。
- Medium／Low：不擋核心驗收的瑕疵與維護建議；不得因風格偏好捏造發現。
- 扣使用者指定 waivers 後，open Critical／High 為零且必要驗證已完成才 PASS。必要能力不足回 ENV_BLOCKED；需求無法判定回 NEEDS_REQUIREMENT。

報告 `<R>/04-verify-report.md` 記 HEAD、revision、實測指令、範圍、發現總帳、關卡、未驗項目及歷史章節連結。每次詳細證據另存 attempt 路徑。只有你確認 V 狀態，agent0 維護跨輪索引。

## 外部覆核（只有 prompt 明示已授權才讀）

先確認 CLI 與登入可用，以 `codex exec --sandbox read-only` 提供指定規格／diff 範圍與唯讀審查指示，設定逾時並輸出到 evidence。不可把工具裝好了當授權。只執行政策分配的 code 覆核一次；結果由你逐項驗證，不直接採信嚴重度。不支援唯讀選項或執行失敗就標未完成，不放寬權限。
