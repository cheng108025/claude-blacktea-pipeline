# agent0 執行流程

共通契約見 `~/.claude/blacktea/protocol.md`。以下步驟適用 build／change／amend；模式只改變選票與驗證範圍。

## 0. 開工或續跑

1. 確認產品規格與 tickets.json 已定稿，讀 git-policy、run-policy。舊版先遷移。
2. 首次先 `pipeline.py --root <專案> init`（舊版先遷移）；Read dispatch，做 plan 單 commit（只限規格、票、HTML、忽略清單與使用者已確認的專案模板）。
3. 新規格 `new-run --mode <build|change|amend> --label <可選T-RevNN>`。spec_revision 由 requirements 內容雜湊產生；每個在途票另綁定其票面雜湊。同一輪續跑使用既有 run，不呼叫 new-run。即使規格正文沒改，新的修訂票／reopen 也要新輪；已結案的無工作請求不要開空輪。
4. 新輪傳 `--tasks T01 T02 ...` 指定本輪必要工作項；純規格／文件決策且無實作變更的 change 可不帶 --tasks，直接進稽核；reopen 的舊票也列入。腳本保留其他已完成票；新輪不繼承失敗重試數。前輪執行中的角色必須先全部回收。
5. 從 state 取得 R、run_id、各階段计數、未決問題；只有 script 更新 state.json，phase 用 `phase --name <build|audit|e2e|report> --status RUNNING`。

## 階段二：建造 → agent2 → agent3-ticket-check

執行 dispatch 的 build 模式。每張票串行：隔離 worktree → agent2 → agent3-ticket-check → receipt 校驗 → commit → fast-forward 整合 → state COMMITTED。

所有必要票完成才進稽核。失敗按共通出口處理；無人值守跳過的票及相依票列入 omissions，繼續獨立項目。修訂替代票完成後，重新計算原相依票是否可執行，不把舊 BLOCKED 永久留在佇列外。

## 階段三：稽核 → agent3-review

- 首次建案／舊版遷移：full。change／amend／修復：incremental，基準是此次 plan commit；若基準缺失或影響範圍不明，升 full。
- 派工前 `allocate --kind V --count <需要數>` 可先保留 ID 區間；也可讓稽核員先回臨時 ID，再由你統一映射。歷史上限只由 state 管，不從前一份報告猜。
- 首輪做 install/build/test 與必要啟動驗證。小修只跑受影響檢查；共享契約、依賴、資料庫或 build 設定改動需全套。沒有測試也記明，不拿「零測試」當功能證據。
- 每次收回稽核結果，先 `record-check --stage audit --result <結果> --evidence <04絕對路徑>`。agent3 回 PASS：進實測。FAIL：`attempt --key audit --limit 3`，再 dispatch 修復、agent3 複審。只有 agent3 可關閉 V。
- Medium／Low 預設列已知限制；只有產品驗收必要或 run-policy 指定才修，不因數量觸發重做。
- ENV_BLOCKED／NEEDS_REQUIREMENT 走共通出口。無人值守選擇帶 open 項前進時，通知實測員相關旅程為已知缺口；不重複修同一個跳過項。

## 階段四：實測 → agent4-run

build、遷移、共享契約／資料模型的大改做 full；其他 change 做影響旅程。連續兩次增量後下一次 full（state 的 incremental_since_full）；只有完整實測 PASS 才歸零。

- 每次收回實測結果，先 `record-check --stage e2e --result <結果> --evidence <05絕對路徑>`。PASS → report；`record-e2e --scope full|incremental --result PASS` 保存範圍與結果。
- FAIL／阻擋交付的 U → `attempt --key e2e --limit 2` → dispatch 修復 → agent3 增量複審 → agent4 重測。這一鏈都屬同一次 e2e 修復，不加 audit 計數；仍失敗就消耗下一次 e2e，不能在中間開無上限稽核迴圈。
- 共享元件或修復影響不明時全旅程重測；否則受影響旅程＋相關回歸。舊旅程不能冒稱本輪重測。
- ENV_BLOCKED：`attempt --key env:e2e --limit 2`，agent2 診斷隔離環境；恢復才重派 agent4。修不了走政策出口。
- E／U 由 agent4 確認 closed；新發現用 allocate，維護 `.pipeline/findings.md` 索引。

纯規格變更且沒有實作票：agent3 確認與現狀一致後，可 `record-check --stage e2e --result N/A --reason <不需實測的依據> --evidence <本輪說明>`；這不是跳過本來必要的實測，不增加增量計數。若新契約須重新操作才可確認，仍派 agent4。

## 階段五：報告與收尾 → agent0／dispatch

1. 整理本輪必要票、實際檢查範圍、Git 狀態、open 發現、waivers、未驗項目與決策。未完成／未跑／跳過必須在首行明示。
2. 寫 `output/reports/<run_id>-report.md`；更新 FINAL-REPORT 索引與當前 open 限制，不重複貼每輪全文。證據連結用真實路徑，提供啟動方式。
3. dispatch docs 單 commit 只收報告。必要票與檢查均通過才 `phase --name report --status COMPLETED`；否則 INCOMPLETE 並帶 `--reason`。失敗也生成報告，不把「跑完流程」當作成功。
4. 回報主對話。未決 Q 在後續 change 一次處理；只接受限制的決策更新報告，不偽造 PASS。

## 外部覆核

`run-policy.md` 記 `external_review: off|plan|code|both`，預設 off；首次詢問時說明會使用外部工具。state 的 `external_reviews` 記完成與失敗嘗試，每個 plan/code 槽全專案最多一次，重試須使用者再授權。code 覆核指示 agent3 先 `external-review --kind code` 登記嘗試，再以唯讀模式呼叫；缺工具標未執行，不阻塞。禁止單憑安裝了 Codex 就自動呼叫。

票級 Codex 驗證是另一件事：run-policy「票級 Codex 驗證: 開」（預設）時，dispatch 在每次票級檢查 prompt 加「Codex 驗證」，由檢查員對該票呼叫一次；不佔 external_reviews 槽，失敗照實記錄、不阻塞。

## 指定階段與恢復

指定階段二需 FINAL 工單；階段三需本輪必要票完成或有政策 omissions；階段四需有效稽核 PASS 或明示降級；階段五需各必要檢查已有結果或有明示未完成原因。不符合就回具體缺項，不默默跳過。使用者明說跳過稽核／實測時，在本輪寫說明並 record-check 為 SKIPPED，結案 INCOMPLETE。

state.phase 已在後續階段时，从該階段續跑；不要重做已完成建造。若檢查後程式內容變動，舊結果無效，重驗受影響階段。每次返回都依目前 phase 與本輪預算，不另造一套變更模式輪次。
