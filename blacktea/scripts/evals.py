#!/usr/bin/env python3
"""Escaped-bug eval set for the blacktea reviewers.

A case is an implementation finding (V) that passed ticket-level checks and was
only caught later by the audit. We rebuild the buggy commit in an isolated clone,
ask a reviewer agent to review the round's diff read-only, and score whether it
points at the known bug.

  evals.py harvest --project ~/gold [--project ~/ai-secretary]
  evals.py list
  evals.py run --label <engine-version> [--agent agent3-review] [--cases ID ...] [--limit N]
  evals.py report [--label L ...]

Cases and raw runs stay local (blacktea/evals/cases, runs: gitignored, may hold
project details). Only aggregate numbers go to blacktea/evals/scoreboard.md.
Scoring is deterministic: a hit is a finding in the same file within --window
lines of the recorded location. It is a proxy, not a judgment of the finding text.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1] / "evals"
CASES = ROOT / "cases"
RUNS = ROOT / "runs"
SCOREBOARD = ROOT / "scoreboard.md"
SOURCE = re.compile(r"\.(py|js|mjs|cjs|ts|tsx|jsx|vue|svelte|html|css|sh|go|rs|java|rb|php|sql)$")
ROW = re.compile(r"^\|\s*\**(V-\d+)\**\s*\|\s*([^|]*?)\s*\|\s*\**(Critical|High|Medium|Low)\**\s*\|\s*([^|]*)\|\s*([^|]*)\|")
LOCATION = re.compile(r"`([^`\s]+?):(\d+)")
CLOSED = re.compile(r"closed[^|]*?`([0-9a-f]{7,40})`")
SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"file": {"type": "string"}, "line": {"type": "integer"},
                       "severity": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]},
                       "summary": {"type": "string"}},
        "required": ["file", "line", "severity", "summary"]}}},
    "required": ["findings"],
}
READ_ONLY_TOOLS = ["Read", "Grep", "Glob", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)"]
BLOCKED_TOOLS = ["Agent", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch"]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True).stdout.strip()


def commits_by_finding(repo):
    found = {}
    for line in git(repo, "log", "--format=%H %s").splitlines():
        sha, subject = line.split(" ", 1)
        for ident in re.findall(r"V-\d+", subject):
            found[ident] = sha  # log is newest first, so the last write is the earliest fix
    return found


def resolve_path(repo, commit, path):
    files = git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
    if path in files:
        return path
    matches = [f for f in files if f.endswith("/" + path)]
    return matches[0] if len(matches) == 1 else None


def harvest(projects):
    CASES.mkdir(parents=True, exist_ok=True)
    added, skipped = 0, {}
    for project in projects:
        repo = Path(project).expanduser().resolve()
        rows, closed = {}, {}
        for report in sorted(repo.glob(".pipeline/rounds/*/04-verify-report.md")):
            for line in report.read_text(encoding="utf-8").splitlines():
                m = ROW.match(line)
                if not m:
                    continue
                ident, category, severity, location, rest = m.groups()
                if "closed" in location + rest:
                    sha = CLOSED.search(line)
                    if sha:
                        closed.setdefault(ident, sha[1])
                rows.setdefault(ident, (category, severity, location, rest, report.parent.name))
        by_message = commits_by_finding(repo)
        for ident, (category, severity, location, rest, round_name) in rows.items():
            def skip(reason):
                skipped[reason] = skipped.get(reason, 0) + 1
            if "實作" not in category or severity == "Low" or "需求" in category:
                skip("not an implementation finding (High/Medium)"); continue
            loc = LOCATION.search(location)
            if not loc or not SOURCE.search(loc[1]) or loc[1].startswith(".pipeline"):
                skip("no source file:line"); continue
            fix = by_message.get(ident) or closed.get(ident)
            if not fix:
                skip("no fix commit"); continue
            try:
                fix = git(repo, "rev-parse", "--verify", fix + "^{commit}")
                buggy = git(repo, "rev-parse", fix + "^")
                base = git(repo, "log", "-1", "--format=%H", "--grep=^plan", buggy)
            except subprocess.CalledProcessError:
                skip("commit not found"); continue
            path = resolve_path(repo, buggy, loc[1])
            if not base or not path:
                skip("file or base missing at buggy commit"); continue
            changed = git(repo, "diff", "--name-only", base, buggy).splitlines()
            case = {"id": f"{repo.name}-{ident}", "project": str(repo), "finding": ident, "round": round_name,
                    "severity": severity, "file": path, "line": int(loc[2]),
                    "summary": re.sub(r"\s+", " ", rest.strip())[:400],
                    "base": base, "buggy": buggy, "fix": fix,
                    "origin": "introduced" if path in changed else "pre-existing"}
            (CASES / (case["id"] + ".json")).write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n")
            added += 1
    return {"cases": added, "skipped": skipped, "dir": str(CASES)}


def load_cases(ids=None, include_pre_existing=False):
    cases = [json.loads(p.read_text()) for p in sorted(CASES.glob("*.json"))]
    if ids:
        cases = [c for c in cases if c["id"] in ids]
    elif not include_pre_existing:
        cases = [c for c in cases if c["origin"] == "introduced"]
    return cases


PROMPT = """評測模式（evals.py）：這是唯讀的程式審查評測，不是流水線派工。總指揮平常會給的欄位如下，已全部提供：
- cwd：目前目錄（受測版本的隔離副本）
- 範圍：incremental，baseline `{base}`，head `{buggy}`（用 `git diff {base}..{buggy}` 看改動）
- 規格：本副本的 `.pipeline/plan/01-requirements.md`（存在才讀，只讀相關章節）
- 可用能力：只能讀檔、搜尋與唯讀 git；不能執行測試、啟動服務或寫檔。round_dir 與報告不用寫。
任務：審查這段改動與它影響的呼叫端，列出你能以讀碼確認的實作 bug（正確性、邊界、錯誤處理、資安）。每項給檔案路徑（相對 repo 根目錄）、行號（head 版本）、嚴重度與一句摘要。沒有就回空清單。只用結構化輸出回答。"""


def run_case(case, agent, model, budget, timeout, keep):
    work = Path(tempfile.mkdtemp(prefix="blacktea-eval-"))
    repo = work / "repo"
    try:
        subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", case["project"], str(repo)], check=True)
        git(repo, "checkout", "-q", case["buggy"])
        command = ["claude", "-p", PROMPT.format(**case), "--agent", agent, "--output-format", "json",
                   "--json-schema", json.dumps(SCHEMA), "--permission-mode", "dontAsk",
                   "--allowedTools", *READ_ONLY_TOOLS, "--disallowedTools", *BLOCKED_TOOLS,
                   "--no-session-persistence", "--max-budget-usd", str(budget)]
        if model:
            command += ["--model", model]
        started = datetime.now(timezone.utc)
        try:
            proc = subprocess.run(command, cwd=repo, stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, timeout=timeout)
            raw, status = proc.stdout, ("ok" if proc.returncode == 0 else f"exit {proc.returncode}")
        except subprocess.TimeoutExpired:
            raw, status = "", "timeout"
        seconds = (datetime.now(timezone.utc) - started).total_seconds()
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
    findings, cost = None, None
    try:
        data = json.loads(raw)
        cost = data.get("total_cost_usd")
        structured = data.get("structured_output")
        if structured is None and isinstance(data.get("result"), str):
            structured = json.loads(data["result"])
        findings = structured["findings"]
    except (ValueError, TypeError, KeyError):
        status = status if status != "ok" else "unparsed output"
    return {"case": case["id"], "status": status, "findings": findings, "cost_usd": cost,
            "seconds": round(seconds), "raw_tail": raw[-2000:] if findings is None else ""}


def score(case, result, window):
    findings = result["findings"] or []
    same_file = [f for f in findings if f["file"].lstrip("./").endswith(case["file"]) or case["file"].endswith(f["file"].lstrip("./"))]
    hit = any(abs(int(f["line"]) - case["line"]) <= window for f in same_file)
    return {"hit": hit, "file_hit": bool(same_file), "finding_count": len(findings)}


def run(args):
    cases = load_cases(args.cases, args.include_pre_existing)
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        sys.exit("no cases; run harvest first")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,60}", args.label):
        sys.exit("label must be letters, digits, . _ -")
    out = RUNS / args.label
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for n, case in enumerate(cases, 1):
        result = run_case(case, args.agent, args.model, args.budget_usd, args.timeout, args.keep)
        result.update(score(case, result, args.window) if result["findings"] is not None else {"hit": False, "file_hit": False, "finding_count": 0})
        result.update(agent=args.agent, model=args.model or "agent default", window=args.window)
        (out / (case["id"] + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        results.append(result)
        print(f"[{n}/{len(cases)}] {case['id']}: {result['status']} hit={result['hit']} findings={result['finding_count']} cost={result['cost_usd']}", flush=True)
    summary = summarize(args.label, results)
    if not args.no_scoreboard:
        append_scoreboard(summary)
    return summary


def summarize(label, results):
    done = [r for r in results if r["findings"] is not None]
    costs = [r["cost_usd"] for r in results if r["cost_usd"] is not None]
    agents = sorted({r.get("agent", "?") for r in results})
    return {"label": label, "agent": ",".join(agents), "cases": len(results), "completed": len(done),
            "hits": sum(r["hit"] for r in done), "file_hits": sum(r["file_hit"] for r in done),
            "hit_rate": round(sum(r["hit"] for r in done) / len(results), 3) if results else 0,
            "mean_findings": round(sum(r["finding_count"] for r in done) / len(done), 2) if done else 0,
            "cost_usd": round(sum(costs), 2)}


def append_scoreboard(s):
    if not SCOREBOARD.exists():
        SCOREBOARD.write_text("# 評測計分表\n\n只記彙總數字；案例與原始輸出留在本機（cases/、runs/ 不入版控）。\n"
                              "命中＝同檔案且行號在容許範圍內。改引擎後重跑，命中率不得低於上一版。\n\n"
                              "| 日期 | 標籤 | 角色 | 案例 | 完成 | 命中 | 同檔 | 命中率 | 平均發現數 | 花費 USD |\n"
                              "|---|---|---|---|---|---|---|---|---|---|\n")
    with SCOREBOARD.open("a") as f:
        f.write(f"| {datetime.now().date()} | {s['label']} | {s['agent']} | {s['cases']} | {s['completed']} | {s['hits']} | "
                f"{s['file_hits']} | {s['hit_rate']:.1%} | {s['mean_findings']} | {s['cost_usd']} |\n")


def report(labels):
    labels = labels or sorted(p.name for p in RUNS.glob("*") if p.is_dir())
    return [summarize(label, [json.loads(p.read_text()) for p in sorted((RUNS / label).glob("*.json"))])
            for label in labels if (RUNS / label).is_dir()]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    h = sub.add_parser("harvest"); h.add_argument("--project", action="append", required=True)
    ls = sub.add_parser("list"); ls.add_argument("--include-pre-existing", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--label", required=True, help="engine version, e.g. git short SHA of ~/.claude")
    r.add_argument("--agent", default="agent3-review")
    r.add_argument("--model")
    r.add_argument("--cases", nargs="*")
    r.add_argument("--limit", type=int)
    r.add_argument("--include-pre-existing", action="store_true")
    r.add_argument("--budget-usd", type=float, default=2.0)
    r.add_argument("--timeout", type=int, default=900)
    r.add_argument("--window", type=int, default=30)
    r.add_argument("--keep", action="store_true", help="keep the clone for debugging")
    r.add_argument("--no-scoreboard", action="store_true")
    rp = sub.add_parser("report"); rp.add_argument("--label", action="append")
    args = p.parse_args()
    if args.command == "harvest":
        result = harvest(args.project)
    elif args.command == "list":
        result = [{k: c[k] for k in ("id", "severity", "file", "line", "origin", "round")}
                  for c in load_cases(include_pre_existing=args.include_pre_existing)]
    elif args.command == "run":
        result = run(args)
    else:
        result = report(args.label)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
