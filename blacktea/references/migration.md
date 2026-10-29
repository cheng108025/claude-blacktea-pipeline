# 舊版專案接手（只在沒有 v2 state.json 時讀）

1. 保存原 state.md、工單、03／04／05 到 `.pipeline/legacy/`；複製不移動，保留舊證據連結。
2. 對照舊工單與 Git 建立 `plan/tickets.json`（格式見 tickets skill）。已有 `[x]` 不等於已驗證：只有可對應的 commit、票級 PASS 與仍成立的 DoD 才可匯入為 COMMITTED；不確定的票列待重新檢查。
3. 建立 `.pipeline/legacy/import.json`：`{"tickets":{"T01":{"status":"COMMITTED","commit":"完整sha"}},"next_ids":{"V":12,"E":4,"U":1,"Q":2}}`。next_ids 必須大於歷史所有輪次與 waivers 中的最大 ID；舊發現另整理為 `.pipeline/findings.md` 索引（ID、狀態、原報告路径）。
4. `pipeline.py --root <專案> init --legacy-import <import.json>` 驗證 commit 存在後建立新狀態；它不替你證明歷史 DoD。匯入後的首輪派完整稽核與全旅程實測。歷史不完整需在報告明示。
5. 舊 run-policy 缺欄位：沿用原模式、採協定重試上限；沒有政策就在主對話補問。Git 政策缺 remote／branch 時從既有設定查證；與已授權目的地無法對應才問人。
6. 重新產生工單檢視版；新輪編號避開已存在的 rounds 目錄，不改舊報告。
