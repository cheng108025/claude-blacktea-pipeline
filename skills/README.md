# skills/——技能，一技能一資料夾

> 此檔只給人看，Claude 不會把它當指示執行。

每個資料夾裡一定有 `SKILL.md`（技能本體），可能有 `references/`（長清單、表格、範例——技能跑到需要時才 Read，不佔平常的 context）。

| 資料夾 | 屬於誰 | 做什麼 | 能不能直接打 `/名稱` |
|---|---|---|---|
| `blacktea-dispatch/` | 總指揮／變更官 | 派工與版控：Ready Queue → 並行建造 → 每票票級檢查 → PASS 才 commit／push；修復批次；單 commit | 不能（由 `/blacktea_plan`、`/blacktea_change` Read 執行） |
| `agent1-interview/` | 訪談官技能 a | 問到整個架構清楚：定調三問＋評分表迴圈，≥9 分才停 | 不能（由 `agents/agent1_plan.md` 接力 Read） |
| `agent1-spec/` | 訪談官技能 b | 把需求寫成規格書（五個必備章） | 不能 |
| `agent1-tickets/` | 訪談官技能 c | 照規格書拆工單、自我稽核 7 項、Codex 覆核分級 | 不能 |
| `agent3-ticket-check/` | 稽核員技能 a | 每做完一張票：親自重跑驗證方式、驗 DoD、跑測試、核對檔案，PASS 才准 commit | 不能（預載進 `agents/agent3_review.md`） |
| `agent3-quality-check/` | 稽核員技能 b | 可讀、可維護、沒有多餘程式碼；只出 Medium/Low、不擋關 | 不能（預載進 `agents/agent3_review.md`） |
| `git/` | 一般技能 | git／GitHub 規範與 WSL 急救 | 能（`/git`），Claude 也會依情況自動讀 |
| `vscode/` | 一般技能 | VS Code 右鍵整合急救 | 能（`/vscode`） |

「不能直接打」的技能在 frontmatter 設了 `user-invocable: false`：它們不會出現在 `/` 選單，也不會在你打 `/agent3-ticket-check` 時執行——它們只在被對應的角色檔讀取或預載時生效。這是刻意的：流水線的入口只有 `commands/` 的三個指令。

## 兩種接力方式

- **Read 接力**（訪談官三技能、dispatch）：主對話把 SKILL.md 當劇本讀進來照做。因為跑在主對話，所以可以問你問題、可以管 git。
- **預載**（稽核員兩技能）：`agents/agent3_review.md` 的 frontmatter `skills:` 列出它們，稽核員分身每次被召喚時整份技能就在它的 context 裡。被預載的技能不可設 `disable-model-invocation: true`。

## 新增技能的慣例

資料夾名就是技能名（全小寫、連字號）；`SKILL.md` 開頭放 frontmatter（`name`、`description`、`user-invocable`）與「給使用者的導讀」；大表格放 `references/`；跨檔引用一律寫絕對路徑 `~/.claude/...`。改完在 `~/.claude` commit 並重啟 Claude Code。
