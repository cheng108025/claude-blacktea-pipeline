> 狀態：定稿（2026-10-25）
> 規格版本: plan-20261025-141000-a7c3
> 最後更新：2026-10-25

# AI 祕書 工作單

## 缺口總覽

- 自我稽核 7 項：全部通過（明細見文末「自我稽核結果」）。
- 外部覆核：Codex 25 項，成立 21 項已修正、4 項判定不改；重度缺口已全部處理（明細見規格書「缺口總覽」）。
- 使用者手動驗收（流水線不跑）：M1～M3（真實登入、真實解析寫入、真實雙向連動）。
- 已知風險：網頁驅動 CLI 登入依賴 CLI 互動輸出格式（T17 先留真實輸出證據，替身照它模仿；失敗有終端機後備指令）。

## 使用說明

- 共 38 張票，照施工順序編號；`依賴` 只列真的需要前票產物的票，沒有依賴關係的票可並行。
- 本輪資料夾 `<R>` ＝ `.pipeline/rounds/01`；票面證據路徑一律寫實際路徑。
- 後端指令一律在 `backend/` 用 `.venv/bin/python`；前端指令在 `frontend/`。
- **測試永遠不呼叫真實 AI CLI 或真實 Google**（T02 的 autouse 護欄強制）；耗額度的真實路徑只在使用者手動驗收 M1～M3 執行。
- 長駐服務的驗證一律「背景啟動 → 輪詢健康檢查 → 驗證 → 只關閉自己啟動的行程 → `ss -ltn` 確認 port 已釋放」。T11 之後一律用 `scripts/dev_fake_up.sh`／`scripts/dev_fake_down.sh`。
- UI 票的共同規定（以下稱「UI 票規定」）：
  1. 只准用 T06／T07 的共用元件與 token；不得出現裸 `<button>`、原生 `<select>`、硬編碼顏色（`rg -n '#[0-9a-fA-F]{6}|<button|<select' frontend/src --glob '!components/ui/**' --glob '!styles.css' --glob '!__tests__/**'` 零命中；測試檔中的 mock 資料可含日曆色碼）。
  2. 該票 DoD 指定的狀態矩陣格（規格書「設計系統 › 每頁狀態矩陣」）都有對應的 Vitest 測試（以 mock 的 `lib/api.ts` 造出該狀態，斷言畫面文案）；同一頁的格由幾張票分攤，合起來覆蓋全部格。
  3. 與 `.pipeline/plan/ui-prototype.html` 對應區段對照無明顯差異（版面、配色、元件樣式）；CJK 名稱不折行。
  4. 1280×800 下以最長內容（200 字標題、長網址、長日曆名）量測 `document.documentElement.scrollWidth ≤ clientWidth`，並看截圖確認文字沒有在詞中被切斷。
  5. 截圖 `.pipeline/rounds/01/evidence/TXX-ui.png`（亮色）與 `TXX-ui-dark.png`（暗色）存在。
- 截圖指令（以下稱「截圖配方」）：`scripts/dev_fake_up.sh --build-frontend --connect-google --login-ai` → `npx -y playwright screenshot --viewport-size=1280,800 http://localhost:8775<路徑> .pipeline/rounds/01/evidence/TXX-ui.png` → 暗色以 `--color-scheme=dark` 再截一次為 `TXX-ui-dark.png` → `scripts/dev_fake_down.sh`。

## 功能群與功能文件對照

| 功能群 | 規格書功能 | 功能文件（由該群最後一張票撰寫） |
|---|---|---|
| 安全 | F17 | `docs/features/security.md`（T03） |
| 外觀 | F15 | `docs/features/appearance.md`（T07） |
| 新增行程 | F1～F12、F23 | `docs/features/add-events.md`（T30） |
| 日曆 | F18～F22、F24 | `docs/features/calendar.md`（T33） |
| 歷史紀錄 | F13 | `docs/features/history.md`（T34） |
| 登入與設定 | F14 | `docs/features/settings-login.md`（T35） |
| 打包 | F16 | （README，T37） |

---

## 一、基礎建設

### 這一群怎麼做

先確認機器環境（T01），再分別搭好後端骨架與測試護欄（T02）、安全中介層（T03）、資料庫（T04）、前端骨架（T05）與設計系統（T06、T07）。接著做三種「替身」——假的 AI CLI（T08）、假的 Google（T09、T10）——以及一支腳本把它們和後端一起在本機背景跑起來（T11），之後所有功能票都靠它們驗證，不碰真實額度與真實日曆。

- [ ] **T01 環境檢查**
  - 所屬功能: 基礎建設
  - 內容: 確認專案路徑、Python、Node、Docker、Playwright 與 `.gitignore` 都符合開工條件
  - 做法: 只執行檢查指令並把輸出存到 `.pipeline/rounds/01/evidence/T01-env.txt`；`.gitignore` 缺項時補上（唯一會動到的檔案：`.gitignore`，動作＝只加缺的行）。檢查項：(1) `pwd` 為 `/home/peter/ai-secretary`（Linux 原生檔案系統、不在 `/mnt/c`、無空白）；(2) `python3 --version` ≥ 3.12 且 `python3 -m venv --help` 可用；(3) `node --version` ≥ 22、`npm --version`；(4) `docker --version`、`docker compose version`、`docker info` 退出碼 0；(5) `.mcp.json` 含 `playwright`；`ls ~/.cache/ms-playwright/` 有 `chromium-*`，沒有就 `npx -y playwright install chromium`；(6) `.gitignore` 至少含：`.env`、`data/`、`.e2e-data/`、`.dev-data/`、`node_modules/`、`.venv/`、`frontend/dist/`、`__pycache__/`、`.pipeline/rounds/`、`.pipeline/mcp-output/`、`.pipeline/evidence/`、`.pipeline/state.md`、`.pipeline/state-history.md`、`.pipeline/server.pid`、`.pipeline/03-build-log.md`、`.pipeline/build-log/`、`.pipeline/ticket-checks/`、`.pipeline/04-verify-report.md`、`.pipeline/05-e2e-report.md`
  - 依賴: 無
  - 完成條件(DoD): 證據檔存在且六項各有輸出與「通過」標記；任一項不通過 → 票標 BLOCKED 並附解法（Docker：安裝 Docker Desktop 並開啟 WSL 整合；Playwright MCP：從 `~/.claude/blacktea/templates/mcp.json` 複製）；`.gitignore` 含上列全部行（`grep -Fxc` 逐行檢查皆為 1）
  - 驗證方式: `for p in .env data/ .e2e-data/ .dev-data/ node_modules/ .venv/ frontend/dist/ __pycache__/ .pipeline/rounds/ .pipeline/mcp-output/ .pipeline/evidence/ .pipeline/state.md .pipeline/state-history.md .pipeline/server.pid .pipeline/03-build-log.md .pipeline/build-log/ .pipeline/ticket-checks/ .pipeline/04-verify-report.md .pipeline/05-e2e-report.md; do grep -Fxq "$p" .gitignore || echo "MISSING $p"; done` 無輸出；`docker info >/dev/null && echo ok`；`python3 -c 'import sys; assert sys.version_info>=(3,12)'`

- [ ] **T02 後端骨架與測試護欄**
  - 所屬功能: 基礎建設
  - 內容: 建立 FastAPI 應用、設定讀取、健康檢查、靜態檔與 SPA fallback、統一錯誤格式，以及禁止測試碰真實 CLI／Google 的 autouse 護欄
  - 做法: 新增 `backend/requirements.txt`（規格書「關鍵套件」後端全部，取當時最新穩定版寫成 `==` 固定版號，pydantic 為 2.x）、`backend/requirements-dev.txt`、`backend/pytest.ini`（`asyncio_mode=auto`、`testpaths=tests`）、`backend/app/__init__.py`、`backend/app/config.py`（讀規格書「環境變數」全部項目；`fake_mode` 判定；`today()` 依 `DEFAULT_TIMEZONE`，替身模式且有 `FAKE_TODAY` 時回該值）、`backend/app/errors.py`（`AppError(code, http_status, message, **extra)` 與 exception handler，輸出 `{"error":{"code","message",...}}`）、`backend/app/main.py`（`create_app()`；自動掛載 `app/routes/` 套件內每個模組的 `router` 屬性（以 `pkgutil.iter_modules` 依模組名排序），之後新增路由的票只需新增路由檔、不改 `main.py`；`GET /api/health` 寫在 `backend/app/routes/health.py`；`STATIC_DIR` 存在時掛靜態檔，非 `/api` 的 GET 回 `index.html`；不存在則非 `/api` 回 404）、`backend/app/routes/__init__.py`、`backend/app/routes/health.py`、`backend/tests/__init__.py`、`backend/tests/conftest.py`（autouse fixture：把 `CLAUDE_BIN`／`CODEX_BIN` 設為 `tests/fakes/bin/` 下的路徑、`GOOGLE_*` 設為 `http://127.0.0.1:1/` 這類不可達位址，並 monkeypatch `subprocess.Popen`、`asyncio.create_subprocess_exec`、`pexpect.spawn` 入口：檢查完整指令列的**每個參數**（含 `sh -c` 字串內的詞），任一參數檔名為 `claude`／`codex` 且不在 `tests/fakes/bin/` 底下就 `pytest.fail("real CLI blocked")`；另在 `httplib2.Http.request`、`httpx.HTTPTransport.handle_request`／`AsyncHTTPTransport.handle_async_request` 封鎖主機 `*.googleapis.com`、`accounts.google.com`、`oauth2.googleapis.com`，命中即 `pytest.fail("real Google blocked")`）、`backend/tests/test_app_basics.py`。建立 `backend/.venv` 並安裝兩份 requirements
  - 依賴: T01
  - 完成條件(DoD): (1) `GET /api/health` 回 200 `{"status":"ok"}`；(2) 在 `app/routes/` 放一個測試用模組（測試內以 tmp 套件模擬）其 `router` 被自動掛載；`STATIC_DIR` 指向含 `index.html` 的暫存目錄時，`GET /calendar` 回該 index 內容、`GET /api/nope` 回 404 JSON 錯誤格式；(3) `FAKE_TODAY=2026-10-25` 且替身模式時 `config.today()=="2026-10-25"`，非替身模式時忽略 `FAKE_TODAY`；(4) 護欄測試（以 `pytester` 跑子測試並斷言其失敗訊息）：`claude --version`、`/usr/bin/env claude`、`sh -c "codex exec x"` 三種啟動方式皆失敗且訊息含「real CLI blocked」；以 httpx 請求 `https://www.googleapis.com/calendar/v3/users/me/calendarList` 失敗且訊息含「real Google blocked」；`tests/fakes/bin/claude` 路徑不被擋；(5) 變異驗證：暫時把護欄改成只檢查 `argv[0]`，`/usr/bin/env claude` 案例轉紅；還原後全綠
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_app_basics.py`；背景 `PUBLIC_PORT=8775 DATA_DIR=../.dev-data .venv/bin/uvicorn app.main:app --port 8775` → 輪詢 `curl -fsS -H 'Host: localhost:8775' http://127.0.0.1:8775/api/health` → 關閉並 `ss -ltn | grep -c ':8775 '` 為 0

- [ ] **T03 安全中介層（Host 白名單與跨站寫入防護）**
  - 所屬功能: F17 本機限定與防跨站
  - 內容: 實作規格書「資安與權限」的 Host 白名單與跨站寫入檢查、JSON Content-Type 檢查
  - 做法: 新增 `backend/app/security.py`（ASGI middleware：Host 完全相等比對 `localhost:{PUBLIC_PORT}`、`127.0.0.1:{PUBLIC_PORT}`；寫入方法檢查 Origin／Sec-Fetch-Site；錯誤用 `BAD_HOST`、`CROSS_SITE_BLOCKED`）；改寫 `backend/app/main.py`（只加一行掛載 middleware）；新增 `backend/tests/test_security.py`；新增 `docs/features/security.md`
  - 依賴: T02
  - 完成條件(DoD): 以 TestClient 驗證（PUBLIC_PORT=8775）：Host `localhost:8775`／`127.0.0.1:8775` → 200；`evil.example:8775`、`127.0.0.1.evil.example:8775`、`localhost:8775.evil.example`、`localhost:9999` → 400 `BAD_HOST`；`POST` 帶 `Origin: http://localhost:8775` → 通過；`Origin: http://evil.example` → 403；無 Origin＋`Sec-Fetch-Site: same-origin` → 通過；無 Origin＋`Sec-Fetch-Site: cross-site` → 403；兩者皆無 → 403；`GET` 不受跨站檢查；變異驗證：把 Host 比對改成 `startswith` → `127.0.0.1.evil.example` 案例轉紅；`docs/features/security.md` 存在（白話說明、檔案組成、資料流、對應 T03）
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_security.py`

- [ ] **T04 資料庫**
  - 所屬功能: F13 歷史紀錄（資料層）
  - 內容: 建表、連線、啟動清理
  - 做法: 新增 `backend/app/db.py`（`connect()` 開 WAL 與 foreign_keys；`init_db()` 執行規格書「建表 SQL」原文；`cleanup()`：刪 7 天前且無 history 引用的 `parse_sessions`、刪 `tmp/` 中 mtime 超過 1 小時的檔；啟動時建立 `DATA_DIR` 下 `claude/`、`codex/`、`tmp/`）；改寫 `backend/app/main.py`（只加 startup 呼叫 `init_db()`、`cleanup()`）；新增 `backend/tests/test_db.py`
  - 依賴: T02、T03（兩票都改 `backend/app/main.py`，須先後執行）
  - 完成條件(DoD): 空目錄啟動後 `app.db` 存在且 `sqlite_master` 含 `parse_sessions`、`history` 兩表與三個 `idx_history_*` 索引；`PRAGMA journal_mode` 為 `wal`；插入相同 `(parse_id, draft_id)` 第二次拋 IntegrityError；`engine='gpt'` 違反 CHECK；清理：8 天前且無引用的 session 被刪、8 天前但有引用的保留、6 天前的保留；`tmp/` 中 2 小時前的檔被刪、10 分鐘前的保留
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_db.py`

- [ ] **T05 前端骨架**
  - 所屬功能: 基礎建設
  - 內容: 建立 React＋TS＋Vite 專案、Tailwind 4、shadcn 初始化、路由四頁空殼、頂欄、Vitest
  - 做法: 新增 `frontend/` 下 `package.json`（scripts：`dev`、`build`、`test`＝`vitest`）、`package-lock.json`、`vite.config.ts`（`@tailwindcss/vite`、`/api` 代理到 `http://localhost:8775`，`changeOrigin: true` 並在 `configure` 的 `proxyReq` 事件把 `Origin` 改寫為 `http://localhost:8775`；Vitest `environment: jsdom`）、`tsconfig.json`、`index.html`（`lang="zh-Hant"`、`<title>AI 祕書</title>`）、`components.json`（shadcn）、`src/main.tsx`、`src/App.tsx`（react-router：`/`、`/calendar`、`/history`、`/settings` 各一個暫時頁元件，頂欄四個分頁連結）、`src/pages/NewEventPage.tsx`、`src/pages/CalendarPage.tsx`、`src/pages/HistoryPage.tsx`、`src/pages/SettingsPage.tsx`（各只有頁標題）、`src/styles.css`（只有 Tailwind import）、`src/__tests__/App.test.tsx`；`package.json` 的 devDependencies 另含 `playwright`（供 `frontend/scripts/screenshots/*.mjs` 截圖腳本使用）
  - 依賴: T01
  - 完成條件(DoD): `npm ci` 成功；`npm run build` 產出 `frontend/dist/index.html`；`npm test -- --run` 通過，且 App 測試斷言在 `/calendar` 路由渲染出頁標題「日曆」、頂欄有「新增行程」「日曆」「歷史紀錄」「設定」四個連結；`dist/` 內無任何 `http://`／`https://` 外部資源引用（`rg -n 'https?://' frontend/dist --glob '*.html' --glob '*.css'` 零命中）；`vite.config.ts` 的代理設定含 Host 與 Origin 改寫（以單元測試讀取設定物件、呼叫 `configure` 傳入假的 proxy 物件，斷言 `proxyReq` 後 `origin` 標頭為 `http://localhost:8775`）
  - 驗證方式: `cd frontend && npm ci && npm run build && npm test -- --run`

- [ ] **T06 設計 token、主題切換與基礎元件**
  - 所屬功能: F15 亮／暗主題
  - 內容: 把規格書設計 token 寫成 CSS 變數（亮／暗）、主題切換、以 shadcn 產生基礎元件並套用 token
  - 做法: 改寫 `frontend/src/styles.css`（整份改寫：規格書「設計 token」表全部變數，`:root` 亮色、`[data-theme="dark"]` 暗色，`prefers-color-scheme` 於 `system` 模式套用；字型堆疊、tabular-nums 工具類；Tailwind 4 `@theme` 對應 token）；新增 `frontend/src/lib/theme.ts`（`light`／`dark`／`system`，localStorage key `ai-secretary-theme`，讀寫 try/catch）；新增 `frontend/src/components/ThemeToggle.tsx`（☀／🌙＋「白天」／「夜晚」）；以 shadcn CLI 產生 `frontend/src/components/ui/` 下：button（加 `danger` 變體用 `--danger-solid`、`loading` 屬性）、input、textarea、select、checkbox、switch、card、badge（`success`／`warning`／`danger`／`neutral`／`ai` 變體）、tabs、dialog、popover、skeleton、sonner；新增 `frontend/src/components/ui/spinner.tsx`；改寫 `frontend/src/App.tsx`（只加 ThemeToggle 到頂欄、`<Toaster/>`）；新增 `frontend/src/__tests__/theme.test.tsx`
  - 依賴: T05
  - 完成條件(DoD): token 只定義在 `styles.css` 一處（`rg -n -- '--primary:' frontend/src` 只有 2 行：亮、暗各一）；token 值與規格書表格逐一相同（測試讀 `styles.css` 比對硬編碼的期望值清單，期望清單從規格書表格手抄）；主題測試：點切換鈕 → `<html data-theme="dark">` 且 localStorage 為 `dark`；重新 render 讀回 `dark`；localStorage 拋例外時不崩潰且預設 `system`；各基礎元件 render 不爆
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/theme.test.tsx && npm run build`

- [ ] **T07 共用元件與 /dev/ui 展示頁**
  - 所屬功能: F15 亮／暗主題（設計系統基座）
  - 內容: 專案層級共用元件與開發用展示頁
  - 做法: 新增 `frontend/src/components/EmptyState.tsx`、`ConfirmDialog.tsx`（danger 確認鈕）、`ErrorBox.tsx`（`--danger` 文字＋`--danger-bg` 底）、`StatusBadge.tsx`（規格書徽章文案的對應表）、`Truncate.tsx`（單行省略＋`title`）；新增 `frontend/src/pages/DevUiPage.tsx`（路由 `/dev/ui`，標「開發用」；展示 T06 基礎元件與本票共用元件的各變體與 disabled／錯誤／loading 態，各一排，並含規格書「視覺樣本」的全部元素（行程卡片、日曆行程塊以靜態 HTML＋token 示意）；EventCard、RecurrenceEditor、ServiceCard、日曆檢視等組合元件由各自的 UI 票以截圖驗收，不放進本頁）；改寫 `frontend/src/App.tsx`（只加 `/dev/ui` 路由，不放進頂欄）；新增 `frontend/src/__tests__/shared.test.tsx`；新增 `docs/features/appearance.md`
  - 依賴: T06
  - 完成條件(DoD): `/dev/ui` 亮色截圖 `.pipeline/rounds/01/evidence/T07-ui.png` 與暗色 `T07-ui-dark.png` 存在，畫面上可見 Button（primary／secondary／ghost／danger／disabled／loading）、Input／Textarea／Select（一般／焦點／錯誤／disabled）、Checkbox、Switch、Card、Badge 五種變體、Tabs、Dialog（開啟狀態）、Popover、Toast、EmptyState、Spinner、Skeleton、ErrorBox、ConfirmDialog；與規格書「視覺樣本」對照配色一致；`Truncate` 在 200 字標題時 `scrollWidth ≤ clientWidth` 且 `title` 為全文；ConfirmDialog 按取消不呼叫 onConfirm、按確認呼叫一次；共用元件 render 不爆；`docs/features/appearance.md` 存在
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/shared.test.tsx && npm run build`；背景 `npx vite preview --port 4173 --strictPort`（在 `frontend/`）→ 輪詢 `curl -fsS http://localhost:4173/dev/ui` → `npx -y playwright screenshot --viewport-size=1280,800 http://localhost:4173/dev/ui .pipeline/rounds/01/evidence/T07-ui.png` → `--color-scheme=dark` 再截 `T07-ui-dark.png` → 關閉自己啟動的 preview 行程並確認 4173 釋放

- [ ] **T08 替身 AI CLI（解析）**
  - 所屬功能: F5 AI 解析（測試替身）
  - 內容: 模仿真實 claude／codex 解析呼叫的參數與輸出格式的替身執行檔，依關鍵字回固定結果
  - 做法: 新增 `backend/tests/fakes/bin/claude`、`backend/tests/fakes/bin/codex`（`#!/usr/bin/env python3`、可執行；共用 `backend/tests/fakes/fake_ai_common.py`）、`backend/tests/fakes/ai_fixtures.json`（規格書「替身 AI 回應表」全部列，由上而下比對）、`backend/tests/test_fake_ai.py`。claude 替身：解析 `-p` 模式，從 stdin 讀 stream-json，輸出 `{"type":"system",...}` 與 `{"type":"result","subtype":"success","structured_output":{...},"result":"<json字串>"}`；codex 替身：解析 `exec` 參數，把結果寫到 `-o` 檔；兩者每次呼叫寫一行到 `$FAKE_AI_LOG`；「格式壞掉」輸出非 JSON；「逾時測試」sleep 30；含圖片（claude 的 image 區塊、codex 的 `-i`）回「海報音樂會」。`auth`／`login` 子指令留給 T17
  - 依賴: T02
  - 完成條件(DoD): 以 subprocess 直接呼叫替身：claude 輸入含「小王吃到九點」→ result 行 `structured_output.events[0]` 為「跟小王吃飯」2026-11-04 19:00–21:00；輸入含「小王」（無「吃到九點」）→ `end_time` 為 null；codex 輸入「講座系列」→ `-o` 檔 3 筆；帶圖片 → 「海報音樂會」；「天氣很好」→ `events` 為空、`no_event_reason`「內容沒有提到任何時間安排」；每次呼叫後 `$FAKE_AI_LOG` 多 1 行；stdin 未關閉時 codex 替身不阻塞（測試以 `stdin=DEVNULL` 呼叫並設 5 秒逾時）
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_fake_ai.py`

- [ ] **T09 替身 Google（核心）**
  - 所屬功能: F12 寫入日曆（測試替身）
  - 內容: 替身 Google 的 OAuth、日曆清單、行程基本 CRUD 與測試控制端點
  - 做法: 新增 `backend/tests/fakes/fake_google.py`（FastAPI app，記憶體儲存）、`backend/tests/fakes/google_seed.json`（規格書「google_seed.json 初始資料」兩張表全部內容）、`backend/tests/test_fake_google_core.py`。實作：`GET /o/oauth2/auth`（302 到 `redirect_uri?code=fake-code&state=…`）、`POST /token`（authorization_code 與 refresh_token 兩種 grant，回 access／refresh token、`id_token` 含 email `tester@example.com`）、`POST /revoke`、`GET /calendar/v3/users/me/calendarList`、`GET/POST /calendar/v3/calendars/{cal}/events`（list 先支援 `timeMin`／`timeMax`／`maxResults`／`pageToken`，insert 產生 id 與 etag）、`GET/DELETE /calendar/v3/calendars/{cal}/events/{id}`（刪除不存在回 410）；Bearer token 驗證（無效回 401）；控制端點 `GET /_state`、`POST /_reset`、`POST /_revoke_all`
  - 依賴: T02
  - 完成條件(DoD): 測試以 TestClient 驗證：授權端點 302 的 Location 帶原 state；token 換到後 calendarList 回 3 本且 `holidays` accessRole 為 `reader`；insert 後 `/_state` 可見；delete 後再 delete 回 410；`/_revoke_all` 後 API 回 401；`/_reset` 後回到 seed（`seed-dinner` 等 6 筆存在、新增的消失）；可用 `uvicorn fake_google:app --app-dir backend/tests/fakes --port 9000` 獨立啟動
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_fake_google_core.py`

- [ ] **T10 替身 Google（進階）**
  - 所屬功能: F18 日曆頁檢視（測試替身）
  - 內容: 重複行程展開、patch 與 etag、私有標記查詢、模擬手機操作
  - 做法: 改寫 `backend/tests/fakes/fake_google.py`（只加功能，不改 T09 既有端點的行為）：events.list 支援 `singleEvents=true`（以 python-dateutil 展開 RRULE，實例 id `<主id>_<YYYYMMDDTHHMMSSZ>`，帶 `recurringEventId` 與 `originalStartTime`）、`orderBy=startTime`、`privateExtendedProperty=k=v`（可重複多次，全部條件需同時成立）、`showDeleted`（被刪的回 `status:"cancelled"`）；`PATCH .../events/{id}`（`If-Match` 不符回 412；每次修改產生新 etag）；`POST /_phone_edit`、`POST /_phone_add`、`POST /_phone_delete`；新增 `backend/tests/test_fake_google_advanced.py`
  - 依賴: T09
  - 完成條件(DoD): `timeMin=2026-11-01T00:00:00+08:00&timeMax=2026-12-01T00:00:00+08:00&singleEvents=true` 讀 primary：「週會」實例恰為 2026-11-02、11-09、11-16、11-23、11-30 五筆（硬編碼期望日期）、「讀書會」11 月實例為 2026-11-10（第二個週二）；patch 帶舊 etag 回 412、帶新 etag 回 200 且 etag 改變；`privateExtendedProperty=ai_secretary=1` 只回帶標記者；同時帶 `privateExtendedProperty=parse_id=p1&privateExtendedProperty=draft_id=e1` 只回兩者皆符合者（另一筆 `parse_id=p1,draft_id=e2` 不回）；`/_phone_delete` 後 `showDeleted=true` 回該筆 `status:"cancelled"`
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_fake_google_advanced.py`

- [ ] **T11 本機替身開發環境腳本**
  - 所屬功能: 基礎建設
  - 內容: 一鍵在本機背景啟動「替身 Google＋後端（替身 AI）」，供之後各票驗證與截圖
  - 做法: 新增 `scripts/dev_fake_up.sh`、`scripts/dev_fake_down.sh`（皆 `set -euo pipefail`、非互動）。up：檢查 8775、9000 未被佔用（被佔用就報錯退出，不殺任何行程）；`DATA_DIR=.dev-data`；背景起替身 Google（9000）與後端（8775，環境：`PUBLIC_PORT=8775`、`STATIC_DIR=frontend/dist`、`CLAUDE_BIN`／`CODEX_BIN` 指向替身、`GOOGLE_*` 指向 `127.0.0.1:9000`、`GOOGLE_CLIENT_ID=fake-dummy`、`GOOGLE_CLIENT_SECRET=fake-secret`、`FAKE_TODAY=2026-10-25`、`FAKE_AI_LOG=.dev-data/fake_ai_calls.log`）；PID、啟動時間、命令、port 寫入 `.dev-data/dev_fake.pids`；輪詢兩者健康（總逾時 30 秒）；選項 `--build-frontend`（先 `npm --prefix frontend run build`）、`--reset`（清 `.dev-data` 中 db 與 token 並 `POST /_reset`）。`--connect-google` 與 `--login-ai` 兩個選項在 T18、T17 完成後才有作用：此票先讓它們印出「尚未支援」並繼續。down：只對 `dev_fake.pids` 中、命令列仍吻合的 PID 送 TERM，等待結束，確認 8775、9000 釋放；PID 不符就回報不殺
  - 依賴: T02、T08、T09
  - 完成條件(DoD): `scripts/dev_fake_up.sh` 退出碼 0 後 `curl -fsS -H 'Host: localhost:8775' http://127.0.0.1:8775/api/health` 回 ok、`curl -fsS http://127.0.0.1:9000/_state` 回 JSON；`scripts/dev_fake_down.sh` 後兩個 port 皆釋放（`ss -ltn | grep -cE ':(8775|9000) '` 為 0）；8775 預先被一個 `python3 -m http.server 8775` 佔住時 up 以非 0 退出且該行程仍存活（測完自行關閉它）；連續 up→down 兩次皆成功
  - 驗證方式: 依 DoD 逐項執行上述指令

---

## 二、後端：行程邏輯

### 這一群怎麼做

把「一筆行程」做成單一資料模型 EventDraft，所有完整性判斷都只寫在後端一處（T12）；重複規則的產生、解析與白話集中在一個模組（T13）；說明欄組裝與重複／撞期偵測是不碰網路的純函式（T14），讓 API 票只負責接線。

- [ ] **T12 EventDraft 模型與完整性驗證**
  - 所屬功能: F6 預覽清單
  - 內容: 規格書「資料型別：EventDraft」與「完整性規則」1～9
  - 做法: 新增 `backend/app/models.py`（Pydantic：EventDraft、Recurrence、Warning 及 API 請求／回應模型的 EventDraft 相關部分）、`backend/app/events/__init__.py`、`backend/app/events/validate.py`（`normalize(draft) -> EventDraft` 依規格書「正規化」；`compute_missing(draft, mode="new"|"edit") -> (missing_fields, field_errors)`，呼叫端一律先 `normalize`；`mode="edit"` 依規格書「編輯模式」放寬）、`backend/tests/test_validate.py`
  - 依賴: T02
  - 完成條件(DoD): 規則 1～8 各有「通過」與「不通過」兩個案例（例：規則 4 `start_time=19:00, end_time=null` → missing 含 `end_time`；`19:00–19:00` → `end_time` 錯誤「結束時間需晚於開始時間」；規則 3 `all_day=null, start_time=null` → missing 含 `all_day`；`all_day=null, start_time=19:00` → 不含 `all_day`；規則 6 `timezone="Mars/Base"` → 錯誤；規則 7 `count=501` → 錯誤、`until` 與 `count` 同時有值 → 錯誤）；`normalize`：`all_day=null, start_time="19:00"` → `all_day=false`、`end_date=null` → 等於 `start_date`、標題頭尾空白被去除；`mode="edit"`：空標題不列缺漏、300 字標題與 9,000 字說明不報錯；`mode="new"` 同樣輸入則報錯；期望值全部硬編碼
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_validate.py`

- [ ] **T13 重複規則：產生、解析、白話**
  - 所屬功能: F7 重複行程、F24 重複行程的編輯與刪除
  - 內容: Recurrence ↔ RRULE 雙向轉換、支援子集判定、白話與次數
  - 做法: 新增 `backend/app/events/recurrence.py`（`to_rrule(rec, start_date, start_time, tz) -> str`，`UNTIL` 依規格書算法轉 UTC；`parse_rrule(lines) -> (Recurrence|None, locked: bool, raw: str|None)`；`describe(rec, start_date) -> str`，有 `until` 時以 python-dateutil 計算次數）、`backend/tests/test_recurrence.py`
  - 依賴: T12
  - 完成條件(DoD): 硬編碼期望：WEEKLY/WE/until 2026-12-31、開始 2026-10-28 → 白話「每週三，到 2026/12/31（共 10 次）」、RRULE `RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=WE;UNTIL=20261231T155959Z`；count 5 → 「每週三，共 5 次」與 `…;COUNT=5`；兩者皆空 → 「每週三，不結束」；interval 2、BYDAY MO,TH、count 6 → 「每 2 週的週一、週四，共 6 次」；MONTHLY 15 號不結束 → 「每月 15 日，不結束」；parse `RRULE:FREQ=WEEKLY;BYDAY=MO` → 解析成功、locked=false；parse `RRULE:FREQ=MONTHLY;BYDAY=2TU`、`FREQ=YEARLY`、含 `EXDATE` 的兩行清單 → locked=true 且 raw 為原字串；to→parse 來回一致
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_recurrence.py`

- [ ] **T14 說明欄組裝與重複／撞期偵測**
  - 所屬功能: F10 重複偵測＋撞期、F11 行程說明
  - 內容: 規格書「說明欄組裝」與「重複偵測規則」的純函式
  - 做法: 新增 `backend/app/events/description.py`（`build(summary, source_type, source_url)`）、`backend/app/events/dedupe.py`（`check(draft, history_rows, google_day_events, exclude_event_id) -> list[Warning]`、`title_similar(a,b)`，不碰 DB 與網路）、`backend/tests/test_description_dedupe.py`
  - 依賴: T12
  - 完成條件(DoD): 說明欄五種來源的輸出逐字等於規格書表格（硬編碼字串）；相似度「跟小王吃飯」vs「跟小王吃火鍋」→ 相似、vs「部門聚餐」→ 不相似；`duplicate_history` 兩種條件各一案例；`duplicate_google` 一案例；`conflict` 邊界：19:00–20:00 vs 20:00–21:00 → 無警告、vs 19:59–21:00 → `conflict` 訊息「撞期：<標題> 19:59–21:00」；已判 `duplicate_google` 的那筆不再重複出 `conflict`；`exclude_event_id` 等於 Google 行程 `id` 或其 `recurringEventId`（系列實例）都被略過，`history` 中 `google_event_id` 等於它的列也不產生 `duplicate_history`；全天行程不產生 `conflict`；變異驗證：把重疊判定的 `<` 改成 `<=` → 邊界案例轉紅
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_description_dedupe.py`

---

## 三、後端：AI 與抓網頁

### 這一群怎麼做

AI 呼叫層把兩個 CLI 包成同一個介面，負責逾時、重試、錯誤對應與 schema 驗證（T15）；抓網頁模組依序嘗試 httpx、trafilatura、無頭瀏覽器並判定登入頁（T16）。兩者都只用替身與本機測試頁驗證。

- [ ] **T15 AI 呼叫層**
  - 所屬功能: F4 AI 引擎選擇、F5 AI 解析
  - 內容: 依規格書「AI相關」實作 claude／codex 呼叫、逾時、重試、錯誤對應
  - 做法: 新增 `backend/app/ai/__init__.py`、`backend/app/ai/schema.json`（規格書輸出 schema，全部 required、可 null、`additionalProperties:false`）、`backend/app/ai/prompt.py`（系統提示 8 點；「今天」用 `config.today()` 加星期）、`backend/app/ai/claude_cli.py`、`backend/app/ai/codex_cli.py`（指令參數逐字照規格書；codex 每次 `tempfile.mkdtemp()` 當 `-C` 並於 finally 刪除）、`backend/app/ai/runner.py`（`parse(engine, text, image_path) -> dict`；`start_new_session=True` 啟動，逾時 `os.killpg`；非 JSON／不符 schema 重試 1 次；退出碼非 0 → `AI_FAILED`，stderr 遮罩長度 ≥24 的連續英數／`-_` 字串後取末段 ≤300 字，stderr 空時「退出碼 N，無錯誤輸出」）、`backend/tests/test_ai_runner.py`（用 T08 替身；另以臨時腳本模擬「退出碼 3＋stderr 含 40 字元 token」與「退出碼 2＋stderr 空」）
  - 依賴: T08
  - 完成條件(DoD): claude、codex 各以「小王吃到九點」取得 1 筆正確事件；帶圖片時 claude 送出 stream-json 含 image 區塊（替身回「海報音樂會」證明）、codex 帶 `-i`；「格式壞掉」→ `AI_BAD_OUTPUT` 且 `FAKE_AI_LOG` 該次 2 行；`AI_TIMEOUT_SECONDS=2`＋「逾時測試」→ 約 2 秒拋 `AI_TIMEOUT`，之後 `ps` 找不到替身行程；退出碼 3 案例 → `AI_FAILED` 訊息不含原 40 字元 token 且含遮罩標記；退出碼 2 空 stderr → 訊息「AI 執行失敗：退出碼 2，無錯誤輸出」；系統提示含「今天是 2026-10-25（星期日）」（`FAKE_TODAY` 替身模式）；codex 指令列含 `-m gpt-5.6-sol` 與 `--sandbox read-only`；claude 指令列含 `--tools ""`
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_ai_runner.py`

- [ ] **T16 抓網頁與測試網站頁**
  - 所屬功能: F2 輸入：連結
  - 內容: 規格書「抓網頁規則」1～6 與驗收用測試網站的四個頁面
  - 做法: 新增 `backend/app/fetch/__init__.py`、`backend/app/fetch/fetcher.py`（`async fetch_text(url) -> str`，失敗拋 `FETCH_NEEDS_PASTE` 並區分兩種訊息；依規格書規則 1 對初始網址與每一次轉址先解析 DNS 並封鎖 loopback／link-local／metadata／未指定位址，httpx 以 `follow_redirects=False` 自行逐跳處理；Playwright 以 `page.route` 攔截並套用同一檢查）、`backend/tests/fakes/site/event.html`、`js.html`、`login.html`、`empty.html`（內容照規格書「fixture-site」描述）、`backend/tests/test_fetcher.py`（測試中以 `http.server` 在隨機空閒 port 供應 `site/`）。本機執行 `backend/.venv/bin/python -m playwright install chromium`
  - 依賴: T02
  - 完成條件(DoD): `event.html` → 文字含「金曲獎得主講座」且未啟動 Playwright（以 spy 斷言）；`js.html` → 文字含「爵士之夜」且有啟動 Playwright；`login.html` → `FETCH_NEEDS_PASTE` 訊息「這個頁面需要登入才看得到內容，請複製頁面上的文字貼上」；`empty.html` → 「抓不到這個連結的內容，請複製頁面上的文字貼上」；不存在的 port → 同上抓不到訊息；回應 6MB 的頁 → 抓不到訊息；`ftp://` 不被當成連結處理（由呼叫端判定，本函式收到時拋 BAD_REQUEST）；整體逾時：一個延遲 25 秒回應的測試端點在 ≤21 秒內回抓不到訊息；SSRF：`http://127.0.0.1:<port>/event.html`、`http://localhost:<port>/`、`http://169.254.169.254/` 皆回抓不到訊息且**未對該位址發出連線**（以 spy 斷言）；一個公開測試頁 302 轉到 `http://127.0.0.1/` → 抓不到訊息；`http://10.0.0.1/`（mock DNS 解析）不被 SSRF 規則擋。註：本票其餘測試需在 loopback 上的 http.server 供應頁面，測試以 monkeypatch 把該測試 port 加入僅限測試的允許清單（正式程式碼的允許清單恆為空）
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_fetcher.py`

---

## 四、後端：登入與 Google

### 這一群怎麼做

先把兩個 CLI 的「登入狀態查詢」與替身的登入子指令做好，並留下真實 CLI 登入畫面的證據（T17）；接著做 Google 授權與總狀態 API（T18）、網頁驅動 CLI 登入（T19）。Google 日曆的讀寫分三步：欄位對應與可編輯判定的純函式（T20）、日曆清單與期間行程讀取（T21）、單筆讀取／修改／刪除（T22）。

- [ ] **T17 CLI 登入狀態與替身登入子指令**
  - 所屬功能: F14 設定頁：登入
  - 內容: 記錄真實 CLI 登入流程的輸出格式、替身 CLI 的登入相關子指令、登入狀態查詢函式
  - 做法: (1) 在一次性容器中**只啟動、不完成**真實登入流程並保存輸出：`docker run --rm node:22-bookworm-slim bash -c 'npm i -g @anthropic-ai/claude-code@2.1.233 @openai/codex@0.147.0 >/dev/null 2>&1; export CLAUDE_CONFIG_DIR=/tmp/c CODEX_HOME=/tmp/x; (timeout 20 script -qc "claude auth login" /dev/null; true); (timeout 20 script -qc "codex login --device-auth" /dev/null; true); claude auth status; echo rc=$?; codex login status; echo rc=$?'`，輸出存 `.pipeline/rounds/01/evidence/T17-real-login-output.txt`（只含網址格式與提示文字，不完成授權、不耗額度）；(2) 改寫 `backend/tests/fakes/bin/claude`、`backend/tests/fakes/bin/codex`、`backend/tests/fakes/fake_ai_common.py`（只加子指令，不改 T08 的解析行為）：claude `auth login`（印出與證據同格式的網址與貼碼提示，讀 stdin 授權碼，`FAKE-CODE-123` → 在 `$CLAUDE_CONFIG_DIR/fake_logged_in` 建檔並退出 0，其他 → 印錯誤退出 1）、`auth status`、`auth logout`；codex `login --device-auth`（印網址與代碼 `ABCD-1234`，3 秒後建 `$CODEX_HOME/fake_logged_in` 退出 0）、`login status`（已登入時退出 0 並印 `Logged in using ChatGPT`）、`logout`；解析行為維持 T08 原樣（不檢查登入，登入把關由 A3 以 `is_logged_in` 負責）；(3) 新增 `backend/app/cli_auth/__init__.py`、`backend/app/cli_auth/status.py`（`is_logged_in(engine)`，30 秒快取、`invalidate(engine)`）；新增 `backend/tests/test_cli_status.py`
  - 依賴: T08
  - 完成條件(DoD): 證據檔存在且含兩個 CLI 的登入網址行與提示文字（若某 CLI 在無 TTY 下無輸出，證據檔記錄實際狀況，並在 build-log 寫明替身採用的格式依據）；替身 `auth status`／`login status` 的未登入與已登入兩種輸出、退出碼與證據檔中真實格式一致；`is_logged_in` 未登入 → False、寫入 fake 標記後在快取期內仍 False、`invalidate` 後 True；T08 的 `tests/test_fake_ai.py` 在本票修改後仍全綠
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_cli_status.py && test -s ../.pipeline/rounds/01/evidence/T17-real-login-output.txt`

- [ ] **T18 Google 授權與狀態 API（A2、A13～A15）**
  - 所屬功能: F14 設定頁：登入
  - 內容: Google OAuth 網頁流程、token 儲存與刷新、`/api/status`
  - 做法: 新增 `backend/app/google/__init__.py`、`backend/app/google/oauth.py`（state 記憶體 10 分鐘一次性；scope 照規格書；`GOOGLE_AUTH_URI`／`TOKEN_URI`／`REVOKE_URI` 可覆寫；token 存 `DATA_DIR/google_token.json` 權限 0600；`get_credentials()` 自動刷新，刷新失敗拋 `GOOGLE_AUTH_EXPIRED`）、`backend/app/routes/google.py`（A13～A15）、`backend/app/routes/status.py`（A2，含 `today`、`fake_mode`、三服務狀態）；改寫 `scripts/dev_fake_up.sh`（只把 `--connect-google` 實作為：`curl` 依序走 `/api/google/login` → 替身授權 → callback，完成後 `/api/status` 的 google.connected 為 true）；新增 `backend/tests/test_google_oauth.py`（啟動 T09 替身於隨機 port）
  - 依賴: T03、T09、T11、T17
  - 完成條件(DoD): 未設 `GOOGLE_CLIENT_ID` → A13 回 409 `GOOGLE_NOT_CONFIGURED`、A2 `google.configured=false`；完整流程後 `google_token.json` 存在、權限 `-rw-------`、A2 `connected=true`、`email="tester@example.com"`；錯誤 state → 302 `/settings?google=error`；同一 state 第二次使用 → error；A15 後 token 檔消失、`connected=false`；`/_revoke_all` 後 `get_credentials()` 使用時拋 `GOOGLE_AUTH_EXPIRED`；A2 的 `today` 在替身模式為 `2026-10-25`；`scripts/dev_fake_up.sh --connect-google` 後 `curl -s -H 'Host: localhost:8775' http://127.0.0.1:8775/api/status` 的 `google.connected` 為 true
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_google_oauth.py`；`scripts/dev_fake_up.sh --reset --connect-google && curl -s -H 'Host: localhost:8775' http://127.0.0.1:8775/api/status; scripts/dev_fake_down.sh`

- [ ] **T19 網頁驅動 CLI 登入（A16～A20）**
  - 所屬功能: F14 設定頁：登入
  - 內容: 以 pexpect 驅動 CLI 登入、擷取網址／代碼、接收授權碼、逾時與後備指令
  - 做法: 新增 `backend/app/cli_auth/sessions.py`（每引擎最多一個 session；狀態機 `waiting_user`→`verifying`→`success`／`failed`；10 分鐘逾時；成功判定以 T17 `is_logged_in` 並 `invalidate`；失敗訊息附後備指令）、`backend/app/routes/auth.py`（A16～A20）；改寫 `scripts/dev_fake_up.sh`（只把 `--login-ai` 實作為：在 `.dev-data/claude/`、`.dev-data/codex/` 建立替身已登入標記）；新增 `backend/tests/test_cli_login.py`（用替身；逾時以 monkeypatch 縮成 2 秒）
  - 依賴: T17、T03、T18（T18 與本票都改 `scripts/dev_fake_up.sh`，須先後執行）
  - 完成條件(DoD): codex：A16 回 `url` 與 `user_code="ABCD-1234"`、`needs_code_input=false` → 輪詢 A17 於 5 秒內 `success`；claude：A16 回 `needs_code_input=true` → A18 送 `WRONG` → A17 `failed` 且 `fallback_command="docker compose exec -it -u app app claude auth login"` → 重新 A16 → A18 送 `FAKE-CODE-123` → `success`；同引擎進行中再 A16 → 409 `LOGIN_IN_PROGRESS`；對 codex session 呼叫 A18 → 409 `CODE_NOT_EXPECTED`；未知 session → 404；逾時案例 → `failed`「登入逾時，請重試」且子行程已結束；A19 後 A2 顯示未登入；`engine=gpt` → 400 `BAD_ENGINE`；A20：codex 流程進行中取消 → 回 ok、該 session 狀態 `failed`「已取消」、子行程已結束（`os.kill(pid,0)` 拋 ProcessLookupError）、立即再 A16 不回 409；之後替身 3 秒到期也不會出現已登入標記
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_cli_login.py`

- [ ] **T20 Google 欄位對應與可編輯判定**
  - 所屬功能: F12 寫入日曆、F20 編輯行程、F22 唯讀行程
  - 內容: EventDraft ↔ Google 行程欄位雙向對應、可編輯判定、CalendarEventItem 轉換
  - 做法: 新增 `backend/app/google/mapping.py`（`draft_to_body(draft, *, extended=None, for_patch=False)`：依規格書「寫入／讀回 Google 的欄位對應」表；`for_patch=True` 時 `recurrence_locked` 不送 recurrence、`reminder="custom"` 不送 reminders、永不送 extendedProperties；`body_to_draft(event, calendar_tz)`；`editability(event, access_role) -> (bool, reason)` 依「可編輯判定」表；`to_item(event, calendar) -> CalendarEventItem`，時間換算到 `DEFAULT_TIMEZONE`、全天 end 減 1 天、顏色一律取所屬日曆色）、`backend/tests/test_mapping.py`
  - 依賴: T12、T13
  - 完成條件(DoD): 全天 2026-11-10 → body `end.date=2026-11-11`，讀回 `end_date=2026-11-10`；非全天 19:00 → `start.dateTime=2026-11-04T19:00:00`、`timeZone=Asia/Taipei`；reminder `1440` → overrides `[{"method":"popup","minutes":1440}]`、讀回 `1440`；Google `{"useDefault":false,"overrides":[{popup,10},{email,60}]}` 讀回 `custom` 且 `for_patch` body 不含 reminders；`RRULE:FREQ=MONTHLY;BYDAY=2TU` 讀回 `recurrence_locked=true` 且 patch body 不含 recurrence；可編輯判定表四列各一案例（含 `seed-invite` 形狀 → 「這是別人邀請你的行程，只能在 Google 日曆回覆」）；`Asia/Tokyo` 10:00 的行程轉 item 為 `09:00+08:00`；`draft_to_body→body_to_draft` 來回一致（10 個欄位逐一比對）
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_mapping.py`

- [ ] **T21 日曆清單與期間行程（A5、A7）**
  - 所屬功能: F8 目標日曆、F18 日曆頁：檢視
  - 內容: Google API 用戶端、列日曆、讀期間行程
  - 做法: 新增 `backend/app/google/calendar.py`（以 `googleapiclient.discovery.build("calendar","v3", credentials, static_discovery=True, client_options={"api_endpoint": GOOGLE_API_BASE_URL})`；Google 錯誤對應：401 → `GOOGLE_AUTH_EXPIRED`、其他 → `GOOGLE_ERROR`；`list_calendars()`、`list_events(cal_id, start, end)` 分頁讀完、`day_events(cal_id, date, tz)` 供重複偵測）、`backend/app/routes/calendars.py`（A5）、`backend/app/routes/calendar_events.py`（A7；之後 T22 在同檔加端點）；新增 `backend/tests/test_calendar_read.py`（替身 Google 於隨機 port＋已授權 token）
  - 依賴: T18、T20、T10
  - 完成條件(DoD): A5 回 3 本，`writable` 依序 true／true／false，`primary.name="我的日曆"`；A7 `start=2026-11-01&end=2026-12-01&calendars=primary,holidays` 回的「週會」恰 5 筆且日期為硬編碼的 11/02、11/09、11/16、11/23、11/30，`seed-invite` 的 `editable=false`；`end-start=63` 天 → 400 `RANGE_TOO_LARGE`、62 天 → 200；某本日曆 id 不存在 → 其他日曆照常回傳且 `errors` 有該 id；未連結 → 409 `GOOGLE_NOT_CONNECTED`；`/_revoke_all` 後 → 401 `GOOGLE_AUTH_EXPIRED`；`day_events("primary", 2026-11-04)` 回「部門聚餐」
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_calendar_read.py`

- [ ] **T22 單筆行程讀取、修改、刪除（A8～A10）**
  - 所屬功能: F20 編輯行程、F21 刪除行程、F22 唯讀行程、F24 重複行程的編輯與刪除
  - 內容: 讀最新內容（實例換系列主行程）、以 etag 修改、刪除並同步本機紀錄
  - 做法: 改寫 `backend/app/google/calendar.py`（只加 `get_event`、`patch_event(If-Match)`、`delete_event`；412 → `EVENT_CHANGED` 並附最新 EventDetail）；改寫 `backend/app/routes/calendar_events.py`（只加 A8、A9、A10；A9／A10 先做可編輯判定，唯讀回 403 `EVENT_READ_ONLY`；A9 先 `normalize` 再以 `mode="edit"` 驗證，不完整回 422；成功後若 `history` 有對應 `(calendar_id, google_event_id)`，更新快照欄位、`event_json`、`updated_at`；A10 對應列改 `status='deleted'`、`deleted_source='web'`）；新增 `backend/tests/test_calendar_write.py`
  - 依賴: T21、T04
  - 完成條件(DoD): A8 以「週會」11/09 實例 id 呼叫 → 回 `event_id="seed-weekly"`、`is_series=true`、`draft.recurrence_text="每週一，不結束"`；A9 把 `seed-gym` 地點改「健身工廠」、結束 08:30 → 替身 `/_state` 中 `location`、`end.dateTime=2026-11-05T08:30:00`，`organizer` 不變；用舊 etag → 409 `EVENT_CHANGED` 且回應 `latest.draft` 為替身最新內容；A9／A10 對 `seed-invite` → 403；A9 對 `seed-complex` 改地點 → recurrence 原樣；以 `/_phone_add` 建一筆無標題行程後 A9 只改地點 → 200，替身 `summary` 仍不存在（未被寫成「（無標題）」）；A8 對有本機紀錄的行程回 `source_type`、`source_url`；A10 對「週會」實例 id → 替身 `seed-weekly` 消失；A10 對不存在的 id → 200；有 history 對應的行程被 A9 修改後該列 `title` 更新、被 A10 刪除後 `status='deleted'`、`deleted_source='web'`
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_calendar_write.py`

---

## 五、後端：新增行程與歷史 API

### 這一群怎麼做

把前面的零件接成三組 API：寫入與重算（A6、A4，T23）、解析（A3，T24）、歷史與同步（A11、A12，T25）。

- [ ] **T23 寫入行程與重算（A6、A4）**
  - 所屬功能: F12 寫入日曆、F23 手動新增、F10 重複偵測＋撞期
  - 內容: 逐筆寫入 Google 並記錄、冪等、手動新增來源、草稿重算
  - 做法: 改寫 `backend/app/google/calendar.py`（只加 `insert_event`）；新增 `backend/app/routes/events.py`（A6：`source=manual` 時建立 `parse_sessions`（engine `none`、source_type `manual`）；每筆先 `normalize` 再驗證（`mode="new"`）、已成功過的 `(parse_id,draft_id)` 直接回既有結果；insert 前以 `privateExtendedProperty` 查 `parse_id`＋`draft_id`，已存在就不 insert、直接補寫 `history`；`draft_to_body` 加 `extended={"ai_secretary":"1","parse_id","draft_id"}`；成功寫 `history`；逐筆捕捉錯誤不中斷其他筆）、`backend/app/routes/check.py`（A4：`normalize`＋依 `mode` 驗證＋`describe`＋`dedupe.check`（history 從 DB、Google 當天行程用 `day_events`，讀取失敗只略過並在回應 `notice` 填「無法讀取 Google 日曆，未檢查撞期」））；新增 `backend/tests/test_events_api.py`
  - 依賴: T22、T14、T13
  - 完成條件(DoD): 寫入「跟小王吃飯」2026-11-04 19:00–21:00 → 回 `ok=true`，替身中 `extendedProperties.private.ai_secretary="1"`、`reminders.useDefault=true`、description 原樣；`history` 1 列欄位正確；同 parse_id＋draft_id 再送 → 回同一 `history_id`、替身行程數不變；3 筆中第 2 筆 `end_time` 缺 → 整批先 422 `INCOMPLETE_EVENT` 且 `draft_ids=["e2"]`、替身零新增；以替身讓第 2 筆 insert 失敗（monkeypatch）→ 第 1、3 筆 ok、第 2 筆 `ok=false` 有 error；中斷模擬：monkeypatch 讓 `history` 寫入在 Google insert 成功後拋例外 → 回 `ok=false`；解除後同請求重送 → 回 `ok=true`、替身該 parse_id＋draft_id 的行程**仍只有 1 筆**、`history` 補上 1 列；`source=manual` 新 uuid → `parse_sessions` 有 `engine='none'`；`source=parsed` 不存在的 id → 404；A4：寫入後同時間同標題的草稿 → `duplicate_history`＋`duplicate_google`；`exclude_event_id` 為自己時不出自己的撞期；以 `mode="edit"`、`exclude_event_id="seed-weekly"` 檢查週會 11/09 的草稿 → 無 `conflict`／`duplicate_google`；Google 未連結時 A4 仍回 `missing_fields`、無 Google 類警告、`notice` 為 null；`/_revoke_all` 後 A4 回 200 且 `notice` 為「無法讀取 Google 日曆，未檢查撞期」；A4 回傳的草稿已正規化（送 `all_day=null`＋`start_time` → 回 `all_day=false`）
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_events_api.py`

- [ ] **T24 解析 API（A3）**
  - 所屬功能: F1 文字、F2 連結、F3 圖片、F5 AI 解析、F6 預覽清單
  - 內容: 規格書「解析流程（A3）」步驟 1～8
  - 做法: 新增 `backend/app/routes/parse.py`（multipart；輸入檢查；來源判定；連結 → `fetch_text`；圖片 → Pillow 轉 RGB、縮長邊 ≤1568、存 JPEG 品質 85 到 `DATA_DIR/tmp/`、`finally` 刪原檔與縮圖；呼叫 `ai.runner.parse`；轉 EventDraft（`draft_id`、`selected`、`reminder`、`description`）；驗證、白話、重複偵測（primary）；疑似重複取消勾選；寫 `parse_sessions`）；新增 `backend/tests/test_parse_api.py`
  - 依賴: T15、T16、T17、T23、T04
  - 完成條件(DoD): 「下週三晚上7點跟小王在信義區吃飯」→ 1 筆、`missing_fields` 含 `end_time`、warnings 含「撞期：部門聚餐 19:30–20:30」；「講座系列…」→ 3 筆 `e1`～`e3`；「瑜珈」→ `recurrence_text="每週三，到 2026/12/31（共 10 次）"`；「家庭日」→ `inferred_fields=["start_date"]`、`missing_fields` 不含日期；「牙醫」→ `missing_fields` 含 `all_day`；連結 `event.html`（測試內起的 http.server）→ `source_type="link"`、description 含「來源：<該網址>」；文字中夾網址（非單一網址）→ `source_type="text"`、`source_url` 為該網址、且未呼叫 fetch（spy）；圖片 PNG → 「海報音樂會」且結束後 `tmp/` 為空；圖片解析失敗（「格式壞掉」附圖）→ `tmp/` 仍為空；空輸入 400 `EMPTY_INPUT`；20,001 字 400；11MB 413；`.txt` 415；`engine=claude` 未登入 409；「天氣很好」→ `events=[]`、`notice` 含「沒看到行程」；`parse_sessions` 有 1 列且 `source_text` 為輸入原文
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_parse_api.py`

- [ ] **T25 歷史與同步（A11、A12）**
  - 所屬功能: F13 歷史紀錄頁
  - 內容: 規格書「與 Google 同步規則」、歷史分頁、刪除本機紀錄
  - 做法: 新增 `backend/app/google/sync.py`、`backend/app/routes/history.py`（A11 先同步再分頁回傳，不含 `event_json`；A12）；新增 `backend/tests/test_history_api.py`
  - 依賴: T23
  - 完成條件(DoD): 經 A6 加入 3 筆後 A11 回 3 筆（新到舊）、`synced=true`；`/_phone_edit` 改其中一筆標題為「跟小王吃火鍋」→ 再 A11 該列標題更新；`/_phone_delete` 另一筆 → 該列 `status='deleted'`、`deleted_source='google'`；Google 未連結 → `synced=false`、資料照回；`/_revoke_all` → `synced=false`、`sync_error` 有原因、資料照回；A12 刪除後該列消失、替身行程仍在；不存在 id → 404；插 120 筆 → `page=3` 回 20 筆、`total=120`
  - 驗證方式: `cd backend && .venv/bin/python -m pytest -q tests/test_history_api.py`

---

## 六、前端頁面

### 這一群怎麼做

先做 API 呼叫層與偏好儲存（T26）。新增行程頁拆三步：輸入卡（T27）、共用的行程卡片與重複編輯器（T28）、預覽與寫入（T29、T30）。日曆頁拆三步：外框與月檢視（T31）、週與清單檢視（T32）、詳情與編輯對話框（T33）。最後是歷史頁（T34）與設定頁（T35）。每張 UI 票都遵守「使用說明」的 UI 票規定。

- [ ] **T26 前端 API 層與偏好**
  - 所屬功能: 基礎建設
  - 內容: 型別、API 函式、錯誤處理、偏好儲存、頂欄替身標籤
  - 做法: 新增 `frontend/src/lib/types.ts`（EventDraft、CalendarEventItem、EventDetail、Status… 對應規格書欄位表）、`frontend/src/lib/api.ts`（A1～A19 每個一個函式；非 2xx 時拋 `ApiError{code,message,extra}`；JSON 請求帶 `Content-Type: application/json`）、`frontend/src/lib/prefs.ts`（上次 AI、上次日曆、顯示哪些日曆、日曆檢視；讀寫 try/catch）、`frontend/src/hooks/useStatus.ts`；改寫 `frontend/src/App.tsx`（只加：`fake_mode` 時頂欄黃色「替身模式」Badge）；新增 `frontend/src/__tests__/api.test.ts`
  - 依賴: T07
  - 完成條件(DoD): 以 mock fetch 驗證：A3 以 FormData 送出 `engine`、`text`、`image`；A9 以 PATCH 送 `{etag, draft}`；錯誤回應 `{"error":{"code":"AI_TIMEOUT","message":"…"}}` → 拋出的 ApiError `code="AI_TIMEOUT"`、`message` 原樣；`EVENT_CHANGED` 的 `latest` 放在 `extra.latest`；prefs 在 localStorage 拋例外時回預設值不崩潰；`fake_mode=true` 時頂欄出現「替身模式」，false 時不出現
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/api.test.ts`

- [ ] **T27 新增行程頁：輸入卡**
  - 所屬功能: F1 文字、F2 連結、F3 圖片、F4 AI 引擎選擇
  - 內容: 文字框、字數、圖片拖放／選檔／Ctrl+V、AI 下拉、解析鈕與解析中／錯誤狀態
  - 做法: 新增 `frontend/src/components/ImageDrop.tsx`、`frontend/src/components/InputCard.tsx`；改寫 `frontend/src/pages/NewEventPage.tsx`（整份改寫：頁標題＋InputCard；解析結果先以 `onParsed` 往上交，預覽留給 T29）；新增 `frontend/src/__tests__/InputCard.test.tsx`。遵守 UI 票規定
  - 依賴: T26、T19（截圖配方需要 `--connect-google`、`--login-ai` 與 A2）
  - 完成條件(DoD): 狀態矩陣「新增行程」的「初次載入」「AI 皆未登入」「解析中」「錯誤（解析）」四格各有測試並與文案逐字一致（含 placeholder 與拖放區文字）；`FETCH_NEEDS_PASTE` 顯示「改貼文字」，按下後文字框清空且取得焦點；`ENGINE_NOT_LOGGED_IN` 顯示「前往設定」連結到 `/settings`；20,001 字時「解析」停用且顯示字數超過；拖放 11MB 檔 → 前端即顯示「圖片太大（上限 10MB）」不送出；`.txt` → 「只支援 PNG、JPEG、WebP、GIF 圖片」；剪貼簿貼上 image 項目 → 出現縮圖與「移除」；AI 下拉記住上次選擇；UI 票規定 1～5 全部達成，截圖 `.pipeline/rounds/01/evidence/T27-ui.png`、`T27-ui-dark.png`（路徑 `/`）
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/InputCard.test.tsx`；截圖配方（路徑 `/`）

- [ ] **T28 行程卡片與重複編輯器**
  - 所屬功能: F6 預覽清單、F7 重複行程、F9 提醒、F11 行程說明
  - 內容: 預覽與編輯共用的行程表單元件
  - 做法: 新增 `frontend/src/components/EventForm.tsx`（標題、全天切換、日期時間、地點、重複、提醒、說明；缺欄位紅框「請填寫」、欄位錯誤訊息、警告與「AI 推測」Badge；`recurrence_locked` 時顯示原規則＋「請到 Google 日曆修改重複設定」且不可編輯；`reminder="custom"` 時下拉多一項「自訂（維持原設定）」）、`frontend/src/components/RecurrenceEditor.tsx`、`frontend/src/components/EventCard.tsx`（左側日曆色條＋勾選框＋EventForm；`variant`：預覽／已加入／失敗）；新增 `frontend/src/__tests__/EventCard.test.tsx`。遵守 UI 票規定
  - 依賴: T26
  - 完成條件(DoD): `missing_fields=["end_time"]` → 結束時間紅框且有「請填寫」與 Badge「缺欄位」；`inferred_fields=["start_date"]` → Badge「AI 推測」；warnings 三種各顯示對應文案；勾「全天」→ 時間欄隱藏並觸發 `onChange` 帶 `all_day=true`；RecurrenceEditor 選「每週」勾三、結束「共 5 次」→ `onChange` 的 recurrence 為 `{freq:"WEEKLY",interval:1,by_weekday:["WE"],until:null,count:5}`；`recurrence_locked` → 編輯控制項不存在且顯示原規則字串；200 字標題時卡片不溢出；鍵盤 Tab 順序為 勾選→標題→日期→時間→地點→重複→提醒→說明；UI 票規定 1～4 達成（截圖由 T29 涵蓋）
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/EventCard.test.tsx`

- [ ] **T29 新增行程頁：預覽清單**
  - 所屬功能: F6 預覽清單、F8 目標日曆、F10 重複偵測＋撞期
  - 內容: 預覽區（找到 N 筆、目標日曆下拉、卡片清單、修改後重算）
  - 做法: 新增 `frontend/src/components/PreviewList.tsx`（目標日曆下拉只列 `writable`，預設上次選擇或 primary；載入時目標不是 primary → 立即呼叫 A4；欄位失焦防抖 400ms 呼叫 A4；換日曆呼叫 A4）；改寫 `frontend/src/pages/NewEventPage.tsx`（只加：把 InputCard 結果交給 PreviewList、無行程時 EmptyState）；新增 `frontend/src/__tests__/PreviewList.test.tsx`。遵守 UI 票規定
  - 依賴: T27、T28、T24（截圖需要 A3～A5）
  - 完成條件(DoD): 狀態矩陣「無行程」「有資料」「缺欄位」「Google 未連結」四格各有測試；日曆下拉不含「台灣節日」；記住的日曆為 `work` 時載入後 A4 被以 `calendar_id="work"` 呼叫 1 次；修改結束時間後 400ms 內只呼叫 A4 一次（fake timers）；疑似重複的卡片初始未勾選；底部按鈕文案「加入日曆（N 筆）」N 等於勾選且完整的筆數，有缺欄位時停用並顯示「有 K 筆勾選的行程還缺資料」；截圖 `T29-ui.png`、`T29-ui-dark.png`：在 dev 環境輸入「下週三晚上7點跟小王在信義區吃飯」解析後的畫面（用 Playwright 腳本操作後截圖，腳本存 `frontend/scripts/screenshots/t29.mjs`）
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/PreviewList.test.tsx`；`scripts/dev_fake_up.sh --build-frontend --reset --connect-google --login-ai && node frontend/scripts/screenshots/t29.mjs && scripts/dev_fake_down.sh`

- [ ] **T30 新增行程頁：寫入結果與手動新增**
  - 所屬功能: F12 寫入日曆、F23 手動新增
  - 內容: 加入日曆、逐筆結果、重試、再新增一筆、手動新增
  - 做法: 新增 `frontend/src/components/SubmitBar.tsx`（底部固定動作列）；改寫 `frontend/src/components/PreviewList.tsx`（只加：送出 A6、逐筆結果與重試、全成功 Toast、「再新增一筆」）；改寫 `frontend/src/components/InputCard.tsx`（只加「手動新增」按鈕：產生 uuid 與 1 張空白草稿 `all_day=null`、`timezone` 預設、交給 PreviewList 並以 `source=manual` 送出）；新增 `frontend/src/__tests__/Submit.test.tsx`；新增 `docs/features/add-events.md`（新增行程功能群：文字／連結／圖片／手動、預覽、重複偵測、寫入；檔案組成、資料流、對應 T12～T16、T23、T24、T27～T30）。遵守 UI 票規定
  - 依賴: T29
  - 完成條件(DoD): 狀態矩陣「手動新增」「寫入中」「寫入結果」「Google 授權過期」四格各有測試；2 筆中 1 筆失敗 → 成功卡「已加入」＋「在 Google 日曆開啟」、失敗卡顯示錯誤與「重試」，按重試只送失敗那筆；全成功 Toast「已加入 2 筆行程」、底部變「再新增一筆」，按下清空輸入與預覽；手動新增送出的請求 `source="manual"`；`GOOGLE_AUTH_EXPIRED` 時卡片內容保留；截圖 `T30-ui.png`、`T30-ui-dark.png`（寫入成功後畫面，腳本 `frontend/scripts/screenshots/t30.mjs`）；`docs/features/add-events.md` 存在
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/Submit.test.tsx`；`scripts/dev_fake_up.sh --build-frontend --reset --connect-google --login-ai && node frontend/scripts/screenshots/t30.mjs && scripts/dev_fake_down.sh`

- [ ] **T31 日曆頁：外框、側欄與月檢視**
  - 所屬功能: F18 日曆頁：檢視、F19 日曆頁：連動更新
  - 內容: 工具列、側欄、資料讀取與定時重讀、月檢視
  - 做法: 新增 `frontend/src/components/calendar/CalendarToolbar.tsx`（今天、‹ ›、期間標題「2026 年 11 月」、月／週／清單 Tabs）、`CalendarSidebar.tsx`（「＋新增」、MiniMonth、日曆清單勾選與色點）、`MiniMonth.tsx`、`MonthView.tsx`（週日起 7×6、今天主色圓（`today` 來自 A2）、每格最多 3 筆、「還有 N 筆」Popover、點空白日期觸發 `onCreate(date)`、行程塊可 Tab 聚焦、AI 祕書行程 ✦、文字顏色：依規格書「行程顏色」規則在白字與 `--event-dark-text`（`#1f1f1f`，規格書指定值，定義在 `styles.css`）之間取 WCAG 對比較高者，函式放 `frontend/src/lib/contrast.ts`）、`frontend/src/hooks/useCalendarEvents.ts`（依檢視算期間呼叫 A7；頁面可見時每 60 秒與 `focus` 時重讀；重讀時保留舊資料）；改寫 `frontend/src/pages/CalendarPage.tsx`（整份改寫）；改寫 `frontend/src/styles.css`（只加 `--event-dark-text` 一行亮暗共用）；新增 `frontend/src/__tests__/MonthView.test.tsx`。遵守 UI 票規定
  - 依賴: T26、T19、T21（截圖需要替身登入與 A7）
  - 完成條件(DoD): `contrast.ts` 對 `#4285f4` 回深色字、`#0b8043` 回白字、`#7986cb` 回深色字（硬編碼期望，來源：規格書「行程顏色」例）；狀態矩陣「日曆」的「Google 未連結」「載入中（首次）」「重新讀取中」「有資料」「期間無行程」「部分日曆讀取失敗」「所有日曆都未勾選」七格各有測試；月檢視 2026-11 第一列為 11/01～11/07（硬編碼），10/25 在 10 月檢視有主色圓；某日 10 筆 → 顯示 3 筆＋「還有 7 筆」；取消勾選日曆後該日曆行程消失且重新 mount 後仍取消；fake timers 前進 60 秒 → A7 再被呼叫 1 次，`document.hidden=true` 時不呼叫；`focus` 事件觸發重讀；截圖 `T31-ui.png`、`T31-ui-dark.png`（dev 環境 `/calendar` 切到 2026 年 11 月，腳本 `frontend/scripts/screenshots/t31.mjs`），畫面可見週會、部門聚餐、健身房、客戶簡報、讀書會
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/MonthView.test.tsx`；`scripts/dev_fake_up.sh --build-frontend --reset --connect-google --login-ai && node frontend/scripts/screenshots/t31.mjs && scripts/dev_fake_down.sh`

- [ ] **T32 日曆頁：週檢視與清單檢視**
  - 所屬功能: F18 日曆頁：檢視
  - 內容: 週時間軸檢視（含全天列、重疊分欄、目前時間線）與 30 天清單檢視
  - 做法: 新增 `frontend/src/components/calendar/WeekView.tsx`（每小時 48px、預設捲到 07:00、全天列、重疊並排、今天欄底色、目前時間主色線、點空白時段觸發 `onCreate(date, hour)`）、`frontend/src/components/calendar/AgendaView.tsx`（依日期分組「11/04（三）」、時間或「全天」、色點、標題、地點；「載入更多」+30 天；空 → EmptyState「這段期間沒有行程」）；改寫 `frontend/src/pages/CalendarPage.tsx`（只加兩種檢視的切換與記住檢視）；新增 `frontend/src/__tests__/WeekAgenda.test.tsx`。遵守 UI 票規定
  - 依賴: T31
  - 完成條件(DoD): 週檢視 19:30–20:30 的行程塊 `top=19.5×48=936px`、`height=48px`（硬編碼）；兩個重疊行程各佔一半寬度；全天行程出現在全天列不在時間軸；捲動位置初始為 `7×48=336px`；清單檢視分組標題格式「11/04（三）」；「載入更多」後 A7 以新期間被呼叫；檢視選擇重新 mount 後保留；截圖 `T32-ui.png`（週檢視 11/01–11/07）、`T32-ui-agenda.png`（清單）、`T32-ui-dark.png`，腳本 `frontend/scripts/screenshots/t32.mjs`
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/WeekAgenda.test.tsx`；`scripts/dev_fake_up.sh --build-frontend --reset --connect-google --login-ai && node frontend/scripts/screenshots/t32.mjs && scripts/dev_fake_down.sh`

- [ ] **T33 日曆頁：詳情、編輯、新增、刪除對話框**
  - 所屬功能: F20 編輯行程、F21 刪除行程、F22 唯讀行程、F23 手動新增、F24 重複行程的編輯與刪除
  - 內容: 詳情對話框、編輯／新增對話框（含衝突處理）、刪除確認
  - 做法: 新增 `frontend/src/components/EventDetailDialog.tsx`（開啟時立即呼叫 A8 讀最新完整內容，載入中 Skeleton、失敗顯示錯誤與「重試」；圖示列、說明、重複白話、提醒、日曆名、原時區、AI 祕書 Badge 與來源連結（`source_url`）、唯讀 Badge＋原因、「在 Google 日曆開啟」、可編輯時「刪除」「編輯」）、`frontend/src/components/EventEditDialog.tsx`（編輯模式：直接使用詳情對話框剛讀到的 EventDetail 與 etag，不再重讀 → EventForm（日曆欄唯讀）→ A4 重算（`mode="edit"`、`exclude_event_id`＝系列主 id 或行程 id）→「儲存」A9；`EVENT_CHANGED` → 頂部警告條並換成 `extra.latest`；`EVENT_NOT_FOUND` → Toast 並關閉；新增模式：標題「新增行程」、日曆下拉只列可寫入、預填日期（週檢視另預填時段與 +1 小時）、儲存走 A6 `source=manual`）；改寫 `frontend/src/pages/CalendarPage.tsx`（只加對話框接線與成功後重讀）；新增 `frontend/src/__tests__/EventDialogs.test.tsx`；新增 `docs/features/calendar.md`（對應 T10、T20～T22、T31～T33）。遵守 UI 票規定
  - 依賴: T32、T28、T23（截圖與驗證需要 A6、A8～A10）
  - 完成條件(DoD): 狀態矩陣「日曆」其餘 11 格（詳情（可編輯）、詳情（唯讀）、詳情載入中、編輯中、儲存中、儲存成功、被別處修改、已被刪除、刪除確認、新增模式、Google 授權過期；與 T31 的 7 格合計 18 格全覆蓋）各有測試；點行程後 A8 被呼叫 1 次，按「編輯」後 A8 不再被呼叫；詳情顯示重複白話（週會為「每週一，不結束」）；唯讀詳情不存在「編輯」「刪除」按鈕且顯示原因原文；重複行程刪除確認含「會刪除整個系列（每週一，不結束）」；EVENT_CHANGED 後表單地點為 latest 的值；新增模式日曆下拉不含唯讀日曆、日期為點選日；Esc 關閉對話框且焦點回到行程塊；截圖 `T33-ui.png`（詳情）、`T33-ui-edit.png`（編輯）、`T33-ui-dark.png`，腳本 `frontend/scripts/screenshots/t33.mjs`；`docs/features/calendar.md` 存在
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/EventDialogs.test.tsx`；`scripts/dev_fake_up.sh --build-frontend --reset --connect-google --login-ai && node frontend/scripts/screenshots/t33.mjs && scripts/dev_fake_down.sh`

- [ ] **T34 歷史紀錄頁**
  - 所屬功能: F13 歷史紀錄頁
  - 內容: 同步狀態列、紀錄清單、開啟／編輯／從日曆刪除／刪除紀錄、分頁
  - 做法: 新增 `frontend/src/components/HistoryRow.tsx`；改寫 `frontend/src/pages/HistoryPage.tsx`（整份改寫；「編輯」開 T33 的 EventEditDialog；「從日曆刪除」走 A10；「刪除紀錄」走 A12；皆經 ConfirmDialog）；新增 `frontend/src/__tests__/HistoryPage.test.tsx`；新增 `docs/features/history.md`（對應 T04、T25、T34）。遵守 UI 票規定
  - 依賴: T33、T25（截圖需要 A11）
  - 完成條件(DoD): 狀態矩陣「歷史紀錄」九格各有測試；來源欄四種顯示「文字」「連結」（網址可點）「圖片」「手動」；AI 欄 `none` 顯示「—」；`status='deleted'` 依 `deleted_source` 顯示「已從日曆刪除」或「已在 Google 刪除」且三個動作停用；`synced=false` 顯示「無法與 Google 同步：<原因>，以下為本機紀錄」；120 筆時顯示「第 1／3 頁」；200 字標題截斷且有 title；截圖 `T34-ui.png`、`T34-ui-dark.png`（先以 API 加入 3 筆再截，腳本 `frontend/scripts/screenshots/t34.mjs`）；`docs/features/history.md` 存在
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/HistoryPage.test.tsx`；`scripts/dev_fake_up.sh --build-frontend --reset --connect-google --login-ai && node frontend/scripts/screenshots/t34.mjs && scripts/dev_fake_down.sh`

- [ ] **T35 設定頁**
  - 所屬功能: F14 設定頁：登入
  - 內容: Claude、Codex、Google 三張服務卡與登入流程面板
  - 做法: 新增 `frontend/src/components/ServiceCard.tsx`、`frontend/src/components/CliLoginPanel.tsx`（「取消」呼叫 A20 並關閉面板；codex：網址＋代碼＋複製鈕＋輪詢 A17 每 1 秒；claude：網址＋授權碼輸入＋送出 A18；失敗：訊息＋「重試」＋「也可以在終端機執行：」＋可複製後備指令）；改寫 `frontend/src/pages/SettingsPage.tsx`（整份改寫；讀 `?google=connected|error` 顯示 Toast）；新增 `frontend/src/__tests__/SettingsPage.test.tsx`；新增 `docs/features/settings-login.md`（對應 T17～T19、T35）。遵守 UI 票規定
  - 依賴: T26、T19（截圖需要 A2 與 A16～A20）
  - 完成條件(DoD): 狀態矩陣「設定」十格各有測試；codex 流程：按登入 → 顯示「ABCD-1234」→ A17 回 success → Badge「已登入」＋Toast「Codex 已登入」、按鈕變「登出」；codex 流程中按「取消」→ A20 被呼叫、面板關閉、Badge 仍「未登入」；claude 送錯碼 → 後備指令 `docker compose exec -it -u app app claude auth login` 可見；`google.configured=false` → 警告框文案逐字與規格書相同且按鈕停用；`?google=connected` → Toast；登出與中斷連結都有 ConfirmDialog；截圖 `T35-ui.png`、`T35-ui-dark.png`（未登入狀態，路徑 `/settings`）；`docs/features/settings-login.md` 存在
  - 驗證方式: `cd frontend && npm test -- --run src/__tests__/SettingsPage.test.tsx`；截圖配方（路徑 `/settings`，但 up 時不加 `--login-ai` 與 `--connect-google`）

---

## 七、打包與文件

### 這一群怎麼做

所有功能完成後才寫 Dockerfile（要 COPY 完整專案）（T36）；再做驗收用的替身覆寫檔並跑一次冒煙測試（T37）；最後寫 README，照 README 從乾淨狀態實際跑起來（T38）。

- [ ] **T36 容器化**
  - 所屬功能: F16 Docker 打包
  - 內容: Dockerfile、entrypoint、compose.yml、.dockerignore、.env.example
  - 做法: 新增 `Dockerfile`、`docker/entrypoint.sh`（可執行）、`compose.yml`、`.dockerignore`、`.env.example`，內容逐項照規格書「執行方式（Docker）」（含 `PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright`、entrypoint 修正 `/data` 擁有者後以 `setpriv` 降權、ports 用 `${PUBLIC_PORT:-8765}`、映像 `ENV PUBLIC_PORT=8765`）與「環境變數」。驗證：把專案複製到暫存目錄 `$ISO`（`rsync -a --exclude data --exclude .env --exclude .e2e-data --exclude .dev-data --exclude node_modules --exclude .venv --exclude .pipeline ./ "$ISO"/`），以下全部在 `$ISO` 內執行，compose 專案名 `ai-secretary-verify`、`PUBLIC_PORT=8767`；**不得在正式專案目錄建立、覆寫或刪除 `.env`、`data/`**
  - 依賴: T24、T25、T19、T30、T33、T34、T35
  - 完成條件(DoD): 在 `$ISO`：`cp .env.example .env` 並把 `PUBLIC_PORT` 設為 `8767`；`$ISO/data` 不存在 → `docker compose -p ai-secretary-verify up -d --build` 退出碼 0；輪詢 `curl -fsS http://localhost:8767/api/health` 回 `{"status":"ok"}`、`ps` 為 healthy；`$ISO/data` 與 `data/app.db` 的 `stat -c %u` 皆為 1000；`exec app stat -c %U /proc/1` 為 `app`；`exec -u app app claude --version` 含 `2.1.233`、`codex --version` 含 `0.147.0`；`exec -u app app python -c` 啟動 Playwright Chromium 印出 `ok`；以 `exec -u app app python -c` 在 `parse_sessions` 插 1 列（parse_id `persist-check`）→ `down` → `up -d` → 該列仍在；`docker compose -p ai-secretary-verify run --rm --no-deps app ls -a /app` 不含 `.env`；`ss -ltn` 顯示 8767 只綁 `127.0.0.1`；`curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost:8767' http://127.0.0.1:8767/settings` 為 200；正式專案目錄的 `.env`、`data/` 在本票前後狀態相同（執行前後以 `ls -la --time-style=full-iso` 比對）
  - 驗證方式: 依 DoD 逐項執行；結束 `docker compose -p ai-secretary-verify down`、`ss -ltn | grep -c ':8767 '` 為 0、刪除 `$ISO`

- [ ] **T37 驗收用替身覆寫與冒煙測試**
  - 所屬功能: 基礎建設
  - 內容: `compose.e2e.yml`（替身 AI、替身 Google、測試網站）與一次冒煙測試
  - 做法: 新增 `compose.e2e.yml`，內容逐項照規格書「全域驗收清單 › 驗收環境」（`app` 的 ports 用 `!override`）；新增 `scripts/e2e_smoke.sh`（up → 健康 → 走一次 Google 替身授權 → 替身 codex 登入 → A3 解析「小王吃到九點」→ A6 寫入 → `/_state` 驗證 → down，非互動，trap 收尾）
  - 依賴: T36
  - 完成條件(DoD): `scripts/e2e_smoke.sh` 退出碼 0；過程中 `curl -s http://localhost:8766/api/status` 的 `fake_mode=true`；寫入後 `curl -s http://127.0.0.1:9000/_state` 含「跟小王吃飯」；容器內 `http://fixture-site:9100/event.html` 可抓（A3 以該網址解析得「金曲獎得主講座」）；`docker compose -p ai-secretary-e2e -f compose.yml -f compose.e2e.yml config` 中 `app` 只有一個 published port 8766；專案目錄沒有 `.env` 時照樣可起；結束後 8766、9000 釋放且正式設定的 `./data` 未被改動（執行前後 `find data -type f -newer <起始標記檔>` 為空）
  - 驗證方式: `scripts/e2e_smoke.sh; echo rc=$?`；`ss -ltn | grep -cE ':(8766|9000) '` 為 0

- [ ] **T38 README**
  - 所屬功能: 基礎建設
  - 內容: 安裝、Google 憑證建立、啟動、登入、測試、替身驗收環境、疑難排解
  - 做法: 新增 `README.md`，章節：功能簡介；需求（Docker Desktop＋WSL 整合）；**建立 Google 憑證**（Google Cloud 建專案 → 啟用 Calendar API → OAuth 同意畫面（外部、加入自己為測試使用者，或改「正式版」避免 7 天過期）→ 建「網頁應用程式」用戶端 → 已授權重新導向 URI 填 `http://localhost:8765/api/google/callback`（若改 `PUBLIC_PORT` 要一起改）→ 把 ID／Secret 填入 `.env`）；啟動 `cp .env.example .env` → `docker compose up -d --build`、停止 `docker compose down`；開 `http://localhost:8765`（必須用 `localhost`）；首次登入（設定頁三服務；後備指令 `docker compose exec -it -u app app claude auth login`、`docker compose exec -it -u app app codex login --device-auth`）；port 與健康檢查網址；測試指令（後端 pytest、前端 vitest）；替身驗收環境（`docker compose -p ai-secretary-e2e -f compose.yml -f compose.e2e.yml up -d --build`）；不用 Docker 的本機開發指令（`scripts/dev_fake_up.sh`、Vite dev server 5173）；疑難排解（登入逾時、Google 授權過期、codex 裝置碼登入需在 ChatGPT 設定開啟、CLI 版本升級要重驗）；資料位置與備份（`./data`）。驗證：把專案複製到暫存目錄 `$ISO`（`rsync -a --exclude data --exclude .env --exclude .e2e-data --exclude .dev-data --exclude node_modules --exclude .venv --exclude .pipeline ./ "$ISO"/`），以下全部在 `$ISO` 內執行，compose 專案名 `ai-secretary-verify`、`PUBLIC_PORT=8767`；**不得在正式專案目錄建立、覆寫或刪除 `.env`、`data/`**（「乾淨狀態」＝副本中沒有 `data/`、`.env`）
  - 依賴: T37
  - 完成條件(DoD): 在 `$ISO` 照 README「啟動」段逐字執行（僅把 `.env` 的 `PUBLIC_PORT` 改為 `8767`、`-p ai-secretary-verify`）→ `curl -fsS http://localhost:8767/api/health` 回 ok；照「測試指令」段執行兩套測試全綠；照「替身驗收環境」段起得來（`http://localhost:8766/api/health` ok）並能關閉；README 中每個指令都在本票實際執行過並把輸出存 `.pipeline/rounds/01/evidence/T38-readme-run.txt`，**例外**：需要真人操作的指令（真實 Claude／Codex 登入、真實 Google 授權）不執行，在證據檔逐條標「需人工，未執行（使用者手動驗收 M1）」；文件殘留自查：`rg -n -F -- 'docs/features.md' README.md docs/` 零命中（正控制：`rg -n -F -- 'docs/features/' README.md` 至少 1 筆）；`rg -n -F -- 'exec -it app ' README.md` 零命中（正控制：`rg -n -F -- 'exec -it -u app app ' README.md` 至少 1 筆）；正式專案目錄的 `.env`、`data/` 前後狀態相同
  - 驗證方式: 依 DoD 執行；結束後所有本票啟動的 compose 專案 down，`ss -ltn | grep -cE ':(8766|8767|9000) '` 為 0、刪除 `$ISO`

---

## 總表

| 票 | 所屬功能 | 內容 | 做法摘要 | 依賴 | 完成條件摘要 | 驗證方式 |
|---|---|---|---|---|---|---|
| T01 | 基礎建設 | 環境檢查 | 檢查指令＋補 .gitignore | — | 六項通過、.gitignore 完整 | grep／docker info |
| T02 | 基礎建設 | 後端骨架與測試護欄 | FastAPI、config、錯誤格式、SPA、autouse 護欄 | T01 | health 200、護欄可擋真實 CLI（變異驗證） | pytest＋curl |
| T03 | F17 | 安全中介層 | Host 完全相等、Origin／Sec-Fetch-Site | T02 | 惡意 Host 400、跨站 403 | pytest |
| T04 | F13 | 資料庫 | 建表 SQL、WAL、清理 | T02、T03 | 兩表三索引、清理邊界 | pytest |
| T05 | 基礎建設 | 前端骨架 | Vite＋React＋Tailwind＋shadcn＋路由 | T01 | build 成功、四頁路由 | npm build／test |
| T06 | F15 | 設計 token、主題、基礎元件 | styles.css token、ThemeToggle、shadcn 元件 | T05 | token 與規格逐一相同、主題記憶 | vitest |
| T07 | F15 | 共用元件與 /dev/ui | EmptyState、ConfirmDialog… 展示頁 | T06 | 展示頁亮暗截圖 | vitest＋截圖 |
| T08 | F5 | 替身 AI CLI（解析） | claude／codex 替身＋fixtures | T02 | 輸出格式與關鍵字回應正確 | pytest |
| T09 | F12 | 替身 Google（核心） | OAuth、calendarList、events CRUD、控制端點 | T02 | 授權、CRUD、revoke、reset | pytest |
| T10 | F18 | 替身 Google（進階） | singleEvents、patch／etag、標記查詢、模擬手機 | T09 | 週會 5 實例、412、cancelled | pytest |
| T11 | 基礎建設 | 本機替身開發腳本 | dev_fake_up／down | T02、T08、T09 | 起停、port 釋放、不殺他人行程 | 腳本＋curl |
| T12 | F6 | EventDraft 與完整性驗證 | models、validate | T02 | 規則 1～8 正反案例 | pytest |
| T13 | F7、F24 | 重複規則 | to_rrule、parse_rrule、describe | T12 | 「共 10 次」等硬編碼期望 | pytest |
| T14 | F10、F11 | 說明欄與重複偵測 | description、dedupe 純函式 | T12 | 邊界不撞期、變異驗證 | pytest |
| T15 | F4、F5 | AI 呼叫層 | schema、prompt、claude／codex、runner | T08 | 逾時、重試、錯誤遮罩 | pytest |
| T16 | F2 | 抓網頁與測試網站 | httpx→trafilatura→Playwright | T02 | 四頁行為、逾時 ≤21 秒 | pytest |
| T17 | F14 | CLI 登入狀態與替身登入 | 真實輸出證據、替身子指令、status | T08 | 證據檔、快取與失效 | pytest |
| T18 | F14 | Google 授權與狀態 API | oauth、A2、A13～A15 | T03、T09、T11、T17 | token 0600、state 一次性 | pytest＋腳本 |
| T19 | F14 | 網頁驅動 CLI 登入 | pexpect sessions、A16～A20 | T17、T03、T18 | 兩引擎流程、409、逾時 | pytest |
| T20 | F12、F20、F22 | 欄位對應與可編輯判定 | mapping 純函式 | T12、T13 | 全天＋1 天、custom、locked、唯讀四列 | pytest |
| T21 | F8、F18 | 日曆清單與期間行程 | calendar client、A5、A7 | T18、T20、T10 | 週會 5 筆、62 天上限 | pytest |
| T22 | F20～F22、F24 | 單筆讀改刪 | A8～A10、etag、history 同步 | T21、T04 | 實例換主行程、412→EVENT_CHANGED | pytest |
| T23 | F12、F23、F10 | 寫入與重算 | A6、A4 | T22、T14、T13 | 冪等、逐筆、manual、警告 | pytest |
| T24 | F1～F3、F5、F6 | 解析 API | A3 全流程 | T15、T16、T17、T23、T04 | 各來源、圖片暫存清空、錯誤碼 | pytest |
| T25 | F13 | 歷史與同步 | sync、A11、A12 | T23 | 手機改／刪反映、分頁 | pytest |
| T26 | 基礎建設 | 前端 API 層與偏好 | types、api、prefs、替身標籤 | T07 | 錯誤轉 ApiError、prefs 容錯 | vitest |
| T27 | F1～F4 | 輸入卡 | ImageDrop、InputCard | T26、T19 | 四格狀態、圖片限制、改貼文字 | vitest＋截圖 |
| T28 | F6、F7、F9、F11 | 行程卡片與重複編輯器 | EventForm、RecurrenceEditor、EventCard | T26 | 缺欄位、AI 推測、locked | vitest |
| T29 | F6、F8、F10 | 預覽清單 | PreviewList、A4 重算 | T27、T28、T24 | 四格狀態、防抖、日曆下拉 | vitest＋截圖 |
| T30 | F12、F23 | 寫入結果與手動新增 | SubmitBar、重試、手動新增 | T29 | 四格狀態、部分失敗重試 | vitest＋截圖 |
| T31 | F18、F19 | 日曆外框與月檢視 | 工具列、側欄、MonthView、定時重讀 | T26、T19、T21 | 七格狀態、3 筆＋還有 N 筆、60 秒重讀 | vitest＋截圖 |
| T32 | F18 | 週與清單檢視 | WeekView、AgendaView | T31 | 位置像素硬編碼、重疊分欄 | vitest＋截圖 |
| T33 | F20～F24 | 詳情／編輯／新增／刪除對話框 | EventDetailDialog、EventEditDialog | T32、T28、T23 | 其餘十一格狀態、衝突處理 | vitest＋截圖 |
| T34 | F13 | 歷史頁 | HistoryRow、HistoryPage | T33、T25 | 九格狀態、同步失敗、分頁 | vitest＋截圖 |
| T35 | F14 | 設定頁 | ServiceCard、CliLoginPanel | T26、T19 | 十格狀態、後備指令 | vitest＋截圖 |
| T36 | F16 | 容器化 | Dockerfile、entrypoint、compose、.dockerignore、.env.example（隔離副本驗證） | T24、T25、T19、T30、T33、T34、T35 | healthy、UID 1000、資料保留、無 .env | docker compose |
| T37 | 基礎建設 | 驗收替身覆寫與冒煙 | compose.e2e.yml、e2e_smoke.sh | T36 | 冒煙通過、正式 data 未動 | 腳本 |
| T38 | 基礎建設 | README | 安裝、Google 憑證、啟動、測試、疑難排解（隔離副本驗證） | T37 | 照 README 從乾淨狀態跑起來 | 逐字執行 |

---

## 自我稽核結果（2026-10-25）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 覆蓋對照 | F1～F24 每項至少一張票（以腳本比對「所屬功能」）；A1～A20 每支端點都有實作票；四頁狀態矩陣共 49 格（新增 12＝T27／T29／T30 各 4；日曆 18＝T31 的 7＋T33 的 11；歷史 9＝T34；設定 10＝T35）全數分配；基座票 T06／T07 存在，所有 UI 票經 T26 依賴它們；J0～J20 每條旅程對應的頁面與 API 皆有票 |
| 2 | 建造者模擬 | 補了：行程顏色一律日曆色（D41）、截圖腳本放 `frontend/scripts/screenshots/` 並在 T05 加 playwright、替身解析不檢查登入（避免 T17 改壞 T08）、路由自動掛載（避免多票改 `main.py`） |
| 3 | 實測員模擬 | J0～J20 每步都有具體輸入值、預期結果與驗證方法；J0 改在隔離副本；J1 加取消登入；日期與次數（每週三到年底共 10 次、11 月週一 5 次、11/10 為第二個週二）以指令驗算 |
| 4 | 模糊詞掃描 | DoD 中「適當／合理／正常運作／良好／之類／等等」零命中 |
| 5 | 依賴檢查 | 所有依賴都指向較小編號（無循環）；依「後票需要前票產物」建立；不可並行的票若會改同一檔案已加依賴（T03→T04、T18→T19），並以腳本確認可並行的票之間零共用檔案 |
| 6 | 指令檢查 | 所有驗證指令非互動；長駐服務皆背景啟動並確認 port 釋放；容器化票 T36 排在所有功能票之後、README 票 T38 依賴 T37→T36；六個功能群的最後一張票都含 `docs/features/` 文件 |
| 7 | 待問清單 | 無待問事項；所有自行決定的事項已記入規格書決策紀錄（標「預設，可改」） |

全域驗收清單以 `01-requirements.md` 的「全域驗收清單」章為唯一來源（本工作單只引用、不複製）。
