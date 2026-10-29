---
name: agent1-tickets
description: 以結構化工單拆解可驗收工作、檢查依賴並生成工單檢視版。
user-invocable: false
disable-model-invocation: true
---

由 agent1／變更官在規格完成後 Read。寫 `.pipeline/plan/tickets.json`，再用腳本生成 02-workplan.md 與 HTML；不手寫第二份真相。

## 格式

```json
{
  "status": "DRAFT",
  "tickets": [{
    "id": "T01",
    "title": "環境與最小啟動",
    "feature": "基礎建設",
    "description": "確認專案能在隔離測試環境啟動",
    "approach": "依規格檢查工具版本，建立最小啟動與使用說明",
    "files": ["README.md", ".gitignore"],
    "depends_on": [],
    "dod": ["啟動指令與退出條件可由他人重現"],
    "verify": ["依實際技術棧填可執行的驗證命令"],
    "supersedes": []
  }]
}
```

id 可用 T01、T-Rev01a，修復用 fix-<run>-<source>-<attempt>-<batch>。六欄為 feature／description／approach／depends_on／dod／verify；files 是允許修改的相對檔案清單，必須具體列檔，不用整個 src/** 放寬權限。supersedes 只在真正替代舊票時填。

## 檢視版的固定結構（選用欄位，render-plan 照 `~/.claude/blacktea/templates/examples/02-workplan-example.md` 排版）

| 欄位 | 寫什麼 |
|---|---|
| `project` | 專案名（同規格書「專案概述」），HTML 檔名用 |
| `preamble` | `[{heading, body}]`，依序：「缺口總覽」（自我稽核與外部覆核結論、使用者手動驗收項、已知風險）、「使用說明」（票數、輪資料夾、指令目錄、測試不碰真實外部服務的護欄、長駐服務配方；有畫面另寫「UI 票規定」與「截圖配方」，UI 票以「遵守 UI 票規定」引用，不每張重抄）、「功能群與功能文件對照」表 `功能群｜規格書功能（F 編號）｜功能文件` |
| `groups` | `[{name, how}]`，例「一、基礎建設」；`how`＝「這一群怎麼做」白話說整體思路與分幾步 |
| 票的 `group` | 所屬功能群名（必須在 groups 裡） |
| `self_audit` | 「自我稽核結果」表 `#｜項目｜結果`，寫實際做了什麼與數字 |

總表（含依賴欄）由腳本從票面產生，不手抄；body 是 Markdown，2 格縮排的清單會被轉成巢狀。引用其他文件寫章節名＋條目鍵（例：「介面契約」的 A3、J10 第 1e 步、D12），不寫行號。

## 拆票

- 以可獨立驗收的垂直功能切片拆分，不用「30分鐘」猜票大小，也不把一個簡單功能切成大量機械票。
- T01 只檢查實際需要的環境：專案路徑在 Linux 原生檔案系統（不在 `/mnt/c`）、語言版本；UI 才檢查瀏覽器；執行方式是 Docker 才檢查 `docker --version`、`docker compose version`、`docker info`。缺能力寫清楚與解法，不修改使用者全域設定。
- UI 若有重複元件才開共用基座票；只做規格需要的元件，不固定建立 /dev/ui。UI 票截圖需要的後端 API、替身與腳本要列入依賴。
- 執行方式是 Docker：開一張容器化票（`Dockerfile`、`compose.yml`、`.dockerignore`，照規格書「執行方式」小節），排在所有功能票之後、README 票之前。DoD：build 成功、健康檢查回 200、volume 資料在 down／up 後仍在、映像內沒有 `.env`。功能票仍用本機配方驗證，只有容器化票與 README 票走 compose 配方。
- README 票固定最後：install、非互動背景啟動、port 與健康檢查、測試指令；啟動指令與「執行方式」一致（Docker 主指令 `docker compose up -d --build`／`down`，另附本機開發指令），從乾淨狀態實際跑得起來。功能文件依複雜度決定，不強制每功能一份長文。
- 會碰使用者資料的驗證（容器化、README 從乾淨狀態、刪除或覆寫 `.env`／`data/`）一律在隔離副本：另一個 compose 專案名與 port，DoD 加「正式目錄的 `.env`、`data/` 前後相同」。需要真人操作（真實登入、授權）的標「需人工，未執行」。
- files 包含測試與必要文件；依賴只列真正需要的產物。做法給方向與不可破壞的契約，不逐函式鎖死實作。
- DoD 寫可觀察行為及具體預期；修改行為的票不能同時要求該行為逐字不變。不用案例數／行數當品質下限。
- verify 必須非互動、有逾時、可在隔離工作區重現；UI 驗收含實際看圖，無法自動化的部分明列人工／工具步驟，不把檔案存在當成外觀通過。

## 出場檢查

1. `python3 ~/.claude/blacktea/scripts/pipeline.py --root <專案> validate-plan`：ID、欄位、路徑、依賴循環、supersedes。
2. 能用腳本查的寫一次性腳本查，貼輸出當證據：「所屬功能」覆蓋全部 F 編號、每個 A 編號端點被某張票提到、狀態矩陣格數與 UI 票分配相符、DoD 模糊詞（適當／合理／正常／良好／等等）與「待定」零命中。其餘人工對照：旅程覆蓋、DoD 與做法是否矛盾、命令是否可重現、Docker 專案的容器化票與 README 票位置。結果寫進 `self_audit`。重大缺口回訪談，使用者已授權的合理預設可直接補。
3. 修訂時列本輪新票／reopen／supersedes；原依賴不可遺失。替代票不得依賴自己將取代的票。
4. `pipeline.py ... render-plan` 產生檢視版；按政策需要 plan 外部覆核時才 Read `~/.claude/skills/agent1-tickets/references/codex-review.md`。
5. 回 agent1 確認；確認後 status=FINAL，再驗證與產生檢視版。
