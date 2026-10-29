---
name: git
description: Git／GitHub 操作的授權、提交與推送檢查；故障時按需讀診斷手冊。
---

## 授權

- 本機 Git 操作依使用者任務執行；新專案未決定 GitHub 時，先問只留本機或建立 repo，選 GitHub 後才問可見性與名稱。
- 已有 `.pipeline/plan/git-policy.md` 或本專案明確授權就沿用。核對 remote URL、branch、private/public，不逐票重問。
- 未授權 GitHub 就不建 repo／不 push。force push、tag、新目的地、改公開需要對應明確授權，不能從一般 push 授權推論。
- 流水線只有 dispatch 執行 Git 寫入。程式碼必須有獨立票級 receipt，規格／報告的單 commit 不夾帶實作。

## 每次 push

1. 核對目標與政策；先更新授權 remote 的分支資訊。可用 `git ls-remote --heads <remote> refs/heads/<branch>` 判斷分支存在；存在就 fetch 指定分支，取得精確 SHA 作為 base。連線／fetch 失敗則延後，不能當成首次推送。
2. `python3 ~/.claude/blacktea/scripts/scan_push.py --root <repo> --base <fresh-remote-sha>`；首次推送且確認遠端分支不存在時省略 --base，掃 HEAD 所有可達歷史。腳本逐 commit tree 掃描，不只看最終 diff。
3. exit 0＝本機啟發式規則未命中；exit 1＝疑似機密；exit 2＝未完成掃描（helper 缺失、超大 blob、巢狀 repo、Git 出錯都算）。後兩者都不推。輸出只記 commit／path／rule，不把金鑰內容抄到報告。規則涵蓋敏感檔名、常見 token、前後綴憑證賦值（含跨行 JSON／YAML 值）；放行看整個值是否全為佔位字詞，範本檔全空才不算敏感檔。短值等已知取捨寫在 `~/.claude/blacktea/tests/test_push_scan.py`。此掃描不是完整機密偵測；有組織既有 scanner 就一併依其規定執行。
4. 預備 push 的 HEAD 必須仍與掃描結果相同，否則重掃。推明確 branch，不附 tags／force。完成回報 repo、branch、commit 範圍。

流水線命中／掃描失敗：用 `pipeline.py --root <專案> push-state --status PAUSED --reason <原因>` 記錄；每次 push 前先讀 state.push，PAUSED 時不推；之後含 docs 的所有 push 都暫停，只保留本機 commit，結案列處理事項。使用者決定解除且重新掃描通過後，才可 `push-state --status READY --reason <決策與掃描證據>`。修改最終檔案不會清除歷史機密；不得自行改寫使用者歷史或輪換憑證。

一般非流水線操作：命中就向使用者報告位置與處理選項。沒有新證據前不反覆重推。

## 故障

只有發生 Git／WSL 問題時讀 `~/.claude/skills/git/references/troubleshooting.md`。一次驗證一個原因，修復不得擴大既有授權。
