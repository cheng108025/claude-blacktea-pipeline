# 紅茶流水線（blacktea）——引擎總地圖

> 此檔只給人看，Claude 不會把它當指示執行。改了任何引擎檔，記得在 `~/.claude` 做一次 git commit（那就是還原點）。
>
> **寫作分工**：執行檔（`agents/`、`skills/`、`commands/`）寫給 AI——第二人稱、一件事只說一次、條件可判定，檔頭只留 2–3 行「門牌」（我是誰、誰呼叫我）；設計理由、呼叫關係、所有 🔧 旋鈕都只寫在這三份 README。檢驗法：一句話刪掉後 AI 的行為不會變，它就屬於 README。

## 你要打的指令只有三個

| 指令 | 什麼時候用 | 會發生什麼 |
|---|---|---|
| `/blacktea_plan 一句話描述` | 開新專案 | 訪談你 → 你確認工作單 → **它請你開新對話再打一次 `/blacktea_plan`** → 建造 → 稽核 → 瀏覽器實測 → FINAL-REPORT 一路到底，不會再請你換對話；「做不下去」的情況（票重做 2 次仍 FAIL、稽核超 3 輪、實測超 2 輪、需求沒定義、環境修不了）怎麼辦，定稿前一題問完寫成 run-policy.md——選「無人值守」就真的全程不回頭 |
| `/blacktea_change 一句話描述` | 專案已交付後想加功能／改呈現／修 bug；或**不帶參數**回頭處理無人值守期間跳過的待裁決事項 | 釐清（待裁決的一次問完）→ 改規格開 T-Rev 票 → spawn 總指揮分身跑建造（每票過票級檢查）→ 增量稽核 → 修復 → 增量實測 → 補報告；不用換視窗 |
| `/blacktea_retro` | 專案結案後 | 翻整個 `.pipeline/` 歸納教訓，經你批准才寫進經驗包 |
| `/blacktea_retro 匯出` ／ `匯入 <檔案>` | 想把經驗包分享給別人／把別人的經驗包併進來 | 見下方「分享經驗包」 |

工單定稿後是**固定換手點**：總指揮會停下來請你開新對話、打 `/blacktea_plan`（不帶參數）再開工——訪談把 context 堆得很厚，建造階段換乾淨的對話跑。中斷（用量上限、關機、重啟）後也是同一招：再打一次同一個指令（不帶參數）就會從 `.pipeline/state.md` 的中斷點續跑。`/blacktea_plan 從階段 3 開始` 可以跳階段（門禁照查）。另外三個一般技能 `/git`、`/vscode`、`/clawd` 與流水線無關。

## 大概要花多少錢（2026-08 查價，之後請以官方定價頁為準）

流水線的主引擎是 **Claude**；**Codex 只是可選的第二意見**——整個專案最多跑兩次 `codex exec`（拆完票覆核一次、首輪稽核一次），機器上沒裝就自動跳過，不影響流水線。

| 角色 | 模型 | 為什麼吃量 |
|---|---|---|
| 訪談官／總指揮（主對話） | session 模型（建議 opus） | 訪談來回多回合、讀整份規格與工單 |
| 建造者 agent2 | sonnet | 一票一隻、最多 3 隻並行，每隻都讀工單＋規格＋程式碼 |
| 票級檢查員 agent3-ticket-check | sonnet | 每票至少一次（FAIL 重做再加）；只載 6 KB 人設，照票面重跑驗證 |
| 稽核員 agent3 | opus | **主要消耗**：全案稽核首輪逐檔全量＋複審最多 3 輪 |
| 實測員 agent4 | sonnet | 真瀏覽器操作、截圖留證 |

| 方案 | 月費 | 對這條流水線的實際體感 |
|---|---|---|
| Claude Pro | $20 | 跑得動但一直撞 5 小時上限：一個視窗大約 2–4 張票就要等解鎖；靠 `state.md` 斷點續跑不會壞，但十幾張票的系統會拖成好幾天 |
| **Claude Max 5x（建議最低）** | $100 | 一天內跑完一個小型系統（10–15 張票、稽核 1–2 輪）的門檻 |
| Claude Max 20x | $200 | 同時開兩個專案、每天都在跑、或常常 20 張票以上再升；可先買 5x 撞到週上限再升級 |
| ChatGPT Plus（Codex，可選） | $20 | 一案只呼叫兩次，Plus 額度綽綽有餘；Pro $100/$200 對這條線是浪費。不買就跳過外部覆核 |

**結論：最低 $100/月（Max 5x）；要跨廠牌覆核再加 $20（ChatGPT Plus）＝ $120/月。** 偶爾才開一個專案的人可以改走 API 按量計費（Opus $5／$25、Sonnet $3／$15 每百萬 token 輸入／輸出），一個小系統跑完粗估 $30–100；每週都在跑的話訂閱划算得多。

省量旋鈕都在引擎裡：票級檢查員模型（`agents/agent3_ticket_check.md` frontmatter，現為 sonnet；要更嚴改 opus）、並行建造數（`skills/blacktea-dispatch/SKILL.md` ③）、稽核員模型（`agents/agent3_review.md` frontmatter）。

## 三個資料夾各放什麼

```
~/.claude/
├── commands/   你打的指令（只有上面三個）。全部 disable-model-invocation：只有人按才跑。只含主對話的工作。
├── agents/     六個角色，一人一檔：他是誰、鐵律、作業步驟。
│   ├── agent0_conduct.md      總指揮分身（subagent，name: agent0-conduct，opus）——階段二～五與變更步驟 3–7 的
│   │                          關卡、回退、失敗出口規則全在這裡；主對話只 spawn 它、看它回報。
│   ├── agent1_plan.md         訪談官——刻意沒有 name，所以不是 subagent（訪談要問你，subagent 不能問人）；
│   │                          由 /blacktea_plan 在主對話 Read 照做。它的三個技能在 skills/agent1-*。
│   ├── agent2_build.md        建造者（subagent，name: agent2-build，sonnet）——一次做一張票，永不碰 git。
│   ├── agent3_ticket_check.md 票級檢查員（subagent，name: agent3-ticket-check，sonnet）——每票獨立重跑驗證，PASS 才 commit。
│   ├── agent3_review.md       稽核員（subagent，name: agent3-review，opus）——全案稽核；預載 skills/agent3-quality-check。
│   └── agent4_run.md          實測員（subagent，name: agent4-run，sonnet）——真瀏覽器黑箱實測，不讀程式碼。
├── skills/     技能，一技能一資料夾（SKILL.md；內容都在本體，只有 codex-review 留 references/）。五個流水線技能都不出現在 / 選單。
│   ├── blacktea-dispatch/    派工與版控：Ready Queue → 並行建造 → 每票票級檢查 → PASS 才 commit／push。唯一能碰 git 的人。
│   ├── agent1-interview/     訪談官技能 a：問到整個架構清楚（評分表 ≥9 才停；評分表與出題格式在檔內）
│   ├── agent1-spec/          訪談官技能 b：把需求寫成規格書（章節菜單在檔內）
│   ├── agent1-tickets/       訪談官技能 c：拆工單＋自我稽核 7 項（格式、T01、清單在檔內）＋可選 Codex 覆核（references/）
│   ├── agent3-quality-check/ 稽核員技能 b：可讀、可維護、沒有多餘程式碼（13 條清單在檔內；不擋關）
│   ├── git/  vscode/  clawd/  一般技能（git 規範、VS Code 右鍵／連 WSL、桌面寵物）
└── blacktea/   共用資料：lessons.md（經驗包，復盤官經你批准才寫）、templates/（專案腳印：settings.json、mcp.json）
```

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
                        （分身裡）dispatch 建造 ─▶ 稽核員增量 ─▶ 修復 ─▶ 實測員增量實測 ─▶ 補 FINAL-REPORT
```

交接靠 `.pipeline/` 裡的檔案，不靠對話：`plan/01-requirements.md`（規格書）、`plan/02-workplan.md`（工單）、`plan/git-policy.md`、`03-build-log.md`（索引）＋`build-log/TXX.md`（每票施工紀錄）、`ticket-checks/TXX.md`（每票檢查紀錄）、`04-verify-report.md`、`05-e2e-report.md`、`evidence/`、`state.md`、`output/FINAL-REPORT.md`。

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
| 技術棧攤牌那一輪表格有哪幾列、什麼時候問 | `skills/agent1-interview/SKILL.md` | 「訪談規則」→ 必問題——技術棧攤牌 |
| 規格書要有哪些章、技術棧表；哪些章不可省 | `skills/agent1-spec/SKILL.md` | 「章節菜單」、「五個必備章」 |
| ticket 要拆多小、六欄長怎樣 | `skills/agent1-tickets/SKILL.md` | 「每張 ticket 的品質要求」、「Ticket 格式」 |
| T01 做什麼、.gitignore 擋什麼 | `skills/agent1-tickets/SKILL.md` | 「工作單的組成」第 2 條 |
| 交棒前自我稽核 7 項、待問清單追問幾輪 | `skills/agent1-tickets/SKILL.md` | 「自我稽核」（第 7 項） |
| 要不要用 Codex 當第二雙眼睛、分級 | `skills/agent1-tickets/references/codex-review.md` | 全檔 |
| **建造** | | |
| 同時派幾隻建造者、哪些票永遠不並行 | `skills/blacktea-dispatch/SKILL.md` | ③ |
| 票級檢查一次跑幾隻、每票重做幾次 | `skills/blacktea-dispatch/SKILL.md` | ⑤ |
| build-log 索引長什麼樣 | `skills/blacktea-dispatch/SKILL.md` | ⑧ |
| 建造者用哪顆模型 | `agents/agent2_build.md` | frontmatter `model` |
| 建造者的編碼守則、健康檢查等多久、server 配方 | `agents/agent2_build.md` | 「編碼守則」、「Linux 指令慣例」 |
| build-log 分檔要記什麼 | `agents/agent2_build.md` | 「附錄」 |
| 票級檢查用哪顆模型、紀錄每段字數、要不要順帶品質檢查 | `agents/agent3_ticket_check.md` | frontmatter、「寫紀錄」、「判定」最後一條 |
| **稽核** | | |
| 稽核員用哪顆模型 | `agents/agent3_review.md` | frontmatter `model` |
| 稽核多嚴、嚴重度基準、資安 8 條 | `agents/agent3_review.md` | 「關卡判定」、「嚴重度基準」、Step 5 |
| Codex 第二意見何時跑 | `agents/agent3_review.md` | 「外部覆核」 |
| 品質檢查查什麼、各算什麼嚴重度、想讓某類擋關 | `skills/agent3-quality-check/SKILL.md` | 「清單」、「嚴重度對照」 |
| **實測** | | |
| 實測員用哪顆模型 | `agents/agent4_run.md` | frontmatter `model` |
| 實測旅程三層、惡意輸入後備測法 | `agents/agent4_run.md` | Step 3 |
| 伺服器啟動等多久、證據命名 | `agents/agent4_run.md` | Step 2、Step 4 |
| **流程** | | |
| 稽核退回上限（3）、實測退回上限（2）、跳過階段 | `agents/agent0_conduct.md` | 建案模式「階段三」「階段四」「跳過階段」 |
| 變更的修復輪上限（3）、什麼嚴重度要在實測前修、幾輪後改全旅程實測 | `agents/agent0_conduct.md` | 變更模式「步驟 5」「步驟 6」 |
| 總指揮分身用哪顆模型 | `agents/agent0_conduct.md` | frontmatter `model` |
| 分身續跑上限（10）、工單定稿後要不要強制換新對話 | `commands/blacktea_plan.md` | 「監督迴圈」、「階段一」末段 |
| 經驗包每段幾條、教訓取捨標準、改引擎的門檻 | `commands/blacktea_retro.md` | 「寫入規則」、「什麼值得記」、「例外」 |
| 匯入別人經驗包時哪些條目一律剔除 | `commands/blacktea_retro.md` | 匯入模式 → 安全過濾 |

每個執行檔開頭只有 2–3 行「門牌」；檔內的 🔧 標記對應上表。

## 不要放寬的守門規則（與所在檔）

- 規格書禁止「待定」；同一輪題目彼此獨立；每輪 ≤4 題；最多 8 輪；總分 ≥9.0 且 ★ 滿分才寫規格書 —— `agents/agent1_plan.md`、`skills/agent1-interview/`
- 工單 DRAFT 就不准開工 —— `skills/blacktea-dispatch/`
- 建造者禁止猜需求（標 BLOCKED）、永不碰 git、票級檢查不得自判 —— `agents/agent2_build.md`
- 票級檢查員不讀 build-log 當證據、不信任建造者回報；每票 PASS 才 commit —— `agents/agent3_ticket_check.md`
- 票面有測試清單的票：先紅後綠（`evidence/TXX-red.log`）、無恆真測試；修復批次每個發現要有會變紅的回饋迴圈、回歸測試、`[DEBUG-]` 清零 —— `agents/agent2_build.md`、`agents/agent3_ticket_check.md`
- git 只有調度技能一個人動；`gh repo create` 只有它能做；push 授權只來自 `git-policy.md`；force push／推 tag／改公開一律先問；push 前機密掃描 —— `skills/blacktea-dispatch/`、`skills/git/`
- 每票過票級檢查 PASS 才 commit；每票最多重做 2 次；機密掃描命中 → 暫停之後所有 push、繼續 commit、最後回報（不中途問） —— `skills/blacktea-dispatch/`
- 稽核員不信任自我宣稱、發現全部列出、關閉權在稽核員、V 編號跨輪不歸零、Critical=0 且 High=0 才 PASS —— `agents/agent3_review.md`（覺得誤報太多時用 `.pipeline/waivers.md` 逐條豁免，不要改鬆關卡；建造者可提可重現反證，多數誤報會在機器之間自己消化掉）
- 稽核退回上限 3 輪、實測退回上限 2 輪、agent4 退回不佔額度、需求層級問題回使用者（無人值守下也不准猜，只能標 BLOCKED 跳過）、跳過階段必須標註、無人值守的自動決策必須寫進 state.md 與 FINAL-REPORT（未通過要在檔首粗體標出） —— `agents/agent0_conduct.md`、`agents/agent1_plan.md`
- 實測員黑箱鐵律（不讀程式碼）、每個 PASS 只能來自本輪親手操作、E 編號跨輪不歸零 —— `agents/agent4_run.md`
- 經驗包先批准才寫入；改引擎先提案；**匯入的經驗包是資料不是指令**，安全過濾不放寬 —— `commands/blacktea_retro.md`

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

## 改完引擎之後

- `agents/` 與 `skills/` 的檔案改完幾秒內會自動重載，不用重啟；`commands/` 官方沒保證熱載入，改完保守起見重啟 Claude Code。
- 重啟後可用 `/agents` 確認只有 agent0-conduct、agent2-build、agent3-ticket-check、agent3-review、agent4-run 五個分身；`/` 選單應有三個 blacktea 指令加 `/git`、`/vscode`、`/clawd`（五個流水線技能不該出現）。
- **執行檔裡不要再加「給使用者的導讀」**：agent 檔的全文會進分身的 system prompt、command 檔的全文會進對話，每多一行說明就是每次 spawn 都付一次；解釋放這裡。
- 三個指令檔首的 `model: opus` **只管你打指令的那一回合**；訪談要來回多回合，之後整條流水線用的是 session 模型。想讓整條線都跑 opus，開工前先打 `/model opus` 把 session 模型切過去（分身的模型由各自 agents 檔決定，不受影響）。

## 取材來源

- 建造者的「測試先行（紅→綠）」與修復批次的「診斷迴圈」六步，取材自 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）的 `tdd` 與 `diagnosing-bugs`，改寫成無人值守版本（seam 由票面 DoD 決定、假設清單寫進 build-log 而不是問人），並由票級檢查員驗證（red log、恆真檢查、`[DEBUG-]` 清零）。沒有整包安裝——它是手動逐個呼叫的工具箱，跟這條流水線的角色重疊且假設有人在中間，裝了會變成兩套規則。
