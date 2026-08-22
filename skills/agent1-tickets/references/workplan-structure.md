# 工作單的組成（02-workplan.md，照這個順序寫）

1. **檔首**：「> 狀態：DRAFT」——這是建造階段（`~/.claude/skills/blacktea-dispatch/SKILL.md`）的門禁：看到 DRAFT 就拒絕開工。只有 Phase E 使用者點頭後才拿掉，並寫上定稿日期。
2. **T01 環境檢查**（固定第一張，「基礎建設」）：
   - **專案路徑在 Linux 原生檔案系統**（例：`~/dev/專案名`），**不在 `/mnt/c` 底下**（那是 Windows 磁碟掛載，IO 慢且檔案監看不可靠）；路徑不含空白。
   - node／python 版本符合規格書。
   - web 專案：Playwright MCP 可用（專案根目錄的 `.mcp.json` 含 playwright（腳印已內建），或 `claude mcp list` 看得到；都沒有就標 BLOCKED，附解法：從 `~/.claude/blacktea/templates/mcp.json` 複製，或跑 `claude mcp add playwright -- npx -y @playwright/mcp@latest --output-dir .pipeline/evidence`）。
   - **核對 `.gitignore`** 🔧：`git init` 與首 commit 由調度技能在派 T01 之前完成，`.gitignore` 也由它依本清單先建好；T01 負責核對內容至少含 `.env`、`node_modules/`、`.pipeline/evidence/`、`.pipeline/state.md`、`.pipeline/server.pid`、`.pipeline/03-build-log.md`、`.pipeline/build-log/`、`.pipeline/ticket-checks/`、`.pipeline/04-verify-report.md`、`.pipeline/05-e2e-report.md`，缺的補上。
   - T01 本身不執行任何 git 指令（建造者一律不碰 git）。
3. **功能 tickets**：照依賴排順序、編號連續、每張可勾選（`- [ ]`）。**每個功能的最後一張 ticket，完成條件必須包含「`docs/features/<功能名>.md` 已撰寫」**——給人看的功能說明書，固定格式：這功能做什麼（白話）、怎麼使用、由哪些檔案組成、資料怎麼流、對應哪些 ticket。
4. **README ticket**（固定最後一張，「基礎建設」）：install 指令、**不需要人工介入的背景啟動指令**、port 與健康檢查網址、測試指令、測試資料說明（如有）。完成條件：照 README 從乾淨狀態實際跑得起來。稽核員與實測員的啟動全靠它。
5. **文末聲明**：「全域驗收清單以 `01-requirements.md` 的『全域驗收清單』章為唯一來源」——只引用、不複製，避免改需求時兩份清單不同步。

（文件分工：README 管「怎麼把專案跑起來」，feature md 管「每個功能怎麼運作」。）
