---
name: git
description: 任何牽涉 git／GitHub 的動作都要先讀本檔。三種時機：(1) 建立新專案或 git init 時——必須先問使用者要不要推 GitHub；(2) 準備 push／建 remote／git commit 後想上傳時——必須先問使用者；(3) 遇到 git 錯誤時——push 失敗、憑證／TLS 錯誤、GitHub 連不上、要求輸入密碼、dubious ownership、睡醒後 git 突然壞掉等，內含 WSL 環境的診斷順序與修復指令。
---

# Git 使用規範與問題急救手冊（WSL Ubuntu-24.04 環境）

本檔分兩部分：**Part A 強制規則**（動手前必讀）、**Part B 問題急救**（出錯時查表）。

---

# Part A：強制規則（不可跳過）

## 規則 1：建立新專案時，必須詢問使用者是否要推到 GitHub

**觸發時機**——只要做到下列任一件事，就必須先問：

- 執行 `git init`
- 建立新專案骨架／腳手架（`npm create`、`cargo new`、`django-admin startproject` 等）
- 紅茶流水線 T01 建立專案目錄時
- 使用者說「開一個新專案」「幫我做一個 XXX」而該專案還沒有 repo

**要問清楚三件事，一次問完，不要分三輪：**

1. 要不要建 GitHub repo？（要／不要）
2. 私有還是公開？——**預設建議私有**，公開要使用者明確選
3. repo 名稱要叫什麼？（可提供建議名讓他確認）

**規則細節：**

- **不准自作主張執行 `gh repo create`。** 沒問過就建 repo = 違規，即使你覺得「一定會想要」。
- 使用者說「不要」→ 只做本機 `git init`，**不建 remote，之後不要再重複問**同一個專案。
- 使用者說「要」→ 建完 repo 後，第一次 push 仍然適用規則 2（要再問一次）。
- 公開 repo 前**必須**跑一次下面的敏感檔檢查，並把結果講給使用者聽再讓他決定。

## 規則 2：每一次 push 前都要詢問使用者

**每一次都要問。「上次同意過」不算這次同意。**

**適用範圍**——下列全部都算 push，全部都要先問：

- `git push`、`git push -u origin <branch>`
- `git push --force` / `--force-with-lease`（這種更要問，且要講清楚會覆蓋什麼）
- `gh repo create --push`、`gh repo create --source=.`（含隱含 push 的）
- 推 tag：`git push --tags`
- 推到任何非 origin 的 remote

**問的時候要一併講清楚（讓使用者有資訊可判斷）：**

- 推去哪：remote 名稱 + URL + 目標 branch
- 推什麼：幾個 commit、動到哪些檔案
- repo 是公開還是私有
- 敏感檔檢查結果（見下）

**唯一例外：** 使用者這一輪自己主動說「push」「推上去」「上傳」——那句話本身就是指示，直接做，不用再問一次。但**下一次 push 仍要重新問**。

**絕對不要：** 為了「順手」「反正做完了」「怕使用者忘記」而自行 push。沒問就推 = 違規。

## push 前的敏感檔檢查（規則 1、2 共用）

推之前一定要跑，結果講給使用者聽：

```bash
# 1. 看清楚到底會推什麼上去
git status
git log --oneline origin/<branch>..HEAD     # 尚未推送的 commit
git diff --stat origin/<branch>..HEAD       # 動到哪些檔案

# 2. 檢查追蹤中的檔案有沒有機密
git ls-files | grep -iE 'credential|token|secret|\.env|\.pem|id_rsa|hosts\.yml|\.key$'

# 3. 檢查 commit 內容有沒有夾帶金鑰字串
git diff origin/<branch>..HEAD | grep -iE 'api[_-]?key|secret|password|ghp_|sk-[a-zA-Z0-9]{20}'
```

**任何一項有命中 → 停下來，先講給使用者聽，不要推。**

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
