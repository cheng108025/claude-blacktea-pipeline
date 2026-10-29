# 技能索引

| 技能 | 何時讀 | 執行者 |
|---|---|---|
| agent1-interview | 初次規劃或重大產品歧義 | 主對話 agent1 |
| agent1-spec | 訪談足以寫可驗收契約 | 主對話 agent1 |
| agent1-tickets | 規格完成／修訂 | 主對話 agent1／變更官 |
| blacktea-dispatch | 建造、修復、Git 整合或文件 commit | agent0 |
| agent3-quality-check | 稽核的品質步驟 | agent3-review；票級檢查僅明確要求時 |
| git | Git 政策、push 與故障 | 主對話或 dispatch |
| vscode、clawd | 对應本機工具故障 | 主對話 |

四個 Read 接力技能保留 user-invocable: false、disable-model-invocation: true；品質 skill 隱藏選單但可由稽核按需讀取。入口仍是三個 blacktea commands。

SKILL.md 留職責、輸入輸出、路由與必要約束；只有實際適用時才讀 references。跨角色的流程協定集中 blacktea/protocol.md；確定性的格式／狀態／驗證機制交 scripts，不在 prompt 裡重寫演算法。
