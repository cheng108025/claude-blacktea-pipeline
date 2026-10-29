# 紅茶流水線（blacktea）——使用說明

> 這份只寫「你要怎麼用」：指令、使用者流程、花費、資料夾結構。角色分工與流程規則在 [blacktea/protocol.md](blacktea/protocol.md)、[agents/README.md](agents/README.md)、[skills/README.md](skills/README.md)。改了任何引擎檔，記得在 `~/.claude` 做一次 git commit（那就是還原點）。

## 1. 使用到的指令

| 指令 | 什麼時候用 | 會發生什麼 |
|---|---|---|
| `/blacktea_plan 一句話描述` | 開新專案 | 訪談你 → 你確認規格書 → 你確認工作單與 UI 原型 → 自動建造 → 稽核 → 實測 → FINAL-REPORT |
| `/blacktea_plan`（不帶參數） | 任何中斷（用量上限、關機、重啟）之後 | 讀 `.pipeline/state.json`，從中斷點續跑 |
| `/blacktea_plan 從階段 N 開始` | 想跳階段 | 交給總指揮檢查門禁；明說跳過稽核／實測會照做，但結案標 INCOMPLETE |
| `/blacktea_change 一句話描述` | 專案已交付後想加功能／改呈現／修 bug | 查舊紀錄 → 有歧義才問 → 改規格開 T-Rev 票 → 建造（每票檢查）→ 增量稽核 → 增量實測 → 本輪報告；不用換視窗，小修也一定稽核 |
| `/blacktea_change`（不帶參數） | 回頭處理無人值守期間「跳過、等你決定」的事項 | 一次問完待裁決，再自動做完 |
| `/blacktea_retro` | 專案結案後 | 只看上次復盤之後的新輪次，歸納教訓，**經你批准**才寫進全域經驗包；commit 後問你要不要 push |
| `/blacktea_retro 匯出`／`匯入 <檔案>`／`移除來源 <暱稱>` | 分享或併入別人的經驗包 | 別人的包只當資料、逐條審核，你批准才寫入 |

另有三個與流水線無關的一般技能：`/git`、`/vscode`、`/clawd`。

## 2. 使用者流程

整條流水線**只有前半段需要你**：回答訪談、確認規格書與工作單、做政策選擇；之後全自動。

### 開工前

- 建議先打 `/model opus`：訪談要來回多回合，用的是 session 模型。
- 票級 Codex 驗證預設開啟，電腦要先裝好 Codex CLI 並登入（沒裝也能跑，只是該步會標「未執行」）。

### 流程一覽

| # | 階段 | 你會看到／要做的事 |
|---|---|---|
| 1 | 打 `/blacktea_plan 一句話描述` | 描述直接當作訪談的起點 |
| 2 | 專案準備 | 建 `.pipeline/`；只有專案需要又缺少時才從模板建 `.claude/settings.json`／`.mcp.json`，不覆蓋你既有的設定 |
| 3 | **Git 政策** | 「只留本機，還是上 GitHub？」選 GitHub 再確認私有／公開、repo 名稱、分支。選了備份＝每張票 commit 完自動 push（push 前掃機密），之後不再逐票問 |
| 4 | **訪談** | 每輪最多 4 題、以選擇題為主，每題標建議與代價；只問會影響產品行為、資料、權限、部署或返工成本的事。說「你決定」就採預設並寫進決策紀錄。最多 8 輪 |
| 4a | 必問題（每案都有） | **頁面與流程**、**視覺定調**（風格、亮暗、主色、參考網站）、**執行方式**（本機或 Docker；選 Docker 會補問 port、volume、機密；會先檢查你有沒有裝 Docker）、**技術路線**（它先給分層技術棧表，你點頭或修改） |
| 5 | **確認規格書** | 產出 `<專案名>_requirements.html`：八個必備章、表格為主、缺口總覽放最前面、設計系統附亮暗視覺樣本與對比驗算。你點頭後才拆票 |
| 6 | 拆工單＋自我找碴 | 工單寫在 `tickets.json`，腳本檢查編號、依賴循環、檔案範圍，再產生 02-workplan.md 與 HTML |
| 7 | **確認工作單與外觀** | `<專案名>_workplan.html`（依功能群分組的票卡片）；有畫面的專案多一份 **UI 原型**，要你明確說「**外觀可以**」。HTML 都能手動切日／夜模式 |
| 8 | **政策（開工前最後的問題）** | ① **做不下去怎麼辦**：無人值守（建議；不猜需求、不花錢、卡住的跳過並在報告列出）或遇事停下來問<br>② **票級 Codex 驗證（預設開，不再問）**：每張票做完，Codex（gpt-5.6-sol／medium）在隔離副本唯讀再檢查一次，Claude 逐項親自覆核；要關閉就在這時說 |
| 9 | **自動執行** | 直接交給總指揮，不用開新對話。一次一張票、每張票在獨立 git worktree 建造 → 獨立檢查簽收據 → commit 並整合 → 全案稽核（Critical／High 清零，修復最多 3 次）→ 實測全部旅程（修復最多 2 次）→ 報告 |
| 10 | 結案 | 全部通過才是 COMPLETED；有跳過、未驗或失敗就是 INCOMPLETE，報告第一行寫原因 |
| 11 | 之後 | 想改東西：`/blacktea_change`；想累積經驗：`/blacktea_retro` |

### 中斷與續跑

再打一次同一個指令（不帶參數）即可。進度存在 `.pipeline/state.json`（`state.md` 是自動產生的摘要）；中斷在 commit 前後都會先核對收據與 Git，不會重做已整合的票，也不會放行沒驗過的票。

## 3. 花費

（2026-08 查價，之後請以官方定價頁為準）

主引擎是 **Claude**。Codex 是第二意見：票級 Codex 驗證預設每張票多一次 `codex exec`；拆票後的計劃覆核與首輪程式覆核要在 run-policy 開 `external_review` 才做，整個專案各最多一次。

| 角色 | 模型 | 為什麼吃量 |
|---|---|---|
| 訪談官（主對話） | session 模型（建議 opus） | 訪談來回多回合 |
| 總指揮 agent0 | opus | 讀狀態、派工、判關卡、寫報告 |
| 建造者 agent2 | sonnet | 一票一隻，只讀該票、相關規格與程式碼 |
| 票級檢查員 | sonnet | 每票至少一次，親自重跑驗證、重建紅燈 |
| 稽核員 agent3 | opus | **主要消耗**：首次全案逐檔，之後增量 |
| 實測員 agent4 | sonnet | 真瀏覽器操作、截圖留證 |

| 方案 | 月費 | 體感 |
|---|---|---|
| Claude Pro | $20 | 跑得動但常撞 5 小時上限，靠斷點續跑不會壞，但十幾張票會拖成好幾天 |
| **Claude Max 5x（建議最低）** | $100 | 一天內跑完一個小型系統（10–15 張票）的門檻 |
| Claude Max 20x | $200 | 同時開多個專案或常常 20 張票以上再升 |
| ChatGPT Plus（Codex） | $20 | 票級 Codex 驗證每票一次，票多的專案留意額度 |

省量旋鈕：各角色模型在 `agents/*.md` frontmatter；票級 Codex 驗證在專案 `run-policy.md` 改「關」。

## 4. 資料夾結構

### 引擎（全域，`~/.claude/`）

```
~/.claude/
├── commands/   三個指令：blacktea_plan／blacktea_change／blacktea_retro
├── agents/     六個角色（總指揮、訪談官、建造者、票級檢查員、稽核員、實測員）
├── skills/     派工與版控、訪談三技能、品質檢查，以及 /git、/vscode、/clawd
└── blacktea/
    ├── protocol.md     共通契約：責任、狀態、重試上限、結案條件
    ├── references/     按需讀的細則：執行流程、驗證配方、修復、稽核、舊專案接手
    ├── scripts/        pipeline.py（狀態、收據、工單檢查與產生）、scan_push.py（機密掃描）、md2html.py（HTML 檢視版）
    ├── templates/      專案模板與 examples/ 格式樣本
    ├── tests/          腳本測試
    └── lessons.md      經驗包
```

### 專案內（每個專案自己的 `.pipeline/`）

```
<你的專案>/
└── .pipeline/
    ├── plan/           01-requirements.md、tickets.json（工單唯一來源）、02-workplan.md（產生的）、git-policy.md、run-policy.md、ui-prototype.html
    ├── output/         <專案名>_requirements.html、_workplan.html、_ui-prototype.html、FINAL-REPORT.md、reports/<輪名>-report.md
    ├── rounds/<NN>/    每輪一個資料夾（01＝首次建造，之後 02-T-Rev01…）：build-log/、ticket-checks/、evidence/、04、05 報告
    ├── worktrees/      每張票的隔離工作區（失敗的票留在這裡，不污染主專案）
    ├── state.json      執行狀態唯一來源（只由 pipeline.py 更新）
    ├── state.md        自動產生的進度摘要
    ├── findings.md     跨輪 V／E／U 發現索引
    └── waivers.md      你明確豁免的項目
```

### 驗證引擎本身

```bash
python3 -m unittest discover -s ~/.claude/blacktea/tests -v
python3 ~/.claude/blacktea/scripts/check_engine.py
```

測試在臨時 repo 驗證收據、worktree 隔離、重試上限、替代依賴、工單產生與機密掃描；不測真實 GitHub push、瀏覽器或 Docker。
