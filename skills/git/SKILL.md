---
name: git
description: 任何牽涉 git／GitHub 的動作都要先讀本檔。三種時機：(1) 建立新專案或 git init 時——必須先問使用者要不要推 GitHub（一個專案只問這一次，答應了就長期有效）；(2) 準備 push／建 remote 時——查專案有沒有先授權（`.pipeline/plan/git-policy.md` 或使用者答應過）：有就直接推並回報推了哪幾張票，沒有就先問；force push／推 tag／改公開一律要再問；(3) 遇到 git 錯誤時——push 失敗、憑證／TLS 錯誤、GitHub 連不上、要求輸入密碼、dubious ownership、睡醒後 git 突然壞掉等，內含 WSL 環境的診斷順序與修復指令。
---

# Git 使用規範與問題急救手冊（WSL Ubuntu-24.04 環境）

本檔分兩部分：**Part A 強制規則**（動手前必讀）、**Part B 問題急救**（出錯時查表）。

---

# Part A：強制規則（不可跳過）

## 規則 1：建立新專案時，必須詢問使用者是否要推到 GitHub

**觸發時機**——只要做到下列任一件事，就必須先問：

- 執行 `git init`
- 建立新專案骨架／腳手架（`npm create`、`cargo new`、`django-admin startproject` 等）
- 紅茶流水線：調度技能做首 commit 前（正常由訪談官 Phase 0 先問好寫成 `git-policy.md`；跑在分身裡問不到人時，照調度技能 ②-3 預設「只留本機」，不建 repo、不 push）
- 使用者說「開一個新專案」「幫我做一個 XXX」而該專案還沒有 repo

**要問清楚三件事，一次問完，不要分三輪：**

1. 要不要建 GitHub repo？（要／不要）
2. 私有還是公開？——**預設建議私有**，公開要使用者明確選
3. repo 名稱要叫什麼？（可提供建議名讓他確認）

**規則細節：**

- **不准自作主張執行 `gh repo create`。** 沒問過就建 repo = 違規，即使你覺得「一定會想要」。
- 使用者說「不要」→ 只做本機 `git init`，**不建 remote，之後不要再重複問**同一個專案。
- 使用者說「要」→ 這一次的回答就是**這個專案的長期授權**：之後建 repo 與 push 都照這個決定執行，不必再逐次問（見規則 2 的預先授權例外）。
- 公開 repo 前**必須**跑一次下面的敏感檔檢查，並把結果講給使用者聽再讓他決定。

## 規則 2：push 前要詢問使用者——除非這個專案已經先授權過

**預設：問過才能推。** 但「問」是**一個專案問一次**，不是一次 push 問一次——問法見規則 1，答應了就在專案內長期有效。

**預先授權例外（符合就直接推，不要再問）：**

- 專案有 `.pipeline/plan/git-policy.md` 且記著「上 GitHub 備份：是」——這是訪談官在 Phase 0 當面問到的答案，**整條流水線的每一次 push 都照它執行**，包含每完成一張 ticket 後的那一次。中途再問等於違反「階段二之後不打斷使用者」的設計。
- 非流水線專案：使用者在這個專案已明確答應過推 GitHub（規則 1 的三問），**之後的 push 沿用該授權**，不必逐次確認。

**授權不涵蓋、仍然必須先問的情況：**

- `git push --force` / `--force-with-lease`——會覆蓋遠端歷史，**每一次都要問**，並講清楚會蓋掉什麼。
- 推到授權當時談的以外的地方：非 origin 的 remote、非當前工作分支、`git push --tags`。
- 把 repo 從私有改公開，或推到公開 repo 而授權時談的是私有。
- 敏感檔檢查有命中（見下）——**有授權也要停下來先講給使用者聽**。**例外：紅茶流水線內**（專案有 `git-policy.md`、執行者是調度技能）命中＝不推、不問、本機照常 commit、流水線繼續、結案一次回報（規則在 `~/.claude/skills/blacktea-dispatch/SKILL.md`，以它為準）。
- 專案沒有 `git-policy.md`、也從沒問過→ 先照規則 1 問，不准先斬後奏。

**每一次 push（含已授權的）都要做的兩件事：**

1. 先跑下面的敏感檔檢查。
2. 推完在回覆裡講清楚：**推了哪幾張票／幾個 commit、推到哪個 repo 與分支**，讓使用者不用去 GitHub 也知道進度。

**絕對不要：** 在完全沒問過、也沒有政策檔的情況下，為了「順手」自行 push 或 `gh repo create`。

**哪些動作算 push**（都適用本規則——有授權就照授權推，沒授權就要先問）：

- `git push`、`git push -u origin <branch>`
- `git push --force` / `--force-with-lease`（授權不涵蓋，每次都要問）
- `gh repo create --push`、`gh repo create --source=.`（含隱含 push 的）
- 推 tag：`git push --tags`（授權不涵蓋）
- 推到任何非 origin 的 remote（授權不涵蓋）

**需要問的時候，要一併講清楚（讓使用者有資訊可判斷）：**

- 推去哪：remote 名稱 + URL + 目標 branch
- 推什麼：幾個 commit、動到哪些檔案
- repo 是公開還是私有
- 敏感檔檢查結果（見下）

## push 前的敏感檔檢查（規則 1、2 共用）

1. 核對已授權的 remote／分支，用 `git status`、待推 log 與 diff stat 確認提交範圍；有 origin 時先 fetch 更新目的分支基準，不能假定舊 tracking ref 就是遠端現況。fetch／基準核對失敗＝掃描未完成，push 延後，不能省略或改拿 HEAD 當基準。
2. 在該 repo 執行 `python3 ~/.claude/blacktea/scan-push.py --base origin/<已核對分支>`。**首次推到已確認為空的遠端**才省略 `--base`（掃全部可達歷史）；找不到既有遠端 ref 不能假裝遠端是空的。
3. helper 逐一掃所有待推 commit 的完整檔案樹（包含合併進來的側分支），檢查敏感檔名、常見 token 與疑似憑證賦值；同 blob 去重。中間 commit 加入後又刪掉的內容仍會命中，不能只看兩端 diff。憑證賦值認得前後綴名稱（`FRED_API_KEY`、`DB_PASSWORD`、`AWS_SECRET_ACCESS_KEY`）與無引號值（`.env`／`.ini` 寫法）。兩個刻意的放行：(a) 範本檔（`.env.example`／`.sample`／`.template`／`.dist`、`*.example` 等）所有賦值皆為空或佔位值時，不算敏感檔名；範本裡有任何實值仍命中，真正的 `.env` 一律命中；(b) 值像測試假資料（含 secret／test／example／fake 等字、非 ASCII 說明文字、`***`、`&lt;`）或像程式參照（`os.environ[...]`、`config.x`、`$VAR`、函式呼叫）、純數字時不算候選。這是候選掃描，不保證辨識所有機密；可疑內容仍依授權政策處理，不放寬命中。
4. 退出碼 **0＝本次規則未命中、1＝有候選、2＝掃描未完成**；1／2 都不 push。helper 缺失、超大 blob、巢狀 repo 或 Git 出錯均不當乾淨。輸出只含 commit／路徑／規則，不貼機密原值。需要重現可跑 `python3 -m unittest discover -s ~/.claude/blacktea/tests -v`（只建立暫存測試 repo）。

任何候選或掃描未完成 → 非流水線先回報；流水線不推、不問、本機照常 commit，記 state 的 push 暫停／延後與基準，結案回報。後續票、單 commit 與最後補推都必須遵守同一暫停狀態，只有使用者明確處理後才能解除；刪掉最新版本的機密不會清除待推歷史。

`.gitignore` 建議用白名單寫法（先 `*` 全忽略，再逐一放行），比黑名單安全——漏寫黑名單會外洩，漏寫白名單只是少備份一個檔案。`~/.claude` 的 .gitignore 就是這種寫法，可參考。

---

# Part B：問題急救手冊

遇到 git 錯誤時，照下面的症狀對照表處理。**先對症，不要亂試。**

## 症狀 1：筆電睡醒後 git push／curl 突然壞掉（憑證或 TLS 憑證錯誤）

WSL2 在筆電睡醒後**時鐘會漂移**，導致 TLS 驗證失敗——錯誤訊息看起來很「玄」（certificate verification failed、token 無效之類），其實只是時間不對。修復：

```bash
sudo hwclock -s        # 校正時鐘
# 或在 Windows PowerShell 執行 wsl --shutdown 再重開
```

驗證：`date` 顯示的時間跟現實一致即修復。**這是本機最常見的 git 玄學問題，睡醒後壞掉先試這個。**

## 症狀 2：push 到 GitHub 失敗、要求輸入帳號密碼、Authentication failed

GitHub 不收密碼，需要透過 GitHub CLI 的憑證。本機已裝好 gh（`~/.local/bin/gh`）：

```bash
gh auth status         # 先看登入了沒
gh auth login          # 沒登入 → 選 GitHub.com → HTTPS → Login with a web browser
gh auth setup-git      # 讓 git 自動使用 gh 的憑證（登入後跑一次）
```

## 症狀 3：`fatal: detected dubious ownership in repository`

跨檔案系統存取 repo（例如從 Windows 側碰 WSL 的 repo）會觸發 git 的所有權保護。確認 repo 路徑無誤後：

```bash
git config --global --add safe.directory <repo絕對路徑>
```

## 症狀 4：repo 放在 /mnt/c 底下各種怪病（慢、權限亂跳、檔案全變 modified）

`/mnt/c` 是 Windows 磁碟掛載，IO 慢、權限模型不合、容易出怪事。**解法不是修，是搬**：把專案移到 Linux 原生路徑（`~/dev/`）。這也是紅茶流水線 T01 的強制規定。

## 症狀 5：沒改內容但 git 顯示整個檔案都變了（行尾 CRLF/LF 問題）

通常是用 Windows 程式直接編輯了 WSL 裡的檔案，寫入了 CRLF 行尾。修復與預防：

```bash
git config --global core.autocrlf input   # commit 時自動轉回 LF
# 預防：編輯 WSL 檔案用 VSCode 的 WSL 模式，不要用 Windows 記事本等程式直接開
```

## 都不是以上症狀？通用診斷順序

```bash
date                          # 1. 時間對不對（症狀 1）
gh auth status                # 2. 憑證在不在（症狀 2）
git remote -v                 # 3. remote 網址對不對（https:// 走 gh 憑證）
git status && git log --oneline -3   # 4. repo 本身狀態
curl -sI https://github.com | head -1  # 5. 網路通不通
```

照順序查，每步有結果再動手修；**不要一次改一堆設定**——改完記不得動過什麼，下次更難查。
