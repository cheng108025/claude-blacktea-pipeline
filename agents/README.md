# agents/——六個角色，一人一檔（含引擎設計說明）

> 此檔只給人看，Claude 不會把它當指示執行。設計理由、呼叫關係、所有 🔧 旋鈕、守門規則都在本檔；使用者怎麼用見 `~/.claude/README.md`。

> **寫作分工**：執行檔（`agents/`、`skills/`、`commands/`）寫給 AI——第二人稱、一件事只說一次、條件可判定，檔頭只留 2–3 行「門牌」（我是誰、誰呼叫我）；設計理由、呼叫關係、所有 🔧 旋鈕都只寫在本檔（與 `skills/README.md`）。檢驗法：一句話刪掉後 AI 的行為不會變，它就屬於 README。

六個角色與三個入口都依專案 `run-policy.md` 及 `blacktea/runtime-contract.md` 工作。共通契約統一政策優先序、查歸檔票、規格版本、跨輪編號、隔離驗證、服務歸屬與收尾；角色檔只補各自的操作步驟。

| 檔案 | 角色 | 是不是 subagent | 模型 | 誰召喚它 |
|---|---|---|---|---|
| `agent0_conduct.md` | 總指揮分身：在乾淨 context 裡跑階段二～五（建造→稽核→實測→FINAL-REPORT）或變更步驟 3–7；**關卡、回退、失敗出口規則全在它自己檔裡**；自己再 spawn 建造者／票級檢查員／稽核員／實測員；只回報完成／續跑／需使用者決定 | 是（`name: agent0-conduct`） | opus | `/blacktea_plan` 第 0 步與「監督迴圈」；`/blacktea_change` 步驟 2 之後（變更模式） |
| `agent1_plan.md` | 訪談官：把你的一句話問到零模糊，寫規格書、拆工單 | **不是**（刻意沒有 `name`） | 跟主對話（由你 `/model` 選的 session 模型決定） | `/blacktea_plan` 階段一用 Read 照做 |
| `agent2_build.md` | 建造者：一次做一張票，跑驗證方式，回報 | 是（`name: agent2-build`） | sonnet | `skills/blacktea-dispatch` ④ |
| `agent3_ticket_check.md` | 票級檢查員：一張票做完後獨立重跑驗證方式、驗 DoD、跑測試、核對檔案，回 PASS／FAIL／INCONCLUSIVE；PASS 才 commit | 是（`name: agent3-ticket-check`） | sonnet | `skills/blacktea-dispatch` ⑤ |
| `agent3_review.md` | 稽核員：全案稽核（能不能跑、bug、資安、架構對照、品質） | 是（`name: agent3-review`） | opus | agent0 階段三、變更步驟 4 |
| `agent4_run.md` | 實測員：真瀏覽器黑箱實測全部旅程 | 是（`name: agent4-run`） | sonnet | agent0 階段四、變更步驟 6 |

## 為什麼訪談官沒有 name

subagent 沒有 `AskUserQuestion` 工具——被召喚出去的分身中途不能問任何人。訪談官整個工作就是問你問題，所以它必須跑在主對話：總指揮用 Read 把 `agent1_plan.md` 讀進來照著做。官方規則是「agents/ 裡沒有 `name` 的檔案視為放在旁邊的文件，不註冊」，所以這個檔刻意不放 `name`。**不要幫它補上**，補了它會變成一個不能問人的分身。

## 為什麼票級檢查員跟稽核員分開

票級檢查是「照票面重跑驗證、對答案」的機械活，每張票至少跑一次；全案稽核是逐檔抓漏的判斷力活，一案只跑幾輪。原本票級檢查由稽核員兼任，每次 spawn 都載 14 KB 的稽核員人設＋預載技能、用 opus——拆開後票級檢查只載約 7 KB、用 sonnet。覺得檢查不夠嚴，把 `agent3_ticket_check.md` 的 `model` 改成 opus 即可，不要再合回去。

## 改這裡的檔案要注意

- 五個分身的 `name` 不能改：`skills/blacktea-dispatch`、`commands/blacktea_plan.md`、`commands/blacktea_change.md`、`agents/agent0_conduct.md` 都用這些名字召喚。
- `agent0_conduct.md` 是階段二～五與變更步驟 3–7 的**唯一**規則來源——想改建造／稽核／實測的串接、關卡、回退，改這裡；`commands/` 只剩主對話的分流與監督迴圈。subagent 巢狀深度官方預設上限 3 層（主對話 → agent0 → agent2/3/4），剛好夠用；**不要讓 agent0 再 spawn agent0**。
- `agent3_review.md` 的 `skills:` 預載 `agent3-quality-check`——被預載的 skill 只能設 `user-invocable: false`，不能設 `disable-model-invocation: true`（設了就預載不進來）。
- agent 檔的 markdown 全文會成為分身的 system prompt，**每次 spawn 都付一次**——不要在裡面寫解釋、設計理由或旋鈕表，那些放 README。
- 改完在 `~/.claude` commit（agents／skills 會自動重載，不用重啟）。六個角色的施工／檢查紀錄都寫進專案的 `.pipeline/`，角色之間靠檔案交接，不靠對話。

---

## 誰呼叫誰（一張圖）

```
你 ─/blacktea_plan─▶ 總指揮（主對話，commands/blacktea_plan.md）
  階段一  Read agents/agent1_plan.md ─▶ Read skills/agent1-interview ─▶ agent1-spec ─▶ agent1-tickets ─▶ 你看 HTML 點頭 ─▶ 定稿 ─▶ 停：請你開新對話
你 ─/blacktea_plan（新對話，不帶參數）─▶ 總指揮讀 state.md ─▶ spawn agents/agent0_conduct（總指揮分身，乾淨 context；規則在它自己檔裡）
                                          主對話只監督：分身回「續跑」就再 spawn 一隻接手；回「需使用者決定」才問你；回「完成」就轉述
  （以下都在分身裡跑；「做不下去」先查 run-policy.md：無人值守→照預設動作記錄後繼續，遇事停下來問→回報主對話問你）
  階段二  Read skills/blacktea-dispatch ─▶ spawn agents/agent2_build（最多 3 隻並行，一票一隻）
            每收一票 ─▶ spawn agents/agent3_ticket_check「票級檢查 TXX」─▶ PASS 才 commit／push
            FAIL ─▶ 建造者單票修復（最多 2 次）
  階段三  spawn agents/agent3_review「全案稽核」：能不能跑（＋核對每票都有票級 PASS）、Bug、資安、架構對照、品質（skills/agent3-quality-check）、Codex
            FAIL ─▶ dispatch 修復批次 ─▶ 複審（上限 3 輪）
  階段四  spawn agents/agent4_run 全旅程瀏覽器實測（上限 2 輪）
  階段五  分身寫 FINAL-REPORT ─▶ 主對話提醒 /blacktea_retro
你 ─/blacktea_change─▶ 變更官（主對話）：釐清、改規格開 T-Rev 票、單 commit ─▶ spawn agents/agent0_conduct（變更模式）─▶ 主對話監督
                        （分身裡）dispatch 建造 ─▶ 稽核員增量 ─▶ 修復 ─▶ 實測員增量實測 ─▶ 寫本輪報告 output/reports/<輪名>-report.md ＋ FINAL-REPORT 總覽加列
```

交接靠 `.pipeline/` 裡的檔案，不靠對話：`plan/01-requirements.md`（規格書）、`plan/02-workplan.md`（工單）、`plan/ui-prototype.html`（外觀契約，有畫面才有）、`plan/git-policy.md`、`plan/run-policy.md`（無人值守政策）、`state.md`（檔首「目前輪資料夾」）、`waivers.md`、`output/FINAL-REPORT.md`（總覽：各輪報告表＋累積已知限制）、`output/reports/<輪名>-report.md`（每次生成一份：`01-report.md`、`02-T-Rev01-report.md`…）；**每一次生成一個輪資料夾** `rounds/<NN>/`（`01`＝首次建造，每跑一次 `/blacktea_change` 多一個 `02-T-Rev01`、`03-T-Rev02`…），裡面才是 `03-build-log.md`（索引）＋`build-log/TXX.md`（每票施工紀錄）、`ticket-checks/TXX.md`（每票檢查紀錄）、`04-verify-report.md`、`05-e2e-report.md`、`evidence/`。各角色檔用 `<R>` 指本輪資料夾；舊專案平放在 `.pipeline/` 頂層的產出，調度技能開工時會自動搬進 `rounds/01/`。

---

## 想調整什麼 → 去哪個檔

| 想調整什麼 | 檔案 | 段落 |
|---|---|---|
| **訪談** | | |
| 資料夾放哪、放什麼；專案腳印 | `agents/agent1_plan.md` | Phase 0「建立資料夾與專案腳印」 |
| Git 政策怎麼問 | `agents/agent1_plan.md` | Phase 0「Git 版控政策」 |
| 無人值守時各種「做不下去」的預設動作 | `agents/agent1_plan.md` | Phase E「2.5 無人值守政策」 |
| HTML 檢視版的樣式與內容 | `agents/agent1_plan.md` | Phase E「產出 HTML 檢視版」 |
| 每輪問幾題、題目能不能綁同一輪、最多幾輪 | `skills/agent1-interview/SKILL.md` | 「訪談規則」第 1 條／第 2 條／最後一條 |
| 門檻分數、評分表面向、哪些必滿分 ★ | `skills/agent1-interview/SKILL.md` | 「門檻」、「評分表」 |
| 問題要問得多詳細 | `skills/agent1-interview/SKILL.md` | 「每一題的標準構成」 |
| 執行方式（本機 vs Docker）怎麼問、選 Docker 要補問什麼、預設 | `skills/agent1-interview/SKILL.md` | 「訪談規則」→ 必問題——執行方式攤牌 |
| 技術棧攤牌那一輪表格有哪幾列、什麼時候問 | `skills/agent1-interview/SKILL.md` | 「訪談規則」→ 必問題——技術棧攤牌 |
| 規格書「執行方式」小節要寫什麼（Docker 的映像、port、volume、機密） | `skills/agent1-spec/SKILL.md` | 「章節菜單」4 |
| 容器化票做什麼、Docker 專案的驗證配方 | `skills/agent1-tickets/SKILL.md` | 「工作單的組成」2c、「每張 ticket 的品質要求」→ 驗證指令 |
| 視覺定調問哪四題、三種風格原型、預設 | `skills/agent1-interview/SKILL.md` | 「訪談規則」→ 必問題——視覺定調 |
| 設計系統章要有哪幾段（token、狀態矩陣、元件清單） | `skills/agent1-spec/SKILL.md` | 「章節菜單」7b |
| 設計系統基座票做什麼、UI 票三條硬規定 | `skills/agent1-tickets/SKILL.md` | 「工作單的組成」2b、「每張 ticket 的品質要求」 |
| UI 原型怎麼做、放哪 | `agents/agent1_plan.md` | Phase E「產出 HTML 檢視版」 |
| 規格書要有哪些章、技術棧表；哪些章不可省 | `skills/agent1-spec/SKILL.md` | 「章節菜單」、「五個必備章」 |
| ticket 要拆多小、六欄長怎樣 | `skills/agent1-tickets/SKILL.md` | 「每張 ticket 的品質要求」、「Ticket 格式」 |
| T01 做什麼、.gitignore 擋什麼 | `skills/agent1-tickets/SKILL.md` | 「工作單的組成」第 2 條 |
| 交棒前自我稽核 7 項、待問清單追問幾輪 | `skills/agent1-tickets/SKILL.md` | 「自我稽核」（第 7 項） |
| 要不要用 Codex 當第二雙眼睛、分級 | `skills/agent1-tickets/references/codex-review.md` | 全檔 |
| **建造** | | |
| 同時派幾隻建造者、哪些票永遠不並行 | `skills/blacktea-dispatch/SKILL.md` | ③ |
| 票級檢查一次跑幾隻、每票重做幾次 | `skills/blacktea-dispatch/SKILL.md` | ⑤ |
| 輪資料夾 `rounds/<NN>` 怎麼命名、舊專案怎麼搬 | `skills/blacktea-dispatch/SKILL.md` | ②-6 |
| 建造進度只維護一段、每票基準 SHA 與檔案擁有權 | `skills/blacktea-dispatch/SKILL.md` | ④、⑧、⑨ |
| 文件殘留自查與獨立覆核 | `agents/agent2_build.md`、`agents/agent3_ticket_check.md` | Step 2-2b、怎麼檢查 5a |
| 重建改動前紅燈、新建檔案、隔離變異 | `blacktea/runtime-contract.md`、`agents/agent3_ticket_check.md` | 隔離驗證與紅燈重建、測試先行核對 |
| build-log 索引長什麼樣 | `skills/blacktea-dispatch/SKILL.md` | ⑧ |
| 建造者用哪顆模型 | `agents/agent2_build.md` | frontmatter `model` |
| 建造者的編碼守則（資安／可維護／前端／測試先行）、健康檢查等多久、server 配方 | `agents/agent2_build.md` | 「編碼守則」、「Linux 指令慣例」 |
| build-log 分檔要記什麼 | `agents/agent2_build.md` | 「附錄」 |
| 票級檢查用哪顆模型、紀錄每段字數 | `agents/agent3_ticket_check.md` | frontmatter、「寫紀錄」 |
| 票級檢查要不要加 Codex 交叉驗證（每票多呼叫一次 `codex exec`） | 開工前問使用者，存 `.pipeline/plan/run-policy.md`「票級 Codex 驗證」；問法 `agents/agent1_plan.md` 2.5；派工 `skills/blacktea-dispatch/SKILL.md` ⑤-2；做法 `agents/agent3_ticket_check.md` 步驟 8 | 欄位 開／關 |
| 票級檢查要不要順帶品質檢查 | `skills/blacktea-dispatch/SKILL.md` | ⑤-2（在指示末尾加「順帶品質檢查」） |
| **稽核** | | |
| 稽核員用哪顆模型 | `agents/agent3_review.md` | frontmatter `model` |
| 稽核多嚴、嚴重度基準、資安 8 條 | `agents/agent3_review.md` | 「關卡判定」、「嚴重度基準」、Step 5 |
| Codex 第二意見何時跑 | `agents/agent3_review.md` | 「外部覆核」 |
| 品質檢查查什麼、各算什麼嚴重度、想讓某類擋關 | `skills/agent3-quality-check/SKILL.md` | 「清單」、「嚴重度對照」 |
| **實測** | | |
| 實測員用哪顆模型 | `agents/agent4_run.md` | frontmatter `model` |
| 實測旅程三層、惡意輸入後備測法 | `agents/agent4_run.md` | Step 3 |
| 視覺檢查表、U 編號類別 | `agents/agent4_run.md` | Step 4b |
| 幾件視覺發現才先修再結案（5）、哪類算破版 | `agents/agent0_conduct.md` | 建案模式「階段四」去向 |
| 伺服器啟動等多久、證據命名 | `agents/agent4_run.md` | Step 2、Step 4 |
| **流程** | | |
| 建案／變更共同歸檔、重跑不重複、報告與歸檔同 commit | `blacktea/runtime-contract.md`、`agents/agent0_conduct.md` | 完工歸檔、階段五／步驟七 |
| 專案政策優先序、測試服務歸屬、修復批次命名 | `blacktea/runtime-contract.md` | 政策、服務生命週期、修復批次識別 |
| 同日規格版本、執行／額度次數與增量範圍、跨輪取號 | `blacktea/runtime-contract.md` | 規格版本與關卡計數、報告搜尋與發現編號 |
| 復盤增量範圍、完成後推進檢查點 | `commands/blacktea_retro.md` | Step 1、Step 7 |
| 掃描所有待推 commit、刪除機密後仍會攔、掃描出錯不放行 | `skills/git/SKILL.md`、`blacktea/scan-push.py` | push 前的敏感檔檢查 |
| 稽核退回上限（3）、實測退回上限（2）、跳過階段 | `agents/agent0_conduct.md` | 建案模式「階段三」「階段四」「跳過階段」 |
| 變更的修復輪上限（3）、什麼嚴重度要在實測前修、幾輪後改全旅程實測 | `agents/agent0_conduct.md` | 變更模式「步驟 5」「步驟 6」 |
| 總指揮分身用哪顆模型 | `agents/agent0_conduct.md` | frontmatter `model` |
| 分身續跑上限（10）、工單定稿後要不要強制換新對話 | `commands/blacktea_plan.md` | 「監督迴圈」、「階段一」末段 |
| 經驗包每段幾條、教訓取捨標準、改引擎的門檻 | `commands/blacktea_retro.md` | 「寫入規則」、「什麼值得記」、「例外」 |
| 匯入別人經驗包時哪些條目一律剔除 | `commands/blacktea_retro.md` | 匯入模式 → 安全過濾 |

每個執行檔開頭只有 2–3 行「門牌」；檔內的 🔧 標記對應上表。

---

## 不要放寬的守門規則（與所在檔）

- 規格書禁止「待定」；同一輪題目彼此獨立；每輪 ≤4 題；最多 8 輪；總分 ≥9.0 且 ★ 滿分才寫規格書 —— `agents/agent1_plan.md`、`skills/agent1-interview/`
- 工單 DRAFT 就不准開工 —— `skills/blacktea-dispatch/`
- 有畫面的專案：「設計系統」章必備、UI 原型要使用者明確說「外觀可以」才定稿、設計系統基座票在所有 UI 票之前、UI 票 DoD 必含視覺驗收（狀態矩陣每格＋與原型對照＋截圖） —— `skills/agent1-spec/`、`agents/agent1_plan.md`、`skills/agent1-tickets/`
- 建造者禁止猜需求（標 BLOCKED）、永不碰 git、票級檢查不得自判 —— `agents/agent2_build.md`
- 票級檢查員不讀 build-log 當證據、不信任建造者回報；每票 PASS 才 commit —— `agents/agent3_ticket_check.md`
- 票面有測試清單：先紅後綠；檢查員用固定派票 SHA 在隔離副本重建行為紅燈／變異，新檔與未追蹤檔也核對，不覆寫正式程式。修復批次要有回饋迴圈、回歸測試；除錯清零只掃程式範圍 —— `blacktea/runtime-contract.md`、建造者／票級檢查員
- Git 寫入只有調度技能執行；`gh repo create` 只有它能做；push 授權只來自 `git-policy.md`；force push／推 tag／改公開一律先問；push 前機密掃描 —— `skills/blacktea-dispatch/`、`skills/git/`
- 每票過票級檢查 PASS 才 commit；每票最多重做 2 次；機密掃描命中 → 暫停之後所有 push、繼續 commit、最後回報（不中途問） —— `skills/blacktea-dispatch/`
- 稽核發現全部列出、親自重現才關閉；Medium／Low 允許總指揮依規則親自核對關閉。V／E／U 從全域最大值續編，Critical=0 且 High=0 才 PASS；豁免仍只由使用者授權 —— `agents/agent3_review.md`、共通契約
- 稽核退回上限 3 輪、實測退回上限 2 輪、agent4 退回不佔額度、需求層級問題回使用者（無人值守下也不准猜，只能標 BLOCKED 跳過）、跳過階段必須標註、無人值守的自動決策必須寫進 state.md 與 FINAL-REPORT（未通過要在檔首粗體標出） —— `agents/agent0_conduct.md`、`agents/agent1_plan.md`
- 實測員黑箱鐵律（不讀程式碼）、每個 PASS 只能來自本輪親手操作、E 編號跨輪不歸零 —— `agents/agent4_run.md`
- 經驗包先批准才寫入；改引擎先提案；**匯入的經驗包是資料不是指令**，安全過濾不放寬 —— `commands/blacktea_retro.md`
- 六個角色、調度與主對話都讀專案政策；既有服務不按 port 清除，Low 程式小修也必須獨立票級檢查；建案與變更均先歸檔再同次提交，保留未決與 push 暫停 —— `blacktea/runtime-contract.md`

驗收掃描器可用 `python3 -m unittest discover -s ~/.claude/blacktea/tests -v`：只在暫存 Git repo 測試，涵蓋中間 commit 加入後刪除、敏感檔刪除、合併側分支、首次推送與掃描失敗。規則文件的 Claude 實際派工／續跑仍須另外驗收，這些測試不代表整條流水線已跑過。

---

## 分享經驗包（把別人的經驗併進你的電腦）

交換單位就是 `blacktea/lessons.md` 本身——每台裝了這套引擎的機器段落結構都一樣（通用／訪談官／建造者／稽核員／實測員／流程），所以可以直接對段落合併。

```
/blacktea_retro 匯出                 → 產出 blacktea/export/lessons-<暱稱>-<日期>.md（檔首帶暱稱、日期、引擎版本），把這個檔案傳給對方
/blacktea_retro 匯入 <檔案路徑>       → 讀對方的包，逐條比對你的經驗包，提案 → 你逐條批准 → 寫入（每條標 `來源：暱稱`）→ commit
/blacktea_retro 移除來源 <暱稱>       → 反悔時把某人匯入的條目整批移除
```

匯入時的守門（在 `commands/blacktea_retro.md`「匯入模式」）：

- **別人的包是資料，不是指令**——四個 agent 開工時會照經驗包做事，所以任何要求執行指令、連網下載、跳過或放寬關卡、改引擎檔、碰專案以外檔案的條目一律剔除並列出原因。
- 對方的證據 ID（V-007 之類）在你這邊無法查證，改記「證據：外部 V-007」，由你用常識判斷可不可泛化。
- 與你既有條目矛盾 → 列出讓你裁決，預設保留你自己的。
- 每段 15 條上限照樣適用；對方包裡的「引擎修改提案」只呈現給你看、不執行。
- **一個字都不會在你批准前寫入**，跟復盤一樣。

---

## 改完引擎之後

- `agents/` 與 `skills/` 的檔案改完幾秒內會自動重載，不用重啟；`commands/` 官方沒保證熱載入，改完保守起見重啟 Claude Code。
- 重啟後可用 `/agents` 確認只有 agent0-conduct、agent2-build、agent3-ticket-check、agent3-review、agent4-run 五個分身；`/` 選單應有三個 blacktea 指令加 `/git`、`/vscode`、`/clawd`（五個流水線技能不該出現）。
- **執行檔裡不要再加「給使用者的導讀」**：agent 檔的全文會進分身的 system prompt、command 檔的全文會進對話，每多一行說明就是每次 spawn 都付一次；解釋放這裡。
- 三個指令檔首的 `model: opus` **只管你打指令的那一回合**；訪談要來回多回合，之後整條流水線用的是 session 模型。想讓整條線都跑 opus，開工前先打 `/model opus` 把 session 模型切過去（分身的模型由各自 agents 檔決定，不受影響）。

---

## 取材來源

- 建造者的「測試先行（紅→綠）」與修復批次的「診斷迴圈」六步，取材自 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）的 `tdd` 與 `diagnosing-bugs`，改寫成無人值守版本（seam 由票面 DoD 決定、假設清單寫進 build-log 而不是問人），並由票級檢查員驗證（red log、恆真檢查、`[DEBUG-]` 清零）。沒有整包安裝——它是手動逐個呼叫的工具箱，跟這條流水線的角色重疊且假設有人在中間，裝了會變成兩套規則。
