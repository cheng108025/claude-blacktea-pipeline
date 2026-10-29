# 按需驗證配方

只讀本次適用的節。任何 PASS 都要有本次實際證據；無能力／無隔離方式回 ENV_BLOCKED。記录命令、cwd、受測版本、exit code 與證據路徑；錯誤輸出不可直接洩漏機密。

## 驗證深度

- 單票／小修：本票 DoD＋受影響回歸測試，獨立檢查員重跑相同範圍。
- 階段整合：install/build/test；共享介面、套件、schema、build 設定改動需全套。
- 全域驗收：實測員驗實際旅程；單元測試不代替 UI／資料持久化證據。
- 只有需要驗證測試敏感度且收益合理才做變異；不要對文案、README、小樣式強制變異。

## 安全的服務生命週期

- CLI 是短程序，直接執行並驗退出碼；沒有 HTTP 就不要求 port／健康網址。
- 使用專案提供的測試啟動指令，指定測試資料路徑與獨立 port。已有服務占用時，不 `fuser -k`／`pkill`；改用隔離 port，或回 ENV_BLOCKED。
- 本機服務：在同一個非互動腳本中啟動、記錄本次 PID／啟動時間／cwd、輪詢有上限的健康檢查；HTTP 檢查要求正確狀態碼，連線成功不等於健康。finally／trap 只清理本次持有的 PID／process group；跨呼叫清理前核對行程身分，不能只信過期 PID。
- Docker：用本輪唯一 compose project 名稱及測試用 env／volume／port。`docker compose -p <name> up -d --build`，驗證後以同一 name `down`。不對 Docker proxy 用 kill；不使用正式 volume 或刪正式資料。
- 啟動逾時／清理不成功都保存證據並回 ENV_BLOCKED；不能無限輪詢。

## UI

- 依已確認 token、原型、目標尺寸與**適用**狀態測試；靜態頁不強求 loading／空資料／Toast／Dialog。
- 可使用原生語意控制項；只有產品選定元件系統時才要求沿用它。小頁面不強制另造元件庫、展示頁或 render-only 測試。
- 驗正常與必要錯誤／loading／disabled 狀態；檢查可讀性、鍵盤焦點、label、必要的操作回饋。長名稱是否折行依設計，不一律 nowrap。
- Playwright MCP 或專案安裝的 Playwright 均可。截圖存本次 task／attempt 路徑後實際打開檢視；截圖檔存在不等於外觀正確。
- 沒有瀏覽器只能列 API 結果與 UI NOT_RUN；不得聲稱 UI PASS。

## 變異副本

由檢查員執行：`python3 ~/.claude/blacktea/scripts/pipeline.py --root <project_root> snapshot --cwd <受測worktree> --output <R>/scratch/<task>-<attempt>`。

腳本複製 Git 追蹤檔與未忽略的新檔，排除流水線資料與機密；拒絕 symlink／submodule，以免副本引用原位置。輸出內容指紋，涵蓋新增、刪除與可執行權限。副本不是 OS sandbox：先核對測試資料設定，重新安裝獨立依賴；絕不把正式 DB／runtime 或 node_modules 以 symlink 接回去。

只在副本改壞實作、跑相關測試；測完保留證據即可，不需還原產品工作區。若無法建立隔離測試，記未做變異及原因，由可重現行為判斷，不在原地改壞再靠 git diff 還原。

## 紅燈重建（票級檢查員；票面有行為測試時一律做）

不論建造者有沒有 red log，檢查員自己證明新測試守得住新行為：

1. 用上節 snapshot 建副本，先在副本跑新測試確認綠。
2. 在副本把本票改過的**實作檔**換回 `git -C <project_root> show <base_head>:<路徑>` 的內容；base 不存在的新實作檔暫移到副本外，新測試保留。
3. 重跑新測試，輸出存 `<R>/evidence/<task>-<attempt>-preimage-red.log`。紅燈必須來自新行為的斷言；匯入失敗、依賴缺漏、服務沒起來不算。
4. 能正確重建舊行為而新測試仍全綠 → FAIL「測試沒守住新行為」。base 沒有可呼叫的公開介面時，改用針對新行為的相關變異；都做不到記原因並回 ENV_BLOCKED，不當 PASS。建造者的 red log 缺漏只記在檢查紀錄，不能取代這份獨立證據。

## 文件殘留自查（建造者寫、檢查員重跑）

改到對外格式、契約、文案或數字時，build-log 必有「文件殘留自查」節；沒改到寫「不適用：<原因>」。適用時記：

- 正控制：先對一個已知存在的字面查詢，證明查詢範圍與指令真的會命中。
- 舊字面與相關標題的固定字串查詢（例 `rg -n -F -- '<舊字面>' README.md docs/`），依專案實際文件路徑調整；讀檔錯誤或搜尋工具出錯不算零命中。
- 每份命中文件的處置：已更新／屬歷史紀錄保留（附理由）。
- 指令、退出碼、輸出路徑。

除錯殘留只掃實際 source 根目錄（含根目錄程式檔），排除 `.pipeline/`、`.git/`、依賴、虛擬環境、證據與生成物。檢查員親自重跑相關查詢；缺節、查詢出錯或仍有未處理的現行文件殘留 → FAIL。
