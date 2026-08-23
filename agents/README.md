# agents/——六個角色，一人一檔

> 此檔只給人看，Claude 不會把它當指示執行。設計理由與所有 🔧 旋鈕都在 `~/.claude/README.md`；執行檔只留 2–3 行門牌。

| 檔案 | 角色 | 是不是 subagent | 模型 | 誰召喚它 |
|---|---|---|---|---|
| `agent0_conduct.md` | 總指揮分身：在乾淨 context 裡跑階段二～五（建造→稽核→實測→FINAL-REPORT）或變更步驟 3–7；**關卡、回退、失敗出口規則全在它自己檔裡**；自己再 spawn 建造者／票級檢查員／稽核員／實測員；只回報完成／續跑／需使用者決定 | 是（`name: agent0-conduct`） | opus | `/blacktea_plan` 第 0 步與「監督迴圈」；`/blacktea_change` 步驟 2 之後（變更模式） |
| `agent1_plan.md` | 訪談官：把你的一句話問到零模糊，寫規格書、拆工單 | **不是**（刻意沒有 `name`） | 跟主對話（由你 `/model` 選的 session 模型決定） | `/blacktea_plan` 階段一用 Read 照做 |
| `agent2_build.md` | 建造者：一次做一張票，跑驗證方式，回報 | 是（`name: agent2-build`） | sonnet | `skills/blacktea-dispatch` ④ |
| `agent3_ticket_check.md` | 票級檢查員：一張票做完後獨立重跑驗證方式、驗 DoD、跑測試、核對檔案，回 PASS／FAIL／INCONCLUSIVE；PASS 才 commit | 是（`name: agent3-ticket-check`） | sonnet | `skills/blacktea-dispatch` ⑤ |
| `agent3_review.md` | 稽核員：全案稽核（能不能跑、bug、資安、架構對照、品質） | 是（`name: agent3-review`） | opus | agent0 階段三、變更步驟 4 |
| `agent4_run.md` | 實測員：真瀏覽器黑箱實測全部旅程 | 是（`name: agent4-run`） | sonnet | agent0 階段四、變更步驟 6 |

## 為什麼訪談官沒有 name

subagent 沒有 `AskUserQuestion` 工具——被召喚出去的分身中途不能問任何人。訪談官整個工作就是問你問題，所以它必須跑在主對話：總指揮用 Read 把 `agent1_plan.md` 讀進來照著做。官方規則是「agents/ 裡沒有 `name` 的檔案視為放在旁邊的文件，不註冊」，所以這個檔刻意不放 `name`。**不要幫它補上**，補了它會變成一個不能問人的分身。

## 為什麼票級檢查員跟稽核員分開

票級檢查是「照票面重跑驗證、對答案」的機械活，每張票至少跑一次；全案稽核是逐檔抓漏的判斷力活，一案只跑幾輪。原本票級檢查由稽核員兼任，每次 spawn 都載 14 KB 的稽核員人設＋預載技能、用 opus——拆開後票級檢查只載約 7 KB、用 sonnet。覺得檢查不夠嚴，把 `agent3_ticket_check.md` 的 `model` 改成 opus 即可，不要再合回去。

## 改這裡的檔案要注意

- 五個分身的 `name` 不能改：`skills/blacktea-dispatch`、`commands/blacktea_plan.md`、`commands/blacktea_change.md`、`agents/agent0_conduct.md` 都用這些名字召喚。
- `agent0_conduct.md` 是階段二～五與變更步驟 3–7 的**唯一**規則來源——想改建造／稽核／實測的串接、關卡、回退，改這裡；`commands/` 只剩主對話的分流與監督迴圈。subagent 巢狀深度官方預設上限 3 層（主對話 → agent0 → agent2/3/4），剛好夠用；**不要讓 agent0 再 spawn agent0**。
- `agent3_review.md` 的 `skills:` 預載 `agent3-quality-check`——被預載的 skill 只能設 `user-invocable: false`，不能設 `disable-model-invocation: true`（設了就預載不進來）。
- agent 檔的 markdown 全文會成為分身的 system prompt，**每次 spawn 都付一次**——不要在裡面寫解釋、設計理由或旋鈕表，那些放 README。
- 改完在 `~/.claude` commit（agents／skills 會自動重載，不用重啟）。六個角色的施工／檢查紀錄都寫進專案的 `.pipeline/`，角色之間靠檔案交接，不靠對話。
