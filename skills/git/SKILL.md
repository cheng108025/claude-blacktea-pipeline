---
name: git
description: 任何牽涉 git／GitHub 的動作都要先讀本檔。三種時機：(1) 建立新專案或 git init 時——必須先問使用者要不要推 GitHub（一個專案只問這一次，答應了就長期有效）；(2) 準備 push／建 remote 時——查專案有沒有先授權（`.pipeline/plan/git-policy.md` 或使用者答應過）：有就直接推並回報推了哪幾張票，沒有就先問；force push／推 tag／改公開一律要再問；(3) 遇到 git 錯誤時——push 失敗、憑證／TLS 錯誤、GitHub 連不上、要求輸入密碼、dubious ownership、睡醒後 git 突然壞掉等，內含 WSL 環境的診斷順序與修復指令;(4) VS Code 檔案總管右鍵問題——「以 Code 開啟」不見了、只剩空白處有、或開 WSL 資料夾還要手動點連線,修復指令在 Part C(2026-08-20 整套修過一次)。
---

# Git 使用規範與問題急救手冊（WSL Ubuntu-24.04 環境）

本檔分三部分：**Part A 強制規則**（動手前必讀）、**Part B git 問題急救**（出錯時查表）、**Part C VS Code 右鍵整合急救**（檔案總管右鍵相關）。

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
- 敏感檔檢查有命中（見下）——**有授權也要停下來先講給使用者聽**。
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

---

# Part C:VS Code 右鍵整合急救(Windows 端)

2026-08-20 整套發生並修復過一次。特徵:壞的都在 Windows 端(登錄檔、選單、VS Code),WSL 本身沒事;所有指令直接在 WSL 終端機執行即可(reg.exe 透過 interop 寫 Windows 登錄檔,免系統管理員)。改完不用重開機,右鍵立即生效。

## 症狀 C1:檔案總管右鍵沒有「以 Code 開啟」

成因:VS Code 自動更新會照安裝程式的工作紀錄重裝,「加入右鍵選單」記成未勾選時,更新會把 HKCU 的右鍵登錄鍵整組清掉。

診斷——查無此鍵就是中了:

```bash
reg.exe query 'HKCU\Software\Classes\Directory\shell\VSCode' /s
```

修復(三組:點資料夾本身/資料夾空白處/點檔案),command 直接指向 C3 的轉接器;最後兩行補正安裝工作紀錄防復發:

```bash
W='C:\Windows\System32\wscript.exe'
V='C:\Users\peter\.vscode\open-with-code.vbs'   # 轉接器不在了 → 先看 C3 復原
C='C:\Users\peter\AppData\Local\Programs\Microsoft VS Code\Code.exe'
reg.exe add 'HKCU\Software\Classes\Directory\shell\VSCode' /ve /d '以 Code 開啟' /f
reg.exe add 'HKCU\Software\Classes\Directory\shell\VSCode' /v Icon /d "$C" /f
reg.exe add 'HKCU\Software\Classes\Directory\shell\VSCode\command' /ve /d "\"$W\" \"$V\" \"%V\"" /f
reg.exe add 'HKCU\Software\Classes\Directory\Background\shell\VSCode' /ve /d '以 Code 開啟' /f
reg.exe add 'HKCU\Software\Classes\Directory\Background\shell\VSCode' /v Icon /d "$C" /f
reg.exe add 'HKCU\Software\Classes\Directory\Background\shell\VSCode\command' /ve /d "\"$W\" \"$V\" \"%V\"" /f
reg.exe add 'HKCU\Software\Classes\*\shell\VSCode' /ve /d '以 Code 開啟' /f
reg.exe add 'HKCU\Software\Classes\*\shell\VSCode' /v Icon /d "$C" /f
reg.exe add 'HKCU\Software\Classes\*\shell\VSCode\command' /ve /d "\"$W\" \"$V\" \"%1\"" /f
reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{771FD6B0-FA20-440A-A002-3B3BAC16DC50}_is1' /v 'Inno Setup: Selected Tasks' /d 'addcontextmenufiles,addcontextmenufolders,associatewithfiles,addtopath,runcode' /f
reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{771FD6B0-FA20-440A-A002-3B3BAC16DC50}_is1' /v 'Inno Setup: Deselected Tasks' /d 'desktopicon' /f
```

## 症狀 C2:空白處右鍵有「以 Code 開啟」,點資料夾本身卻沒有

不是壞掉:Win11 新式選單只在「空白處/桌面」直接顯示傳統項目,點「資料夾/檔案本身」時全部收進「顯示其他選項」,重開機也不會變。要第一層直接顯示就切回傳統選單(本機已於 2026-08-20 切換):

```bash
reg.exe add 'HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32' /ve /f
powershell.exe -NoProfile -Command "Stop-Process -Name explorer -Force"   # explorer 會自動重啟
```

想改回新式選單:`reg.exe delete 'HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}' /f`,再重啟一次 explorer。

## 症狀 C3:右鍵開 WSL 資料夾後,還要手動點左下角「連線至 WSL」

WSL 擴充沒有自動連線設定(0.104.3 全部設定翻過),解法是轉接器 `C:\Users\peter\.vscode\open-with-code.vbs`:偵測到 `\\wsl.localhost\` 或 `\\wsl$\` 路徑,就改用 `Code.exe --remote wsl+<發行版> <Linux路徑>` 啟動,一開就是連好的;其他路徑照舊本機開。右鍵 command 要指到它——正確值就是 C1 修復指令那一套。

轉接器遺失時的復原:本資料夾備有一份 [open-with-code.vbs](open-with-code.vbs),直接複製回去:

```bash
cp ~/.claude/skills/git/open-with-code.vbs /mnt/c/Users/peter/.vscode/open-with-code.vbs
```

(行尾必須是 CRLF;repo 這份已用 .gitattributes 的 `*.vbs -text` 鎖住不轉換,直接複製即可。)

## 整條鏈驗證

```bash
cscript.exe //NoLogo 'C:\Users\peter\.vscode\open-with-code.vbs' '\\wsl.localhost\Ubuntu-24.04\home\peter'
```

跳出的 VS Code 視窗左下角顯示 `WSL: Ubuntu-24.04` 即全部正常。

## 已知風險

VS Code 自動更新重跑安裝程式時,可能把三個 command 鍵值改回預設 `"Code.exe" "%V"`——症狀是右鍵還能開,但又變回要手動連 WSL。重跑 C1 的修復指令即可。
