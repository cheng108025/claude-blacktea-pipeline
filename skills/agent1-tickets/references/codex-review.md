# 規格外部覆核（僅 run-policy 授權 plan／both 才讀）

主對話確認 state 的 plan 覆核槽尚未使用；沒有 state 時先 init。以 `external-review --kind plan` 登記本次嘗試，全專案最多一次；失敗也保留紀錄，不在每次修訂自動重跑。

確認 Codex CLI 可用，以 `codex exec --sandbox read-only` 請它閱讀規格及 tickets.json，指出矛盾、缺口與不可行做法，附來源與嚴重度；輸出存 `.pipeline/plan/external-review.log`，設定逾時。工具不可用或失敗就明示，不能放寬執行權限。

外部意見不是裁決：主對話先核對證據，成立的重大產品歧義問使用者，實作细節自行修訂；無依據的忽略並記原因。結果隨規格確認一起摘要，不另創一套分級門禁。
