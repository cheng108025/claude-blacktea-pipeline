# 紅茶流水線（blacktea）——引擎總地圖

> 此檔只給人看，Claude 不會把它當指示執行。改了任何引擎檔，記得在 `~/.claude` 做一次 git commit（那就是還原點）。

## 你要打的指令只有三個

| 指令 | 什麼時候用 | 會發生什麼 |
|---|---|---|
| `/blacktea_plan 一句話描述` | 開新專案 | 訪談你 → 你確認工作單 → 建造 → 稽核 → 瀏覽器實測 → FINAL-REPORT，中途只有卡關才找你 |
| `/blacktea_change 一句話描述` | 專案已交付後想加功能／改呈現／修 bug | 釐清 → 改規格開 T-Rev 票 → 建造（每票過票級檢查）→ 增量稽核 → 修復 → 增量實測 → 補報告 |
| `/blacktea_retro` | 專案結案後 | 翻整個 `.pipeline/` 歸納教訓，經你批准才寫進經驗包 |
| `/blacktea_retro 匯出` ／ `匯入 <檔案>` | 想把經驗包分享給別人／把別人的經驗包併進來 | 見下方「分享經驗包」 |

中斷（用量上限、關機、重啟）後再打一次同一個指令（不帶參數）就會從 `.pipeline/state.md` 的中斷點續跑。`/blacktea_plan 從階段 3 開始` 可以跳階段（門禁照查）。另外三個一般技能 `/git`、`/vscode`、`/clawd` 與流水線無關。

## 大概要花多少錢（2026-08 查價，之後請以官方定價頁為準）

流水線的主引擎是 **Claude**；**Codex 只是可選的第二意見**——整個專案最多跑兩次 `codex exec`（拆完票覆核一次、首輪稽核一次），機器上沒裝就自動跳過，不影響流水線。

| 角色 | 模型 | 為什麼吃量 |
|---|---|---|
| 訪談官／總指揮（主對話） | session 模型（建議 opus） | 訪談來回多回合、讀整份規格與工單 |
| 建造者 agent2 | sonnet | 一票一隻、最多 3 隻並行，每隻都讀工單＋規格＋程式碼 |
| 稽核員 agent3 | opus | **主要消耗**：每票一次票級檢查＋全案稽核最多 3 輪 |
| 實測員 agent4 | sonnet | 真瀏覽器操作、截圖留證 |

| 方案 | 月費 | 對這條流水線的實際體感 |
|---|---|---|
| Claude Pro | $20 | 跑得動但一直撞 5 小時上限：一個視窗大約 2–4 張票就要等解鎖；靠 `state.md` 斷點續跑不會壞，但十幾張票的系統會拖成好幾天 |
| **Claude Max 5x（建議最低）** | $100 | 一天內跑完一個小型系統（10–15 張票、稽核 1–2 輪）的門檻 |
| Claude Max 20x | $200 | 同時開兩個專案、每天都在跑、或常常 20 張票以上再升；可先買 5x 撞到週上限再升級 |
| ChatGPT Plus（Codex，可選） | $20 | 一案只呼叫兩次，Plus 額度綽綽有餘；Pro $100/$200 對這條線是浪費。不買就跳過外部覆核 |

**結論：最低 $100/月（Max 5x）；要跨廠牌覆核再加 $20（ChatGPT Plus）＝ $120/月。** 偶爾才開一個專案的人可以改走 API 按量計費（Opus $5／$25、Sonnet $3／$15 每百萬 token 輸入／輸出），一個小系統跑完粗估 $30–100；每週都在跑的話訂閱划算得多。

省量旋鈕都在引擎裡：票級檢查的模型可降為 sonnet（`skills/blacktea-dispatch/SKILL.md` ⑤）、並行建造數（同檔 ③）、稽核員模型（`agents/agent3_review.md` frontmatter）。簡單專案這幾個一調，Max 5x 綽綽有餘。

## 三個資料夾各放什麼

```
~/.claude/
├── commands/   你打的指令（只有上面三個）。全部 disable-model-invocation：只有人按才跑。
├── agents/     四個角色，一人一檔：他是誰、鐵律、作業步驟。
│   ├── agent1_plan.md    訪談官——刻意沒有 name，所以不是 subagent（訪談要問你，subagent 不能問人）；
│   │                     由 /blacktea_plan 在主對話 Read 照做。它的三個技能在 skills/agent1-*。
│   ├── agent2_build.md   建造者（subagent，name: agent2-build，sonnet）——一次做一張票，永不碰 git。
│   ├── agent3_review.md  稽核員（subagent，name: agent3-review，opus）——票級檢查＋全案稽核；預載 skills/agent3-*。
│   └── agent4_run.md     實測員（subagent，name: agent4-run，sonnet）——真瀏覽器黑箱實測，不讀程式碼。
├── skills/     技能，一技能一資料夾（SKILL.md ＋ references/）。六個流水線技能都不出現在 / 選單。
│   ├── blacktea-dispatch/    派工與版控：Ready Queue → 並行建造 → 每票票級檢查 → PASS 才 commit／push。唯一能碰 git 的人。
│   ├── agent1-interview/     訪談官技能 a：問到整個架構清楚（評分表 ≥9 才停）
│   ├── agent1-spec/          訪談官技能 b：把需求寫成規格書
│   ├── agent1-tickets/       訪談官技能 c：照規格書拆工單＋自我稽核＋Codex 覆核
│   ├── agent3-ticket-check/  稽核員技能 a：每張票做完親自重跑驗證，PASS 才准 commit
│   ├── agent3-quality-check/ 稽核員技能 b：可讀、可維護、沒有多餘程式碼（不擋關）
│   ├── git/  vscode/  clawd/  一般技能（git 規範、VS Code 右鍵／連 WSL、桌面寵物）
└── blacktea/   共用資料：lessons.md（經驗包，復盤官經你批准才寫）、templates/（專案腳印：settings.json、mcp.json）
```

## 誰呼叫誰（一張圖）

```
你 ─/blacktea_plan─▶ 總指揮（主對話，commands/blacktea_plan.md）
  階段一  Read agents/agent1_plan.md ─▶ Read skills/agent1-interview ─▶ agent1-spec ─▶ agent1-tickets ─▶ 你看 HTML 點頭 ─▶ 定稿
  階段二  Read skills/blacktea-dispatch ─▶ spawn agents/agent2_build（最多 3 隻並行，一票一隻）
            每收一票 ─▶ spawn agents/agent3_review「票級檢查 TXX」（用 skills/agent3-ticket-check）─▶ PASS 才 commit／push
            FAIL ─▶ 建造者單票修復（最多 2 次）
  階段三  spawn agents/agent3_review「全案稽核」：能不能跑（＋核對每票都有票級 PASS）、Bug、資安、架構對照、品質（skills/agent3-quality-check）、Codex
            FAIL ─▶ dispatch 修復批次 ─▶ 複審（上限 3 輪）
  階段四  spawn agents/agent4_run 全旅程瀏覽器實測（上限 2 輪）
  階段五  總指揮寫 FINAL-REPORT ─▶ 提醒 /blacktea_retro
你 ─/blacktea_change─▶ 變更官（主對話）：改規格開 T-Rev 票 ─▶ dispatch 建造 ─▶ 稽核員增量 ─▶ 修復 ─▶ 實測員增量實測 ─▶ 補 FINAL-REPORT
```

交接靠 `.pipeline/` 裡的檔案，不靠對話：`plan/01-requirements.md`（規格書）、`plan/02-workplan.md`（工單）、`plan/git-policy.md`、`03-build-log.md`（索引）＋`build-log/TXX.md`（每票施工紀錄）、`ticket-checks/TXX.md`（每票檢查紀錄）、`04-verify-report.md`、`05-e2e-report.md`、`evidence/`、`state.md`、`output/FINAL-REPORT.md`。

## 想調整什麼 → 去哪個檔

| 想調整什麼 | 檔案 | 段落 |
|---|---|---|
| 每輪問幾題、最多幾輪、門檻分數 | `skills/agent1-interview/SKILL.md` | 訪談規則、門檻 |
| 評分表的面向、哪些必滿分 | `skills/agent1-interview/references/scorecard.md` | 全檔 |
| 問題要問得多詳細 | `skills/agent1-interview/references/question-format.md` | 全檔 |
| 規格書要有哪些章、技術棧表 | `skills/agent1-spec/references/spec-outline.md` | 全檔 |
| ticket 要拆多小、六欄長怎樣 | `skills/agent1-tickets/SKILL.md`、`references/ticket-template.md` | 品質要求／全檔 |
| T01 做什麼、.gitignore 擋什麼 | `skills/agent1-tickets/references/workplan-structure.md` | T01 |
| 交棒前自我稽核 7 項、Codex 分級 | `skills/agent1-tickets/references/self-audit-checklist.md`、`codex-review.md` | 全檔 |
| Git 政策怎麼問、HTML 檢視版 | `agents/agent1_plan.md` | Phase 0、Phase E |
| 同時派幾隻建造者、每票重做幾次、票級檢查用哪顆模型 | `skills/blacktea-dispatch/SKILL.md` | ③、⑤ |
| build-log 索引長什麼樣 | `skills/blacktea-dispatch/SKILL.md` | ⑧ |
| 建造者的編碼守則、server 配方 | `agents/agent2_build.md` | 編碼守則、Linux 指令慣例 |
| 票級檢查查什麼 | `skills/agent3-ticket-check/SKILL.md` | 怎麼檢查、判定 |
| 品質檢查查什麼、各算什麼嚴重度 | `skills/agent3-quality-check/references/quality-checklist.md` | 全檔 |
| 稽核多嚴、嚴重度基準、資安 8 條 | `agents/agent3_review.md` | 關卡判定、嚴重度基準、C 段 |
| 稽核退回上限（3）、實測退回上限（2） | `commands/blacktea_plan.md` | 階段三、階段四 |
| 實測旅程三層、降級方式、證據命名 | `agents/agent4_run.md` | 設計旅程、一條一條執行 |
| 變更的修復輪上限、多少輪後改全旅程實測 | `commands/blacktea_change.md` | 步驟 5、步驟 6 |
| 經驗包每段幾條 | `commands/blacktea_retro.md` | 寫入規則 |
| 匯入別人經驗包時哪些條目一律剔除 | `commands/blacktea_retro.md` | 匯入模式 → 安全過濾 |

每個檔案開頭都有一段「給使用者的導讀」與 🔧 標記，指出該檔可以調整的地方。

## 不要放寬的守門規則（與所在檔）

- 規格書禁止「待定」；同一輪題目彼此獨立；每輪 ≤4 題；最多 8 輪；總分 ≥9.0 且 ★ 滿分才寫規格書 —— `agents/agent1_plan.md`、`skills/agent1-interview/`
- 工單 DRAFT 就不准開工 —— `skills/blacktea-dispatch/`
- 建造者禁止猜需求（標 BLOCKED）、永不碰 git、票級檢查不得自判 —— `agents/agent2_build.md`
- git 只有調度技能一個人動；`gh repo create` 只有它能做；push 授權只來自 `git-policy.md`；force push／推 tag／改公開一律先問；push 前機密掃描 —— `skills/blacktea-dispatch/`、`skills/git/`
- 每票過票級檢查 PASS 才 commit；每票最多重做 2 次 —— `skills/blacktea-dispatch/`
- 稽核員不信任自我宣稱、發現全部列出、關閉權在稽核員、V 編號跨輪不歸零、Critical=0 且 High=0 才 PASS —— `agents/agent3_review.md`
- 稽核退回上限 3 輪、實測退回上限 2 輪、agent4 退回不佔額度、需求層級問題回使用者、跳過階段必須標註 —— `commands/blacktea_plan.md`
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
- 重啟後可用 `/agents` 確認只有 agent2-build、agent3-review、agent4-run 三個分身；`/` 選單應有三個 blacktea 指令加 `/git`、`/vscode`、`/clawd`（六個流水線技能不該出現）。
- 三個指令檔首的 `model: opus` **只管你打指令的那一回合**；訪談要來回多回合，之後整條流水線用的是 session 模型。想讓整條線都跑 opus，開工前先打 `/model opus` 把 session 模型切過去（分身的模型由各自 agents 檔決定，不受影響）。
