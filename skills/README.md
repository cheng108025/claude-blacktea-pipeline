# skills/——技能，一技能一資料夾

> 此檔只給人看，Claude 不會把它當指示執行。設計理由與所有 🔧 旋鈕都在 `~/.claude/agents/README.md`；執行檔只留 2–3 行門牌。

每個資料夾裡有 `SKILL.md`（技能本體）。流水線技能的清單、表格、範例**都寫在 SKILL.md 裡**——它們每次都會被讀，拆成 `references/` 只會多一次工具呼叫；唯一例外是 `agent1-tickets/references/codex-review.md`（可選步驟，問使用者要才讀）。

| 資料夾 | 屬於誰 | 做什麼 | 能不能直接打 `/名稱` |
|---|---|---|---|
| `blacktea-dispatch/` | 總指揮分身（agent0）／變更官 | 派工與版控：Ready Queue → 並行建造 → 每票票級檢查 → PASS 才 commit／push；修復批次；單 commit | 不能（agent0 在階段二／修復輪／階段五、變更官在步驟 2 單 commit 時 Read 執行） |
| `agent1-interview/` | 訪談官技能 a | 問到整個架構清楚：定調三問＋評分表迴圈，≥9 分才停；評分表與出題格式在檔內 | 不能（由 `agents/agent1_plan.md` 接力 Read） |
| `agent1-spec/` | 訪談官技能 b | 把需求寫成規格書（七個必備章（含每個專案都要有的「設計系統」）、有用 AI 時的「AI相關」章、15 章菜單在檔內） | 不能 |
| `agent1-tickets/` | 訪談官技能 c | 照規格書拆工單（六欄格式、T01、README 票）、自我稽核 7 項、可選 Codex 覆核（`references/codex-review.md`） | 不能 |
| `agent3-quality-check/` | 稽核員技能 b | 可讀、可維護、沒有多餘程式碼（15 條清單，含 UI 一致性）；只出 Medium/Low、不擋關 | 不能（預載進 `agents/agent3_review.md`；票級檢查員被指示「順帶品質檢查」時也 Read） |
| `git/` | 一般技能 | git／GitHub 規範與 WSL 急救 | 能（`/git`），Claude 也會依情況自動讀 |
| `vscode/` | 一般技能 | VS Code 右鍵整合急救（含一鍵連 WSL 轉接器） | 能（`/vscode`） |
| `clawd/` | 一般技能 | Clawd on Desk 桌面寵物急救（WSL 配對、mirrored 網路、驗證） | 能（`/clawd`） |

「不能直接打」的技能分兩種旗標設定：四個 **Read 接力**的技能（`blacktea-dispatch`、`agent1-*`）同時設 `user-invocable: false` 與 `disable-model-invocation: true`——對你、對 Claude 都隱藏，完全不進 context，只能靠角色檔用 Read 讀路徑載入；**預載**的 `agent3-quality-check` 只能設 `user-invocable: false`（官方規則：設了 `disable-model-invocation` 就預載不進去），所以 Claude 理論上仍可能自行載入，靠描述裡的「預載進 agent3-review」約束。這是刻意的：流水線的入口只有 `commands/` 的三個指令。

## 兩種接力方式

- **Read 接力**（訪談官三技能、dispatch）：執行者把 SKILL.md 當劇本讀進來照做。訪談官三技能跑在主對話（要問人）；dispatch 通常跑在 agent0 分身裡（不能問人，需要使用者決定的事交回呼叫方）。
- **預載**（quality-check）：`agents/agent3_review.md` 的 frontmatter `skills:` 列出它，稽核員分身每次被召喚時整份 SKILL.md 就在它的 context 裡（只含 SKILL.md，不含 `references/`）。被預載的技能不可設 `disable-model-invocation: true`。

## 新增技能的慣例

資料夾名就是技能名（全小寫、連字號）；`SKILL.md` 開頭放 frontmatter（`name`、`description`、`user-invocable`，Read 接力的再加 `disable-model-invocation`）與 2–3 行門牌（我是誰、誰呼叫我、旋鈕去 README 查）；內容寫給 AI，解釋寫進 README；每次都會讀的清單直接放 SKILL.md，真正可選的才放 `references/`；所有引用一律寫絕對路徑 `~/.claude/...`——因為技能是在專案目錄下被 Read 進來的，相對路徑會找不到檔。改完在 `~/.claude` commit（skills 會自動重載）。
