# agents/——五個角色，一人一檔

> 此檔只給人看，Claude 不會把它當指示執行。

| 檔案 | 角色 | 是不是 subagent | 模型 | 誰召喚它 |
|---|---|---|---|---|
| `agent0_conduct.md` | 總指揮分身：在乾淨 context 裡跑階段二～五（建造→稽核→實測→FINAL-REPORT），自己再 spawn 建造者／稽核員／實測員；只回報完成／續跑／需使用者決定 | 是（`name: agent0-conduct`） | opus | `/blacktea_plan` 第 0 步（工單定稿、你開新對話之後）與「監督迴圈」 |
| `agent1_plan.md` | 訪談官：把你的一句話問到零模糊，寫規格書、拆工單 | **不是**（刻意沒有 `name`） | 跟主對話（由你 `/model` 選的 session 模型決定） | `/blacktea_plan` 階段一用 Read 照做 |
| `agent2_build.md` | 建造者：一次做一張票，跑驗證方式，回報 | 是（`name: agent2-build`） | sonnet | `skills/blacktea-dispatch` |
| `agent3_review.md` | 稽核員：票級檢查＋全案稽核（能不能跑、bug、資安、架構對照、品質） | 是（`name: agent3-review`） | opus | dispatch（票級）、`/blacktea_plan` 階段三、`/blacktea_change` 步驟 4 |
| `agent4_run.md` | 實測員：真瀏覽器黑箱實測全部旅程 | 是（`name: agent4-run`） | sonnet | `/blacktea_plan` 階段四、`/blacktea_change` 步驟 6 |

## 為什麼訪談官沒有 name

subagent 沒有 `AskUserQuestion` 工具——被召喚出去的分身中途不能問任何人。訪談官整個工作就是問你問題，所以它必須跑在主對話：總指揮用 Read 把 `agent1_plan.md` 讀進來照著做。官方規則是「agents/ 裡沒有 `name` 的檔案視為放在旁邊的文件，不註冊」，所以這個檔刻意不放 `name`。**不要幫它補上**，補了它會變成一個不能問人的分身。

## 改這裡的檔案要注意

- 四個分身的 `name` 不能改：`skills/blacktea-dispatch`、`commands/blacktea_plan.md`、`commands/blacktea_change.md` 都用這些名字召喚。
- `agent0_conduct.md` 自己不記任何階段規則——它 Read `commands/blacktea_plan.md` 的階段二～五照做。想改建造／稽核／實測行為去改那些檔，不要在這裡另寫一份。subagent 巢狀深度官方預設上限 3 層（主對話 → agent0 → agent2/3/4），剛好夠用；**不要讓 agent0 再 spawn agent0**。
- `agent3_review.md` 的 `skills:` 欄位列出它預載的兩個技能（`agent3-ticket-check`、`agent3-quality-check`）——那兩個 skill 只能設 `user-invocable: false`，不能設 `disable-model-invocation: true`（設了就預載不進來）。
- 每個檔開頭的「給使用者的導讀」列出該檔可以調整的地方（🔧）；改完在 `~/.claude` commit（agents／skills 會自動重載，不用重啟）。
- 四個角色的施工／檢查紀錄都寫進專案的 `.pipeline/`，角色之間靠檔案交接，不靠對話。
