---
name: clawd
description: Clawd on Desk 桌面寵物急救(Windows 端第三方程式,靠 Claude Code hooks 回報)。使用者回報這幾類問題時讀本檔:寵物在 Claude 工作時沒動畫／沒反應、寵物看不到 WSL 裡的 session、Clawd 設定頁「掃描 WSL」後找不到配對選項、配對後還是沒動、或 Claude Code／Clawd 更新後寵物壞掉。內含診斷順序、WSL 配對步驟與驗證指令(WSL 終端機直接可跑);2026-08-22 整套發生並修復過一次。
---

# Clawd on Desk 桌面寵物急救手冊

## 先搞清楚它是什麼

寵物**不是** Claude Code 內建功能(`/buddy` 或 VS Code 擴充裡的 clawd.svg 都無關),是第三方 Electron 程式 **Clawd on Desk**(<https://github.com/rullerzhou-afk/clawd-on-desk>):

- 安裝位置:`C:\Users\peter\AppData\Local\Programs\Clawd on Desk\`
- hook 腳本來源:`...\resources\app.asar.unpacked\hooks\`(`clawd-hook.js`、`install.js`、`wsl-connectivity-probe.js`)
- 使用者資料/設定/log:`C:\Users\peter\AppData\Roaming\clawd-on-desk\`(`clawd-prefs.json`、`session-debug.log`)
- 執行中狀態:`C:\Users\peter\.clawd\runtime.json`(`port`,預設 23333;`ownerPid`)

**運作原理**:Claude Code 每個 hook 事件(SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/Stop/Subagent*…)執行 `node clawd-hook.js <事件>`,它 HTTP POST 到 **Windows 端** `127.0.0.1:23333~23337/state`,寵物才依事件播動畫。

**關鍵事實**:Windows 與 WSL 各有一份 `~/.claude/settings.json`,hooks 互不相通。
- Windows 端 `C:\Users\peter\.claude\settings.json`:Clawd 安裝時自動寫入。
- WSL 端 `/home/peter/.claude/settings.json`:要另外「配對」才會有。VS Code 擴充套件(`CLAUDE_CODE_ENTRYPOINT=claude-vscode`)跑的是 WSL 裡的 Linux 二進位,讀的是這一份。

## 診斷順序(WSL 終端機直接跑)

```bash
# 1. 寵物程式有沒有在跑、聽哪個 port
tasklist.exe | grep -i clawd | head -3
cat /mnt/c/Users/peter/.clawd/runtime.json

# 2. WSL 端 hooks 有沒有裝(沒裝 → 症狀 1)
grep -c clawd-hook ~/.claude/settings.json      # 期望 ≥ 10;0 或檔案沒 hooks 就是沒裝
ls ~/.claude/hooks/clawd-hook.js

# 3. WSL 打不打得到 Windows 的寵物 server(不通 → 症狀 2)
wslinfo --networking-mode                       # 期望 mirrored;nat 一定不通
node ~/.claude/hooks/wsl-connectivity-probe.js  # 期望 REACHABLE 23333

# 4. 寵物有沒有真的收到事件(用目前 session id 查)
grep -a "$CLAUDE_CODE_SESSION_ID" "/mnt/c/Users/peter/AppData/Roaming/clawd-on-desk/session-debug.log" | tail -3
```

## 症狀 1:WSL 端沒有 hooks(寵物對 VS Code／WSL 裡的 Claude 完全沒反應)

用 Clawd 內建的一鍵配對。**結果不是顯示在按鈕旁邊,而是收在 Claude Code 那一列的摺疊區裡(預設收合)**——2026-08-22 就是因為這樣被誤判成「沒有選項」:

1. 右鍵寵物或系統匣圖示 → 設定 → **Agents** 分頁。
2. 上方按 **「掃描 WSL」**,等「掃描中...」結束。
3. 往下到 **「已接入」** 區塊,**點 Claude Code 那一列的標題**(不是開關)展開。
4. 最底下 **「實例」** 段會出現 `WSL: Ubuntu-24.04`,按右邊 **「配對」**。
5. 出現「配對成功」→ 該列多一個綠色「已部署 hooks」徽章。

配對會做:在 WSL 建 `~/.claude/hooks/` 複製全部腳本 → 用 `bash -l -i -c` 跑 `CLAWD_WSL_DISTRO=Ubuntu-24.04 node install.js`(login shell 才找得到 nvm 的 node)→ 合併寫入 15 個 hook 事件 + statusLine 到 WSL `settings.json`(不會動既有的 `effortLevel`／`model`)→ 跑連線探測。

`WSL: Ubuntu-24.04` 那一列本來就只有「配對／取消配對」,沒有獨立設定;權限泡泡、子代理、閒置提醒等開關在 Claude Code 卡片層級,Windows 與 WSL 的 session 共用。

掃描後真的沒出現 Claude Code 的「實例」段時,可在 WSL 重演程式的掃描條件,三項都要成立:
```bash
wsl.exe -l -q | tr -d '\0\r'                                   # 要列出 Ubuntu-24.04
wsl.exe -d Ubuntu-24.04 -- bash -c 'echo $HOME' | tr -d '\0\r'  # 要印 /home/peter
test -d /home/peter/.claude && echo OK                          # 要 OK
```

## 症狀 2:hooks 裝了但打不到寵物(配對時跳「已配對,但該發行版無法存取 Clawd——WSL 的 NAT 網路不互通 localhost」)

WSL2 預設 NAT 模式下,WSL 的 `127.0.0.1` 不是 Windows 的;寵物 server 只綁 Windows loopback,所以一定不通。唯一解法是 mirrored 網路(本機 WSL 2.7.8 + Windows 26200 支援,2026-08-22 已切換):

```bash
# 寫 .wslconfig(已存在就先 cat 看內容,別蓋掉別的設定)
printf '[wsl2]\r\nnetworkingMode=mirrored\r\n' > /mnt/c/Users/peter/.wslconfig
```
然後**使用者自己**在 Windows PowerShell 跑 `wsl --shutdown`(會斷掉所有 WSL 視窗與 VS Code 連線,Claude 對話要 `claude --resume` 接回),重開後 `wslinfo --networking-mode` 應為 `mirrored`、探測應為 `REACHABLE 23333`。

## 症狀 3:配對與網路都正常,寵物還是不動

- Claude Code 只在 **session 啟動時**讀 hooks:配對前就開著的對話要重開才會回報;新開的對話才算數。
- 寵物程式沒在跑或 `runtime.json` 的 `ownerPid` 已死 → 重啟 Clawd on Desk。
- `session-debug.log` 有收到事件但沒動畫 → 檢查 Clawd 設定裡 Claude Code 的主開關、勿擾模式。

## 手動部署(一鍵配對壞掉時的備案)

```bash
S="/mnt/c/Users/peter/AppData/Local/Programs/Clawd on Desk/resources/app.asar.unpacked/hooks"
mkdir -p ~/.claude/hooks && cp "$S"/*.js ~/.claude/hooks/
cd ~/.claude/hooks && CLAWD_WSL_DISTRO=Ubuntu-24.04 node install.js
node ~/.claude/hooks/wsl-connectivity-probe.js
```
不要直接在 `/mnt/c/...Clawd on Desk/...` 路徑下跑 `install.js`:WSL 模式產生的 hook 指令不加引號,路徑含空白會壞。

## 已知風險

- Claude Code 或 Clawd 更新可能重寫 `settings.json`,WSL 端 hooks 被清掉 → 重做症狀 1 的配對即可(Clawd 有「自動管理 Claude hooks」會修 Windows 端,但不會修 WSL 端)。
- mirrored 模式改變 WSL 網路行為(與 Windows 共用 port);之後遇到 port 衝突或 VPN 異常先懷疑它。
- 相關:VS Code 右鍵開 WSL 資料夾的問題看 `vscode` 技能。
