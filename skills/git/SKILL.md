---
name: git
description: 遇到 git 相關的錯誤或異常時使用：push 失敗、憑證／TLS 憑證錯誤、GitHub 連不上、要求輸入密碼、dubious ownership、睡醒後 git 突然壞掉等。內含 WSL 環境的診斷順序與修復指令。
---

# Git 問題急救手冊（WSL Ubuntu-24.04 環境）

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
