# 角色索引

| 角色檔 | 註冊名稱 | 執行位置／呼叫者 | 職責 |
|---|---|---|---|
| agent1_plan.md | 無 name | 主對話 Read | 與人釐清、規格、開票、確認 |
| agent0_conduct.md | agent0-conduct | 主對話 Agent | 流程控制、派執行角色、報告 |
| agent2_build.md | agent2-build | agent0 的 dispatch | 隔離工作區實作／修復 |
| agent3_ticket_check.md | agent3-ticket-check | dispatch，建造完成後 | 獨立驗證並簽 receipt |
| agent3_review.md | agent3-review | agent0，整合完成後 | 稽核與 V 發現關閉 |
| agent4_run.md | agent4-run | agent0，稽核後 | 黑箱實測與 E／U 關閉 |

只有 agent0 派子 agent。worker 設 disallowedTools: Agent；Git 寫入只有 agent0 執行 dispatch。這些 prompt 的責任限制不等於作業系統權限隔離，尤其 Bash 可執行多種指令；真正提交門禁由腳本另核對。

agent1 沒有 name，因此保持主對話劇本。稽核不再預載品質 skill，使用時按需讀取。模型由各 agent frontmatter 決定。

共通契約與完整轉移規則見 `blacktea/protocol.md`、`blacktea/references/execution.md`；不要在每個角色重新寫一套重試或門禁。
