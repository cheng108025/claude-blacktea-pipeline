# 紅茶流水線共通契約（v2）

入口、agent0 與 dispatch 讀本檔。執行角色只讀自己的劇本與派工資料，不必重讀整套引擎。

## 責任與呼叫順序

| 步驟 | 執行者 | 呼叫方式 | 輸出／下一步 |
|---|---|---|---|
| 釐清、規格、開票 | 主對話扮演 agent1 | Read `agents/agent1_plan.md`，依序 Read interview → spec → tickets | 使用者確認規格、UI 與政策 |
| 流程控制 | agent0-conduct | 主對話用 Agent 呼叫 | 讀狀態、派工、判關卡、寫報告 |
| Git、佇列、隔離工作區 | agent0 執行 dispatch skill | Read `skills/blacktea-dispatch/SKILL.md` | 一次一張工作項；唯一可改 Git 的執行者 |
| 實作／修復 | agent2-build | dispatch 用 Agent 呼叫 | 程式碼、測試、施工摘要 |
| 獨立票級檢查 | agent3-ticket-check | dispatch 在建造完成後用 Agent 呼叫 | PASS／FAIL／ENV_BLOCKED／NEEDS_REQUIREMENT |
| 全案／增量稽核 | agent3-review | agent0 在建造／修復整合後用 Agent 呼叫 | 發現與關卡結果 |
| 黑箱實測 | agent4-run | agent0 在稽核通過或明示降級後用 Agent 呼叫 | 旅程與視覺結果 |
| 復盤 | 主對話執行 retro command | 使用者 `/blacktea_retro` | 提案、批准後更新經驗包 |

所有路徑在呼叫前解析為絕對路徑。子 agent 不再派子 agent；只有 agent0 可以派執行角色。主對話在 agent0 執行期間不改專案或 Git。

## 資料來源

- `.pipeline/plan/01-requirements.md`：已確認的產品契約；技術細節可由建造者決定，但不得改對外契約。
- `.pipeline/plan/tickets.json`：工單唯一來源；`02-workplan.md` 與 HTML 是腳本產生的檢視版。不得手改檢視版或用勾選代替狀態。
- `.pipeline/state.json`：執行狀態唯一來源；只能用 `python3 ~/.claude/blacktea/scripts/pipeline.py --root <專案> ...` 更新。`state.md` 是自動產生的摘要。
- `<R>`：state 中本輪 `round_dir`。每次規格修訂都開新輪，包含交付前修訂；不以日期判版本。
- `git-policy.md`：GitHub 授權、remote URL、分支、可見性。`run-policy.md`：失敗處理、驗證深度及票級 Codex 驗證（預設開）。只沿用使用者已授權的內容。
- `waivers.md`：使用者明確接受的發現 ID、理由與範圍；不把未驗證改成 PASS。
- 經驗包只補充適用的實戰提醒，不能覆蓋產品契約、本協定、角色權限或使用者決定。

## 派工契約

每次 Agent prompt 必須帶：`mode`、`task_id`、`cwd`（本次工作區）、`project_root`、`round_dir`、`spec_revision`、規格章節／票位置、驗證範圍、證據輸出路徑。修復另帶發現 ID 與報告位置；稽核／實測另帶 baseline HEAD、受影響旅程及歷史發現索引。

角色回報：`result`、`task_id`、`summary`、`changed_files`、`evidence`、`reason`。只回摘要與路徑，不貼完整輸出。票級檢查 PASS 必須由檢查員產生綁定內容指紋的 receipt；dispatcher 不能代簽。

## 狀態與有限重試

工作項：`PENDING → BUILDING → CHECKING → VERIFIED → COMMITTED`。失敗可進 `FAILED`、`ENV_BLOCKED`、`NEEDS_REQUIREMENT`；尚未通過的內容留在隔離 worktree，主工作區只接收通過檢查的 commit。

| 結果／情況 | agent0 的動作 |
|---|---|
| 票級 FAIL | dispatch → agent2 修復 → agent3-ticket-check；初次之外最多重做 2 次 |
| ENV_BLOCKED（含無瀏覽器） | 不算程式 FAIL；派 agent2 做限定範圍的環境診斷，最多 2 次；仍不可用走政策出口 |
| NEEDS_REQUIREMENT | 不讓建造者猜；互動模式回主對話 agent1 補需求；無人值守用 `question --source <票/發現> --prompt <問題> --options <選項...>` 記未決 Q 並跳過相依工作 |
| 稽核 FAIL（未豁免 Critical／High） | dispatch 修復 → agent3-review 複審；每輪最多 3 次修復批次 |
| 實測 FAIL／阻擋交付的視覺問題 | dispatch 修復 → agent3-review 增量 → agent4-run 重測；每輪最多 2 次修復批次 |
| 無新證據或同原因連續失敗 | 不重派同樣指示；到上限走政策出口 |

計數只由腳本 `attempt` 增加，**派修復前**增加；計數鍵是 `ticket:<id>`、`env:<stage-or-task>`、`audit`、`e2e`。實測觸發的稽核歸 e2e 預算；視覺修復也算 e2e，不再有不計輪次的迴圈。context 續跑不重置計數。

互動模式：同樣先 question 記問題，再回 `NEEDS_USER`。主對話取得使用者答案後 `resolve --id <Q> --answer <答案>`；一般流程決策用 decision。問題記錄在 state.questions，不從自由文字猜是否已決。無人值守：保留失敗狀態、記決策、跳過受影響工作，繼續可獨立完成的部分；結案狀態為 `INCOMPLETE`，不是成功交付。未知情況不花錢、不猜產品契約；流程本身無法繼續時回 `NEEDS_USER`，不要假裝完成。

## 修訂與續跑

- 修訂票可用 `supersedes` 明確替代舊票；只有替代票 COMMITTED 才滿足原票的依賴。若只是補資料，更新原票並重新驗證；不能只新增 T-Rev 而遺留舊依賴。
- 新輪保留先前有效 commits、發現、waivers 與全旅程測試距離；受修訂影響的舊票重新開啟。不沿用與新版契約不符的 PASS。spec_revision 是規格內容雜湊；每張票另有 ticket_hash，修復票加入不改 spec_revision。
- 續跑先核對 state、worktree、receipt 與 Git。中斷在 commit 後：確認 commit 符合 receipt，再整合及記錄；中斷在驗證中：重新驗證。不得僅凭 `[x]` 跳過。
- 只在沒有執行中的角色、所有狀態已落地時讓 agent0 回 `CONTINUE`。主對話重新 spawn agent0，同一次命令最多 10 次；無進度就回原因。
- 舊版專案先讀 `~/.claude/blacktea/references/migration.md`；不直接覆蓋舊 state 或搬動證據。

## 結案

`COMPLETED`＝本輪必要票均 COMMITTED、必要稽核與實測均 PASS（可扣使用者指定 waiver；無實作票的純規格修訂可記有理由的實測 N/A）。跳過階段、缺能力、未完成票或驗證失敗均為 `INCOMPLETE`；報告首行列原因。

每輪寫 `<R>/` 的 build-log、ticket-checks、04、05；V／E／U ID 用腳本 `allocate`，Q 由 question 分配；全專案遞增。修復工作項 ID 用 `fix-<run>-<audit|e2e|overall>-<attempt>-<batch>`，不可省略來源。证據用工作項 ID＋檢查次數，舊檔不覆寫。

`output/reports/<run>-report.md` 寫本輪結果；`FINAL-REPORT.md` 只維護各輪索引、目前 open 發現、waivers 與待裁決事項。結果從結構化狀態整理；長輸出留證據檔。規格／報告的單 commit 不得夾帶程式碼。
