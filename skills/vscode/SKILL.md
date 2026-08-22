---
name: vscode
description: VS Code 檔案總管右鍵整合急救(Windows 端)。使用者回報這幾類問題時讀本檔:右鍵沒有「以 Code 開啟」、只有資料夾空白處有而點資料夾本身沒有、右鍵開 WSL 資料夾(\\wsl.localhost\...)後還要手動點左下角「連線至 WSL」、或 VS Code 更新後右鍵行為跑掉。內含全套修復指令(WSL 終端機直接可跑)、一鍵連 WSL 的轉接器 vbs 備份與整條鏈驗證;2026-08-20 整套發生並修復、2026-08-22 連 WSL 的 command 被更新蓋掉再修復一次。
---

# VS Code 右鍵整合急救手冊(Windows 端)

特徵:壞的都在 Windows 端(登錄檔、選單、VS Code),WSL 本身沒事;所有指令直接在 WSL 終端機執行即可(reg.exe 透過 interop 寫 Windows 登錄檔,免系統管理員)。改完不用重開機,右鍵立即生效。

本機環境:Windows 11 25H2、VS Code 使用者層級安裝(`C:\Users\peter\AppData\Local\Programs\Microsoft VS Code`)、WSL 發行版 `Ubuntu-24.04`。

## 症狀 1:檔案總管右鍵沒有「以 Code 開啟」

成因:VS Code 自動更新會照安裝程式的工作紀錄重裝,「加入右鍵選單」記成未勾選時,更新會把 HKCU 的右鍵登錄鍵整組清掉。

診斷——查無此鍵就是中了:

```bash
reg.exe query 'HKCU\Software\Classes\Directory\shell\VSCode' /s
```

修復(三組:點資料夾本身/資料夾空白處/點檔案),command 直接指向症狀 3 的轉接器;最後兩行補正安裝工作紀錄防復發:

```bash
W='C:\Windows\System32\wscript.exe'
V='C:\Users\peter\.vscode\open-with-code.vbs'   # 轉接器不在了 → 先看症狀 3 修復 A 復原
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

## 症狀 2:空白處右鍵有「以 Code 開啟」,點資料夾本身卻沒有

不是壞掉:Win11 新式選單只在「空白處/桌面」直接顯示傳統項目,點「資料夾/檔案本身」時全部收進「顯示其他選項」,重開機也不會變。要第一層直接顯示就切回傳統選單(本機已於 2026-08-20 切換):

```bash
reg.exe add 'HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32' /ve /f
powershell.exe -NoProfile -Command "Stop-Process -Name explorer -Force"   # explorer 會自動重啟
```

想改回新式選單:`reg.exe delete 'HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}' /f`,再重啟一次 explorer。

## 症狀 3:右鍵開 WSL 資料夾後,還要手動點左下角「連線至 WSL」

### 為什麼要轉接器

VS Code 的 WSL 擴充沒有「開 `\\wsl.localhost\` 路徑就自動連線」的設定(0.104.3 全部設定翻過)。預設右鍵 command 是 `"Code.exe" "%V"`,對 WSL 路徑只會用本機模式開 UNC 路徑,所以要再手動按左下角「連線至 WSL」。

解法是轉接器 `C:\Users\peter\.vscode\open-with-code.vbs`:偵測到 `\\wsl.localhost\<發行版>\...` 或 `\\wsl$\...`,就改成 `Code.exe --remote wsl+<發行版> <Linux路徑>` 啟動,一開就是連好的;其他路徑照舊本機開。右鍵的三個 command 鍵都要指到它。

### 診斷(WSL 終端機直接跑)

```bash
# 三個 command 都應該是 wscript.exe + open-with-code.vbs;看到 "Code.exe" "%V" 就是被蓋回預設
reg.exe query 'HKCU\Software\Classes\Directory\shell\VSCode\command' /ve
reg.exe query 'HKCU\Software\Classes\Directory\Background\shell\VSCode\command' /ve
reg.exe query 'HKCU\Software\Classes\*\shell\VSCode\command' /ve
# 轉接器在不在、跟備份一不一樣
cmp /mnt/c/Users/peter/.vscode/open-with-code.vbs ~/.claude/skills/vscode/open-with-code.vbs && echo same
```

查無 `VSCode` 鍵(整組不見)→ 是右鍵選單被清掉,先照症狀 1 處理,它的修復指令本來就會指到轉接器。

### 修復 A:轉接器遺失或內容不對

本資料夾備有一份 [open-with-code.vbs](open-with-code.vbs),直接複製回去(行尾必須 CRLF;repo 已用 `.gitattributes` 的 `*.vbs -text` 鎖住不轉換):

```bash
mkdir -p /mnt/c/Users/peter/.vscode
cp ~/.claude/skills/vscode/open-with-code.vbs /mnt/c/Users/peter/.vscode/open-with-code.vbs
```

### 修復 B:command 被改回 `"Code.exe" "%V"`(最常見,VS Code 更新後)

```bash
W='C:\Windows\System32\wscript.exe'
V='C:\Users\peter\.vscode\open-with-code.vbs'
reg.exe add 'HKCU\Software\Classes\Directory\shell\VSCode\command' /ve /d "\"$W\" \"$V\" \"%V\"" /f
reg.exe add 'HKCU\Software\Classes\Directory\Background\shell\VSCode\command' /ve /d "\"$W\" \"$V\" \"%V\"" /f
reg.exe add 'HKCU\Software\Classes\*\shell\VSCode\command' /ve /d "\"$W\" \"$V\" \"%1\"" /f
# 補正安裝工作紀錄,降低下次更新再蓋掉的機率
reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{771FD6B0-FA20-440A-A002-3B3BAC16DC50}_is1' /v 'Inno Setup: Selected Tasks' /d 'addcontextmenufiles,addcontextmenufolders,associatewithfiles,addtopath,runcode' /f
reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{771FD6B0-FA20-440A-A002-3B3BAC16DC50}_is1' /v 'Inno Setup: Deselected Tasks' /d 'desktopicon' /f
```

(reg.exe 回應的亂碼是 CP950 的「操作順利完成」,不是錯誤。)

## 整條鏈驗證

```bash
cscript.exe //NoLogo 'C:\Users\peter\.vscode\open-with-code.vbs' '\\wsl.localhost\Ubuntu-24.04\home\peter'
```

跳出的 VS Code 視窗左下角顯示 `WSL: Ubuntu-24.04` 即全部正常。

## 已知風險

VS Code 自動更新重跑安裝程式時,可能把三個 command 鍵值改回預設 `"Code.exe" "%V"`——症狀是右鍵還能開,但又變回要手動連 WSL;轉接器本身不會被動到,重跑症狀 3 修復 B 即可。(2026-08-22 實際發生一次,重跑後即修復。)
