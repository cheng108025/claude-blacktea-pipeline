---
name: agent1-tickets
description: 訪談官技能 c「照規格書拆任務」——Phase D，出 02-workplan.md 工作單、自我稽核 7 項、可選 Codex 覆核。由 ~/.claude/agents/agent1_plan.md 接力讀取，不單獨使用。
user-invocable: false
disable-model-invocation: true
---

> 門牌：訪談官技能 c。由 `~/.claude/agents/agent1_plan.md` 在規格書寫完後 Read 本檔照做，跑在主對話。Ticket 格式、工作單組成、自我稽核清單都在本檔；Codex 覆核（可選）在 `references/codex-review.md`。旋鈕（票要多小、.gitignore 清單、追問輪數）與設計理由見 `~/.claude/agents/README.md`。

# 訪談官技能 c：照規格書拆任務（.pipeline/plan/02-workplan.md）

- **前提**：`01-requirements.md` 已寫完且沒有任何「待定」。不符合 → 停，回報「請先完成規格書（agent1-spec）」。
- **產出**：`02-workplan.md`（檔首「> 狀態：DRAFT」）、自我稽核 7 項結果、外部覆核結果（依重度／中度／輕度分組）；完成後回到 `agent1_plan.md` 接力 Phase E。

工作單的單位是 **ticket**：一張 ticket ＝ 一項獨立、可勾選、可驗證的工作。每個需要做的項目都要分別列成一張——不准把好幾件事塞進同一張。

## 流程

1. 照下面「Ticket 格式」與「工作單的組成」寫出全部 ticket。
2. 逐張套用「每張 ticket 的品質要求」。
3. 照「自我稽核（7 項）」逐條做完並展示結果；待問清單不空就回去追問（最多 2 輪 🔧）。
4. Read `~/.claude/skills/agent1-tickets/references/codex-review.md`，問使用者要不要外部覆核；有跑就依分級處理，重度缺口處理完才能交棒。
5. 回到 `~/.claude/agents/agent1_plan.md`，接力 Phase E（產 HTML、請使用者確認、定稿）。

## Ticket 格式（每張六欄，缺一不可）

編號規則：從 `T01` 開始、照施工順序依序編號（T01、T02、T03…）；需求變更追加的票用 `T-Rev01`、`T-Rev02`。

虛構範例（會員系統，前面已有 T01 環境檢查、T02 建資料表；登入 API 要先有資料表，所以「依賴」填 T02）：

```markdown
## T03 使用者登入 API
- 所屬功能: 帳號系統
- 內容: POST /api/login，驗證帳密、簽發 session cookie
- 做法: 在 src/routes/auth.js 新增路由；用 bcrypt 比對密碼雜湊；用 express-session 簽發 cookie
- 依賴: T02
- 完成條件(DoD): 正確帳密回 200 + Set-Cookie；錯誤帳密回 401（依規格書「介面契約」）
- 驗證方式: 背景啟動 server → curl -s -o /dev/null -w "%{http_code}"
  -X POST http://localhost:3000/api/login -d "..." 應輸出 200 → 停止 server
```

| 欄位 | 是什麼 |
|---|---|
| 所屬功能 | 對應規格書「功能清單」章的哪一項（環境檢查、README 這類記「基礎建設」） |
| 內容 | 這張票要完成**什麼** |
| 做法 | **怎麼**做：用什麼套件或方式，**並且必須明確列出會動到的檔案**——使用者靠它看懂工作內容，建造者拿它當實作指引，調度技能靠檔案清單判斷哪些票可以並行、票級檢查靠它核對建造者有沒有動到不該動的檔 |
| 依賴 | 要先做完哪張票才能做這張。**只有後票真的需要前票的產物才建依賴**——不得因為編號順序、共用唯讀程式碼就建（假依賴會害無關的票不能並行） |
| 完成條件(DoD) | 怎樣算做完——必須可以直接判對錯；票級檢查會逐條驗 |
| 驗證方式 | 用哪條指令證明完成條件成立；建造者自己跑一次，票級檢查再獨立跑一次 |

## 工作單的組成（照這個順序寫）

1. **檔首**：「> 狀態：DRAFT」——這是建造階段（調度技能）的門禁：看到 DRAFT 就拒絕開工。只有 Phase E 使用者點頭後才拿掉，並寫上定稿日期與兩份文件一致的唯一規格版本（同日修訂也不同）。
2. **T01 環境檢查**（固定第一張，「基礎建設」）：
   - **專案路徑在 Linux 原生檔案系統**（例：`~/dev/專案名`），**不在 `/mnt/c` 底下**（那是 Windows 磁碟掛載，IO 慢且檔案監看不可靠）；路徑不含空白。
   - node／python 版本符合規格書。
   - web 專案：Playwright MCP 可用（專案根目錄的 `.mcp.json` 含 playwright（腳印已內建），或 `claude mcp list` 看得到；都沒有就標 BLOCKED，附解法：從 `~/.claude/blacktea/templates/mcp.json` 複製，或跑 `claude mcp add playwright -- npx -y @playwright/mcp@latest --output-dir .pipeline/mcp-output`）。另確認 Playwright **CLI** 截圖能跑：`~/.cache/ms-playwright/` 底下有 chromium，沒有就 `npx -y playwright install chromium`（基座票與 UI 票的驗證方式靠它截圖）。
   - **核對 `.gitignore`** 🔧：`git init` 與首 commit 由調度技能在派 T01 之前完成，`.gitignore` 也由它依本清單先建好；T01 負責核對內容至少含 `.env`、`node_modules/`、`.pipeline/rounds/`、`.pipeline/mcp-output/`、`.pipeline/evidence/`、`.pipeline/state.md`、`.pipeline/state-history.md`、`.pipeline/server.pid`、`.pipeline/03-build-log.md`、`.pipeline/build-log/`、`.pipeline/ticket-checks/`、`.pipeline/04-verify-report.md`、`.pipeline/05-e2e-report.md`，缺的補上。
   - 規格書「執行方式」是 Docker 打包 → 另檢查 `docker --version`、`docker compose version` 都能跑、daemon 在線（`docker info` 退出碼 0）；不通就標 BLOCKED，附解法（安裝 Docker Desktop 並開啟 WSL 整合）。
   - T01 本身不執行任何 git 指令（建造者一律不碰 git）。
2b. **設計系統基座票**（有畫面的專案固定一張，「基礎建設」，排在第一張 UI 票之前、所有 UI 票都依賴它）：
   - 做法：安裝技術棧表的「UI 樣式方案」；把「設計系統」章的 token 寫進 CSS 變數或框架設定；建立共用元件（章內元件清單的每一個，含各變體與 disabled／錯誤態）；做一個開發用展示頁 `/dev/ui`（每個元件各狀態一排；這頁是「本版不做」的合法例外，標「開發用」）。
   - DoD：展示頁截圖 `<R>/evidence/TXX-ui.png` 存在且每個元件各狀態可見；token 只定義在一處；共用元件有最小測試（render 不爆）。
   - 驗證方式：背景起 dev server → `npx -y playwright screenshot --viewport-size=1280,800 http://localhost:<port>/dev/ui <R>/evidence/TXX-ui.png`（或等效 node 腳本）→ 關閉。
   - **票面的 evidence 路徑寫實際路徑**：`<R>`＝本輪資料夾——`/blacktea_plan` 開的票一律寫 `.pipeline/rounds/01`；`/blacktea_change` 開的 T-Rev 票寫 state.md「目前輪資料夾」的值（例 `.pipeline/rounds/02-T-Rev01`）。票面不留 `<R>` 字樣。
2c. **容器化票**（規格書「執行方式」是 Docker 打包才有，固定一張，「基礎建設」；排在所有功能票**之後**、README 票之前，README 票依賴它——Dockerfile 要 COPY 完整專案，所以不能早於功能票）：
   - 做法：新增 `Dockerfile`、`compose.yml`、`.dockerignore`，內容照規格書「執行方式」小節（基底映像、port 對應、volume、`env_file`、健康檢查）。
   - DoD：`docker compose build` 退出碼 0；`docker compose up -d` 後健康檢查網址回 200；掛 volume 的資料在 `docker compose down` → `up -d` 後仍在；映像裡沒有 `.env`（`docker compose run --rm <service> ls -a <工作目錄>` 輸出不含 `.env`）。
   - 驗證方式：`docker compose up -d --build` → 輪詢 `curl` 健康檢查 → 驗證 → `docker compose down` → 確認 port 已釋放。
3. **功能 tickets**：照依賴排順序、編號連續、每張可勾選（`- [ ]`）。**每個功能的最後一張 ticket，完成條件必須包含「`docs/features/<功能名>.md` 已撰寫」**——給人看的功能說明書，固定格式：這功能做什麼（白話）、怎麼使用、由哪些檔案組成、資料怎麼流、對應哪些 ticket。
4. **README ticket**（固定最後一張，「基礎建設」）：install 指令、**不需要人工介入的背景啟動指令**、port 與健康檢查網址、測試指令、測試資料說明（如有）。啟動指令必須與規格書「執行方式」一致：本機 → 背景啟動指令；Docker 打包 → 主指令是 `docker compose up -d --build`／`docker compose down`，並另附一段「不用 Docker 的本機開發指令」。完成條件：照 README 從乾淨狀態實際跑得起來。稽核員與實測員的啟動全靠它。
5. **文末聲明**：「全域驗收清單以 `01-requirements.md` 的『全域驗收清單』章為唯一來源」——只引用、不複製，避免改需求時兩份清單不同步。

（文件分工：README 管「怎麼把專案跑起來」，feature md 管「每個功能怎麼運作」。）

## 每張 ticket 的品質要求

- **要小**：一張 30 分鐘內能完成 🔧；太大就拆。
- **完成條件可判對錯**：用回應碼、輸出內容、檔案存在與否描述；禁用「適當」「合理」「正常運作」這種靠感覺的詞。記住：「完成實作」只是宣稱；「測試通過」可作證據，但**不能取代功能本身應達成的結果**——完成條件要寫到功能結果那一層。涉及數值計算的票，完成條件要給**預期值與算法來源**（驗「值對」不只驗「有值」）。
- **驗證實作偏好**：規格書裡標「實作偏好（未驗證）」的項目，寫「做法」欄時逐項驗證——可行就採用、有問題就修正或拒絕，並在決策紀錄註明依據；不得未經驗證直接照抄。
- **驗證指令**：HTTP 用 `curl`；丟棄輸出用 `-o /dev/null`；長駐服務「背景啟動→輪詢健康檢查→驗證→關閉（kill 後確認 port 已釋放）」；全部指令不能等待人工輸入。Docker 打包的專案：功能票的驗證方式照本機配方（快、除錯直接），只有容器化票與 README 票必須走 Docker 配方（`docker compose up -d --build` → 輪詢 → 驗證 → `docker compose down` → 確認 port 已釋放，不用 PID 檔）。
- **UI 票（會動到畫面的票）三條硬規定**：(1)「做法」只准用設計系統基座的共用元件與 token（寫明「不得出現裸 `<button>`／原生 `<select>`／硬編碼顏色」）；(2) DoD 必含**視覺驗收**：該頁在「設計系統」章狀態矩陣的每一格都做到（逐格列出）、與 `ui-prototype.html` 對應區段對照無明顯差異、CJK 名稱不折行、截圖 `<R>/evidence/TXX-ui.png`（1280×800，`<R>` 照基座票的規則寫實際路徑）存在；(3) 驗證方式含截圖指令（同基座票的寫法）。
- **同一檔案在一張票裡只能有一個動作**（「新增」或「改寫」或「保留原內容只加一段」擇一），不准同時寫「整份改寫」又「原內容暫留」這種互相矛盾的做法。

## 自我稽核（7 項：工作單產出後、給使用者看之前，逐條做完並展示結果）

1. **覆蓋對照（雙向）**：(a) 「功能清單」章的每個功能，至少有一張 ticket 的「所屬功能」指向它；反過來每張 ticket 的「所屬功能」都對得到「功能清單」的項目（或「基礎建設」）；頁面／API／資料實體同樣都有 ticket 對應；有畫面的專案另查「設計系統」章狀態矩陣的每一格都被某張 UI 票的 DoD 涵蓋、基座票存在且所有 UI 票依賴它；(b) 「全域驗收清單」跟「功能清單」「介面契約」「頁面清單」（後兩章有寫的話）完全一致，每個項目至少被一條旅程走到。零缺口才過。
2. **建造者模擬**：一項一項問自己：「如果我是建造者，只拿這兩份文件，做這項時有沒有任何要用猜的決定？」有 → 能補預設就補進決策紀錄，不能就記進待問清單。
3. **實測員模擬**：一條一條旅程問自己：「如果我是實測員，只拿「全域驗收清單」章＋README，能不能實際執行每一步、直接判 PASS/FAIL？」判不了 → 補具體輸入值和預期結果。
4. **模糊詞掃描**：找出完成條件裡的「適當／合理／正常／良好／之類／等等」，全部改寫成可判對錯的說法。
5. **依賴檢查**：依賴的編號都存在、能排出先後順序、沒有「A 等 B、B 又等 A」的死結（主序列 T01..Tnn 連續；`T-RevNN` 是需求變更的合法追加編號）。反向也查：每條依賴都真的必要（後票需要前票的產物或決策），假依賴刪掉——依賴越少，建造階段能並行的票越多。
6. **指令檢查**：每條驗證指令符合品質要求、不用人工介入；README ticket 存在、啟動指令可背景執行且與規格書「執行方式」一致（Docker 打包的專案：容器化票存在、排在所有功能票之後、README 票依賴它）；每個功能的最後一張 ticket，DoD 都含對應的 `docs/features/` 功能文件。
7. **待問清單處理**：清單不是空的 → 回去**最多再追問 2 輪** 🔧（出題照 `~/.claude/skills/agent1-interview/SKILL.md`「每一題的標準構成」）；還是沒答案的，明確記成「（預設，可改）」收進決策紀錄——不准留白。
