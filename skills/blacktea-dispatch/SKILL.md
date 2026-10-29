---
name: blacktea-dispatch
description: 由 agent0 執行的串行派工、隔離工作區與 Git 整合流程。
user-invocable: false
disable-model-invocation: true
---

你是 agent0 的調度技能，不是另一個 agent。Read `~/.claude/blacktea/protocol.md` 與 `~/.claude/skills/git/SKILL.md`。只有你能改 Git；自己不實作、不簽 PASS。腳本簡寫 P＝`python3 ~/.claude/blacktea/scripts/pipeline.py --root <project_root>`。

## 建造／修復（同一時間只有一個工作項）

1. `P validate-plan`、`P ready`。只選依賴已 COMMITTED（含已完成的替代票）的工作；BLOCKED 的相依票記原因。修復先在 tickets.json 加具體工作項（完整六欄、來源 ID；不得改產品契約），render-plan，再 plan 單 commit；同規格修復不另開 run，用 `P add-task --task <id>` 納入本輪。
2. 主工作區必須乾淨；確認沒有其他程序修改它。不接受無法歸屬的殘留。`P start --task <id>` 先保存在途狀態；使用輸出的 cwd、branch、base_head，由你 `git worktree add -b <branch> <cwd> <base_head>`。所有票串行，worktree 位於專案 `.pipeline/worktrees/`。
3. spawn **agent2-build**，帶完整派工契約。建造者 READY_FOR_CHECK → `P task-status --task <id> --status CHECKING` → spawn **agent3-ticket-check**（帶 base_head）。PARTIAL 先補完，不直接驗收。
   - run-policy「票級 Codex 驗證」為「開」→ 每次票級檢查（單票、重驗、修復）prompt 末尾都加「Codex 驗證」🔧；「關」不加。欄位缺漏視同「開」，補寫該欄並在摘要告知（你不能問人）。
   - 派出去的角色不會隨你結束：它回報前你不得交回。被迫中斷時把在途角色與產出路徑記進 state（`decision`），回報明寫「有在途角色、結果未知」；下一棒先確認它已結束才動同一 worktree。
4. PASS → `P verify-receipt --task <id>`；任何內容不同就重派檢查。只 stage 票面許可範圍的實際異動（含新增／刪除，禁止 `add .`／`-A`），再核對 staged diff；使用 `git -C <cwd> commit`。若該工作項只驗證既有環境、changed_files 為空，可用 --allow-empty 保存檢查完成邊界。記住 commit SHA。
5. `P verify-commit --task <id> --commit <sha>` 必須成功；確認主工作區仍乾淨且 HEAD=base_head，再 `git merge --ff-only <sha>`。`P complete --task <id> --commit <sha>` 驗證 receipt／commit／主 HEAD 後才標 COMMITTED。state.md 進度檢視由腳本同步，不改 tickets.json 的產品內容。
6. 依 Git 政策掃描待推歷史、push。push 失敗／掃描命中用 push-state 設 PAUSED，暫停後續 push，繼續本機工作；掃描失敗不當成掃描通過。
7. 乾淨且已整合的 worktree 可 `git worktree remove <cwd>`，不加 force；失敗 worktree 保留，不整合、不刪除。取下一張 ready 票。

## 失敗與續跑

- FAIL：`P task-status ... --status FAILED`，`P attempt --key ticket:<id> --limit 2` 通過才重派 agent2 單票修復，先 `P start --task <id>` 消耗已登記的重試、更新 attempt，再沿用同 worktree（不可再 worktree add）。每次重驗使用新檔名與 receipt。
- ENV_BLOCKED／NEEDS_REQUIREMENT：保存同名狀態與原因，回 agent0 按政策處理；環境恢復前先 `attempt --key env:<id> --limit 2` 再 start，需求問題必須開新輪；沒有 INCONCLUSIVE 的隱含等待。
- 中斷在 worktree 建立前：state 有 cwd 但不存在，照原 base 建立，不分配新 task。
- 中斷在 commit 前：不相信舊回報，核对 receipt 指紋；不符重新檢查。
- 中斷在 commit 後、complete 前：先 verify-commit，再檢查是否已 fast-forward；未整合才 merge。complete 可重複執行，不重複 commit。
- 主 HEAD 已被別人移動／worktree 有 commit 後異動：不自動 reset／rebase／stash；回 ENV_BLOCKED。需要重新整合時，在新基準重建工作項並重新驗證。

## plan／docs 單 commit

只收呼叫方明確列出的文件。plan 可含 `.gitignore`、`.pipeline/plan/`、`.pipeline/output/*.html`、使用者已確認的 `.claude/settings.json`／`.mcp.json`；docs 只含 `.pipeline/output/`。變更含任何實作檔，改走上面的 agent2→票級檢查流程。

初次無 repo：git init；先建立 ignore（`.env`、`.env.*`，保留 `.env.example`，依賴／build／測試 runtime、`.pipeline/state.*`、rounds、worktrees、mcp-output、legacy、findings.md）。尚未追蹤的實作不夾入 plan commit；既有非流水線專案需先建立使用者確認的基準。

GitHub 授權只來自 git-policy；沒有授權只做本機 commit。repo 建立、remote、分支與公開範圍依已確認政策；不自行 force push 或擴大目的地。
