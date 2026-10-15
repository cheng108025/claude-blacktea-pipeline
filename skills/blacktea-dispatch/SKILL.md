---
name: blacktea-dispatch
description: 紅茶流水線派工與版控技能——Ready Queue→並行建造（≤3 隻）→每票票級檢查→PASS 才 commit／push；也做修復批次與單 commit。由 agent0-conduct 分身（階段二／修復輪／階段五／變更步驟 3–7）或 /blacktea_change 主對話（步驟 2 單 commit）Read 執行，不單獨使用。
user-invocable: false
disable-model-invocation: true
---

> 門牌：調度技能——不寫程式，只管派誰、何時派、收回來怎麼驗、怎麼 commit；整條流水線**唯一能碰 git 的人**。執行者通常是 agent0-conduct 分身（Read 本檔照做）。旋鈕（並行數、串行清單、重做次數、索引格式）與設計理由見 `~/.claude/README.md`。

# 你是調度員

你管佇列、派工、收結果、驗收、commit。**你自己不寫程式**（建造者做）、**不自己判定票有沒有做對**（票級檢查員做）。你多半跑在 agent0-conduct 分身裡——**不能問人**；需要使用者決定的事寫進摘要交回呼叫方。

## ① 輸入與模式（呼叫方會告訴你）

| 模式 | 做什麼 | 誰用 |
|---|---|---|
| **完整建造** | 工單上所有未完成（非 `[x]`）的票 | agent0 階段二 |
| **T-Rev 票清單** | 只做 `T-RevNN` 編號且未完成的票（呼叫方可附加派工紀律，會原樣轉達給建造者與票級檢查） | agent0 需求變更後、變更模式步驟 3 |
| **修復批次**（附發現清單＋報告位置） | 把發現按檔案分組派建造者修，修完票級檢查、commit | agent0 階段三／四退回、變更模式步驟 5 |
| **單 commit**（附檔案清單＋訊息） | 只做一次 commit（依政策 push），不派工 | 定稿、FINAL-REPORT、規格修訂 |

## ② 門禁與開工準備

1. **門禁**：`.pipeline/plan/02-workplan.md` 存在且已定稿（檔首沒有 DRAFT）。不符合 → 停，回報「工單尚未定稿」。單 commit 模式不查此門禁。
2. Read `~/.claude/skills/git/SKILL.md` 的 Part A（強制規則）。
3. 讀 `.pipeline/plan/git-policy.md`：
   - **存在** → 照它執行，**不要再問使用者**（訪談階段已經問過了）。
   - **不存在**（正常不會——訪談官 Phase 0 必問，`/blacktea_plan` 第 0 步開工前也會補問）→ 你跑在不能問人的分身裡，**不准自行建 repo 或 push**：寫一份 `git-policy.md` 記「上 GitHub 備份：否（預設，未問到使用者）」，全程只本機 commit，摘要與 FINAL-REPORT 提醒使用者「git 政策未問到，預設只留本機；要上 GitHub 請之後執行 /git」。
4. **repo 與首 commit**（還沒有才做）：
   - 沒有 `.git` → `git init`。
   - 沒有 `.gitignore` → 依工單 T01 票列的清單建立（至少含 `.env`、`node_modules/`、`.pipeline/rounds/`、`.pipeline/mcp-output/`、`.pipeline/evidence/`、`.pipeline/state.md`、`.pipeline/server.pid`、`.pipeline/03-build-log.md`、`.pipeline/build-log/`、`.pipeline/ticket-checks/`、`.pipeline/04-verify-report.md`、`.pipeline/05-e2e-report.md`）。
   - `.pipeline/plan/` 或 `.pipeline/output/*.html` 有未 commit 的變更（**不論是不是首 commit**——需求變更後重新定稿也算）→ 先用 ⑦ 單 commit 模式把 `.gitignore .pipeline/plan/ .pipeline/output/*.html .claude/settings.json .mcp.json`（存在的才加）commit 進去：首次訊息 `plan: 規格書與工單定稿`，需求變更後 `plan: T-RevNN 需求變更`（依政策 push），索引「其他 commit」節記一列。訪談官自己從不 commit，規格書入庫全靠這一步。
   - 政策為「上 GitHub 備份」且沒有 `origin` → `gh auth status`（沒登入 → 不卡流水線：照常 commit，push 標「延後」，最後摘要提醒使用者補推）→ `gh repo create <名稱> --private --source=. --remote=origin`（或 `--public`，照政策）。**建 repo 只有你能做。**
5. **工作單健檢**（不合格就不開工，回報「需求層級問題：工單結構不合格」由呼叫方走需求變更子流程）：主序列編號 T01..Tnn 連續不重複（`T-RevNN` 也合法；已列在 `.pipeline/plan/archive/INDEX.md` 的票一併算進來）；每個「依賴」指到的編號都存在（在 02 或 `archive/INDEX.md` 皆可，**在索引裡＝已完成**）；依賴能排出先後、沒有死結；每張票都有六欄。
6. **輪資料夾 `<R>`**（本檔與各角色檔凡寫 `<R>`＝state.md 檔首「目前輪資料夾」記的路徑；每票的施工紀錄、檢查紀錄、證據與 03／04／05 報告**全部放它底下**，`.pipeline/` 頂層只留 `plan/`、`output/`、`state.md`、`waivers.md`、`server.pid`）：
   - **命名**：`.pipeline/rounds/01`＝第一次生成（首次建造；交付前的需求變更與續跑都還是第 1 輪）；之後每跑一次 `/blacktea_change` 就多一個 `rounds/<NN>-T-RevNN`（NN＝前一輪＋1，例 `rounds/02-T-Rev01`、`rounds/03-T-Rev02`）。稽核輪次／實測輪次／修復輪次是**輪資料夾裡面**的計數，跟資料夾編號是兩回事。
   - **舊專案搬遷**：`.pipeline/rounds/` 不存在、但頂層有 `build-log/`、`ticket-checks/`、`evidence/`、`03-build-log.md`（含 `-legacy`）、`04-verify-report.md`、`05-e2e-report.md` 任一 → `mkdir -p .pipeline/rounds/01`，用 `mv` 把這些**全部**搬進去（都在 `.gitignore`，不用 `git mv`；索引與報告裡的相對路徑照舊有效），摘要告知使用者「舊產出已搬到 `.pipeline/rounds/01/`」。
   - **設定 `<R>`**：state.md 沒有「目前輪資料夾」→ 建案模式一律寫 `- 目前輪資料夾: .pipeline/rounds/01`；變更模式的值由 `/blacktea_change` 步驟 2 先寫好，沒寫就停，回報「變更輪資料夾未設定」。
   - 建立 `<R>/build-log/`、`<R>/ticket-checks/`、`<R>/evidence/`（不存在才建）；`<R>/03-build-log.md` 不存在或不是索引格式 → 依「⑧ 索引格式」建立（舊格式的先改名 `03-build-log-legacy.md` 保留）。

## ③ Ready Queue 與分道

1. **Ready Queue**：「依賴」全部已 `[x]`（＝已通過票級檢查並 commit；勾只有你會打）、且自己不是 BLOCKED／FAILED 的票進佇列。
2. **分道**：佇列內的票，按「做法」欄列出的異動檔案比對——檔案**無重疊** → 可並行，同時派**最多 3 隻** 🔧；檔案**有重疊** → 同一條道，照依賴／編號順序串行。
3. **強制串行清單** 🔧（不管重不重疊，永不並行）：動 `package.json`／lockfile 的票、資料庫 schema／migration 票、**驗證方式需要啟動 dev server 的票**（會搶 port）、動 `.pipeline/` 的票。**判斷不了會不會衝突 → 一律當作會衝突，串行。寧慢勿亂。**
4. 修復批次模式：把發現按「建議修法」涉及的檔案分組成最多 3 批，無重疊的批可並行，每批派一隻。

## ④ 派建造者

用 Agent 工具 spawn `agent2-build`（可背景執行，槽位一空就派下一張**不依賴在途票**的票），指示固定格式：

> ⚠ **派出去的子任務不會隨你終止**——你若在它回報前結束（context 用盡、被要求交回、額度中斷），它會變成孤兒：做完的事沒人收（下一棒看不到、整包白做），或與下一棒重派的那隻**並行改同一批檔案**。因此：**在途子任務未全部回報前不得交回**；真的必須交回時，先把在途清單與每隻的產出路徑寫進 state.md「建造進度」，並在回報裡明寫「有 N 隻在途、結果未知」。

> 單票模式：TXX。輪資料夾 `<R>`。不碰 git。施工紀錄寫 `<R>/build-log/TXX.md`，指令輸出存 `<R>/evidence/TXX-*.log`。回報時附完整異動檔案清單。

（指示裡的 `<R>` 要代成**實際路徑**，例 `.pipeline/rounds/01`——建造者與票級檢查員都以指示為準，不自己猜。）

修復批次的指示：

> 修復批次 第 <輪次> 輪 批次 <n>：依 `<04 或 05 報告路徑>` 修 V-xxx、V-yyy（附每項的重現情境與修法建議）。輪資料夾 `<R>`。不碰 git。紀錄寫 `<R>/build-log/fix-<輪次>-<n>.md`。回報時附完整異動檔案清單。

（<輪次>＝觸發報告檔首的稽核輪次或實測輪次；<n>＝本輪第幾批。）

呼叫方附加的紀律（如有，例如變更官的「不得呼叫耗額度的真實外部服務」）原樣接在指示末尾；同一段也附進該票的票級檢查指示。

## ⑤ 收票 → 票級檢查 → commit（串行，一次一張 🔧）

每收回一張票：

1. **核對檔案**：建造者回報的異動檔案清單 vs `git status --porcelain`——多出的檔案（不在清單、也不屬於其他在途票）→ 要求建造者說明，說不清就當偏離記進索引。`<R>/` 下的紀錄檔（`build-log/`、`ticket-checks/`、`evidence/`）不算多出的檔案。
2. **派票級檢查**：用 Agent 工具 spawn `agent3-ticket-check`（票級檢查員；模型由 `~/.claude/agents/agent3_ticket_check.md` 的 frontmatter 決定 🔧），指示固定格式：
   - 一般票：「票級檢查：TXX；輪資料夾 `<R>`；異動檔案：<清單>」（`<R>` 同樣代成實際路徑，下面兩種也是）
   - 修復批次：「票級檢查：修復批次 第 <輪次> 輪 批次 <n>；發現 V-xxx、V-yyy（報告 `<04/05 路徑>`）；受影響票：TXX、TYY（你依異動檔案對照各票「做法」欄找出）；異動檔案：<清單>；紀錄寫 `<R>/ticket-checks/fix-<輪次>-<n>.md`」
   - 整體檢查修正：「票級檢查：整體檢查修正；異動檔案：<清單>；紀錄寫 `<R>/ticket-checks/overall-check.md`」

   要順帶品質檢查就在指示末尾加「順帶品質檢查」🔧（預設不加，全案稽核再做）。票級檢查員會親自重跑該票的驗證方式、逐條驗 DoD、跑測試，寫紀錄。票級檢查**一次只跑一隻** 🔧（它可能會起 dev server）。
3. 讀 `<R>/ticket-checks/TXX.md`（修復批次：`fix-<輪次>-<n>.md`；整體檢查修正：`overall-check.md`）的結論：
   - **PASS** → 先在 `02-workplan.md` 該票那一行打 `[x]`（只改那一行；勾只有你會打）→ 從異動清單剔除被 `.gitignore` 擋住的路徑（`<R>/` 底下的 `build-log/`、`ticket-checks/`、`evidence/`，留著會讓 `git add` 回 exit 1）→ `git add <該票的異動檔案清單> .pipeline/plan/02-workplan.md`（**禁用 `git add -A`／`git add .`**——並行時工作區有別票的半成品）→ commit，訊息帶票號（例：`T03: 使用者登入 API`；修復批次：`fix round 2: V-003 V-007`）→ 政策為「上 GitHub 備份」且 push 未暫停 → 先跑機密掃描（git skill 的三條指令）→ `git push`；**掃到東西 → 不推、不問、不卡**：本機 commit 保留，state.md 記「push 暫停：機密掃描命中 <檔案／樣式>（TXX 起）」，**之後所有票也一律不推**（推了等於把那個 commit 一起推上去），流水線照常繼續；最後摘要與 FINAL-REPORT 列出命中內容，由使用者事後處理（移除機密、改寫歷史或決定照推）。索引表更新該列；修復批次另在索引「修復輪次」節記一列（第 N 輪＝觸發報告檔首的輪次）。
   - **FAIL** → 確認 `02-workplan.md` 該票仍是 `[ ]`（建造者若誤打勾就改回）→ spawn `agent2-build`「單票修復：TXX，輪資料夾 `<R>`，依 `<R>/ticket-checks/TXX.md` 的 FAIL 項」→ 回來再派一次票級檢查。修復批次的票級檢查 FAIL → 再派一次「修復批次」，指示加「依 `<R>/ticket-checks/fix-<輪次>-<n>.md` 的 FAIL 項只修這些」。**每票（每批）最多重做 2 次** 🔧；第 2 次仍 FAIL → 索引標 **FAILED**（不 commit、保持 `[ ]`），跳過所有依賴它的票，最後統一回報。建造者提出可重現反證 → 轉給票級檢查員複驗，檢查員判定為準。
   - **INCONCLUSIVE**（檢查員判定失敗來自本票異動清單之外、屬於其他在途票的檔案）→ 等該批在途票全部收回後重跑一次票級檢查，不佔 2 次額度。
   - **BLOCKED**（建造者回報卡住）→ 索引標 BLOCKED，跳過依賴它的票，最後統一回報（屬需求缺漏 → 呼叫方走需求變更子流程）。
4. 更新 `state.md` 的「建造進度」節（⑨）。

## ⑥ 迴圈與收尾

1. 回到 ③，直到佇列清空（或只剩被 BLOCKED／FAILED 擋住的票）。
2. **整體檢查**：派最後一隻 `agent2-build`「整體檢查」跑 install → build → test（輸出存 `<R>/evidence/overall-check.log`）；它若為了轉綠改了檔，照 ⑤ 走一次票級檢查（指示格式見 ⑤-2「整體檢查修正」）再 commit（訊息 `chore: 整體檢查修正`）。
3. 政策為「上 GitHub 備份」且 push 未因機密掃描暫停 → 最後再 `git push` 一次收尾，把過程中延後（gh 未登入等）的 commit 補推；補不了就在摘要明說還差幾個。push 已暫停 → 不推，摘要明說原因與從哪張票起沒推。
4. **摘要**給呼叫方（它會轉述給使用者）：完成票數／總數、並行了幾隻、分幾道；票級檢查 N/N PASS、被退回重做的票與次數；BLOCKED／FAILED 清單（各一句話卡點，引用 ticket-checks 檔）；偏離事項數；整體檢查結果；**版控狀態逐票列出**（例：`T01–T07 已 commit 並推上 origin/main；T08 commit 完成但 push 延後：gh 未登入`）、commit 總數、repo 網址。

## ⑦ 單 commit 模式

呼叫方給檔案清單與訊息 → `git add <清單>`（同樣禁用 `-A`／`.`）→ commit → 政策為是 → 機密掃描 → push → 在索引「其他 commit」節加一列。沒有 repo 時先做 ②-4。

## ⑧ `<R>/03-build-log.md` 索引格式 🔧

由你維護；**一個輪資料夾一份索引**（路徑欄是相對於 `<R>/` 的相對路徑）；建造者只寫自己的分檔，不動索引。

```markdown
# Build Log（索引）
> 開工時間：… ／ 工作單版本：<02 檔首定稿日期> ／ 模式：逐票派工（並行上限 3）

## 工作單結構檢查
（通過 ／ 不合格：逐條列出具體缺陷）

## 票索引
| 票 | 狀態 | commit | 異動檔案數 | 票級檢查 | 偏離 | 分檔 |
|---|---|---|---|---|---|---|
| T01 | ✅ | a1b2c3d | 3 | PASS（第 1 次） | 0 | build-log/T01.md |
| T04 | ✅ | d4e5f6a | 5 | PASS（第 2 次：第 1 次 FAIL→單票修復） | 1 | build-log/T04.md |
| T07 | ⛔ BLOCKED | — | — | — | — | build-log/T07.md |
| T09 | ❌ FAILED | — | 4 | FAIL×2（ticket-checks/T09.md） | 0 | build-log/T09.md |

## 派工波次
W1：T01 ｜ W2：T02＋T05＋T08（並行）｜ W3：T03 …

## BLOCKED／FAILED
（無 ／ 逐條：票號、一句話卡點、影響的依賴票）

## 修復輪次
### 第 1 輪（依 04-verify-report.md）
- 批次 1：V-003 V-007 → commit b2c3d4e（票級檢查 PASS）→ 分檔 build-log/fix-1-1.md
- V-005 → 建造者反證，交稽核員複驗

## 整體檢查
install ✅ ／ build ✅ ／ test ✅（evidence/overall-check.log）

## 其他 commit
- plan: 規格書與工單定稿 → 9f8e7d6
- docs: FINAL-REPORT → …
```

稽核員判「複審輪」的雙條件之一就是這裡的「修復輪次」節有紀錄——不要省略。

## ⑨ state.md「建造進度」節（每派一票、每收一票都更新）

```markdown
## 建造進度（blacktea-dispatch 維護）
- 輪資料夾：.pipeline/rounds/01
- 佇列：T06 T07
- 在途：T04（建造中）、T05（建造者已回報，票級檢查中）
- 已 commit：T01 T02 T03
- FAILED／BLOCKED：（無）
```

續跑（中斷後再進來）時，**照這個順序**：

1. **先確認上一棒有沒有留下仍活著的子任務**（`ListAgents`；或看「在途」清單對應的 `<R>/build-log/`、`<R>/ticket-checks/` 檔案 mtime 還在長、`git status` 的異動清單自己在變、`git diff` 每次看都不一樣）。有 → **等它回報或確認已終止，才動同一批檔案**；不得逕行重派（會變成兩隻同時改同一批檔案）。
2. 在途票的產出檔不存在或不完整 → 重派那一張。
3. 工作區有未 commit 的變更 → 對照「在途」清單，對那些票重新派票級檢查，PASS 才 commit；不重派已 `[x]` 的票。

## ⑩ Context 保險絲

收到 context 即將不足的提示 → 不硬撐：把手上這張票走完 ⑤（commit 或標 FAILED）、更新 state.md 與索引，**然後停下來**把目前進度交回呼叫方（agent0 會以「續跑」狀態回報，主對話再 spawn 一隻新分身接手；新分身依 ⑨ 的續跑規則接著派）。不繼續派下一張、不叫使用者開新對話。斷點只落在「票已 commit」，不落在建造中或檢查中。

# 鐵律

- **git 只有你一個人動**：建造者不准執行任何 git 指令；稽核員與票級檢查員只准用唯讀指令（`git status`／`diff`／`log`／`rev-parse`），不准 add／commit／push／checkout／stash；你也不准在票級檢查 PASS 之前 commit 任何票。
- **`gh repo create` 只有你能做**——建 repo 牽涉私有／公開與命名，是使用者的決定。
- **push 的授權只來自 `git-policy.md`**：政策記「上 GitHub 備份：是」＝使用者已預先授權（見 `~/.claude/skills/git/SKILL.md` 規則 2 的預先授權例外），照著推不算越權，**中途不准再問使用者**。政策記「否」→ 全程只 commit，完全不碰 GitHub。
- **force push、推 tag、推到別的 remote、把 repo 改公開 → 授權不涵蓋，一律停下來交回呼叫方問使用者。**
- **push 前一律先跑機密掃描**（git skill「push 前的敏感檔檢查」）；掃到東西**絕對不推**——暫停本次與之後所有 push、本機照常 commit、流水線繼續，最後一次性回報給使用者處理（使用者 2026-08-23 決定：不推就不會外洩，不必中途打斷）。
- `gh auth status` 失敗 → 不要卡住整條流水線：照常 commit，把 push 標記為「延後」，最後摘要時告訴使用者要補推。
- 每票一個 commit 的紀律不變——稽核員的增量複審靠 `git diff` 找變更範圍。
- 已 `[x]` 的票不重派；判斷不了會不會衝突的票一律串行。
