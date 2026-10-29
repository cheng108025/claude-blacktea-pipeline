#!/usr/bin/env python3
"""Local blacktea state, plan, and verification helpers. No network or Git writes."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    require(result.returncode == 0, "Git operation failed: " + " ".join(args[:2]))
    return result.stdout


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text())


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".blacktea-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def dump(path, data):
    atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def plan(root):
    data = read_json(root / ".pipeline/plan/tickets.json")
    require(data.get("status") in {"DRAFT", "FINAL"}, "plan status must be DRAFT or FINAL")
    require(isinstance(data.get("tickets"), list), "tickets must be a list")
    tickets = {}
    replaced = {}
    for ticket in data["tickets"]:
        ident = ticket.get("id", "")
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", ident), "invalid ticket id")
        require(ident not in tickets, "duplicate ticket id: " + ident)
        for key in ("title", "feature", "description", "approach"):
            require(isinstance(ticket.get(key), str) and ticket[key].strip(), ident + ": missing " + key)
        for key in ("files", "depends_on", "dod", "verify", "supersedes"):
            value = ticket.get(key)
            require(isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value), ident + ": invalid " + key)
            require(len(value) == len(set(value)), ident + ": duplicates in " + key)
        require(ticket["dod"] and ticket["verify"], ident + ": empty acceptance or verification")
        for name in ticket["files"]:
            p = PurePosixPath(name)
            require(not p.is_absolute() and ".." not in p.parts and p.parts and
                    p.parts[0] not in {".git", ".pipeline"} and
                    not any(c in name for c in "*?[]\\\n\r"), ident + ": unsafe or non-concrete file path")
        require(isinstance(ticket.get("group", ""), str), ident + ": invalid group")
        tickets[ident] = ticket
        for old in ticket["supersedes"]:
            require(old not in replaced, "multiple replacements for " + old)
            require(old != ident, "self replacement: " + ident)
            replaced[old] = ident
    require(isinstance(data.get("project", ""), str) and isinstance(data.get("self_audit", ""), str), "invalid project/self_audit")
    for key, fields in (("preamble", ("heading", "body")), ("groups", ("name",))):
        items = data.get(key, [])
        require(isinstance(items, list) and all(isinstance(x, dict) and all(isinstance(x.get(f), str) and x[f].strip() for f in fields)
                                                and isinstance(x.get("how", ""), str) for x in items), "invalid " + key)
    names = [g["name"] for g in data.get("groups", [])]
    require(len(names) == len(set(names)), "duplicate group name")
    for ticket in tickets.values():
        require(not ticket.get("group") or ticket["group"] in names, ticket["id"] + ": unknown group")
    for ticket in tickets.values():
        for other in ticket["depends_on"] + ticket["supersedes"]:
            require(other in tickets, "unknown dependency/replacement: " + other)

    def resolve(ident):
        seen = set()
        while ident in replaced:
            require(ident not in seen, "replacement cycle")
            seen.add(ident)
            ident = replaced[ident]
        return ident

    visited, active = set(), set()

    def visit(ident):
        ident = resolve(ident)
        require(ident not in active, "dependency cycle involving " + ident)
        if ident in visited:
            return
        active.add(ident)
        for other in tickets[ident]["depends_on"]:
            visit(other)
        active.remove(ident)
        visited.add(ident)

    for ident in tickets:
        visit(ident)
    return data, tickets, {ident: resolve(ident) for ident in tickets}


def task_hash(ticket):
    return hashlib.sha256(json.dumps(ticket, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def revision(root):
    return hashlib.sha256((root / ".pipeline/plan/01-requirements.md").read_bytes()).hexdigest()


def require_final_spec(root):
    text = (root / ".pipeline/plan/01-requirements.md").read_text()
    require(re.search(r"(?m)^(?:>\s*狀態\s*[:：]\s*)?FINAL\s*$", text) and
            not re.search(r"(?m)^(?:>\s*狀態\s*[:：]\s*)?DRAFT\s*$", text), "requirements must explicitly be FINAL")


def source_path(name):
    return not (name == ".pipeline" or name.startswith(".pipeline/"))


def work_files(cwd):
    names = set(git(cwd, "ls-files", "-z", "--cached", "--others", "--exclude-standard").decode().split("\0"))
    entries = []
    for name in sorted(filter(None, names)):
        if not source_path(name):
            continue
        p = cwd / name
        if p.is_symlink():
            mode, content = "120000", os.readlink(p).encode()
        elif p.is_file():
            mode = "100755" if p.stat().st_mode & 0o111 else "100644"
            content = p.read_bytes()
        elif p.exists():
            raise Invalid("submodule/directory entry not supported: " + name)
        else:
            continue  # tracked deletion: absent from the candidate tree
        entries.append((name, mode, content))
    return entries


def committed_files(cwd, commit):
    entries = []
    for record in git(cwd, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = path.decode()
        if source_path(name):
            require(kind == "blob", "submodules are not supported for receipts")
            entries.append((name, mode, git(cwd, "cat-file", "blob", oid)))
    return entries


def digest(entries):
    result = hashlib.sha256()
    for name, mode, content in sorted(entries):
        result.update(json.dumps([name, mode, hashlib.sha256(content).hexdigest()], ensure_ascii=False).encode() + b"\n")
    return result.hexdigest()


def dirty(cwd):
    return bool(git(cwd, "status", "--porcelain", "--untracked-files=all").strip())


def changed_files(cwd, base, commit=None):
    if commit:
        raw = git(cwd, "diff", "--name-only", "-z", base, commit)
    else:
        raw = git(cwd, "diff", "--name-only", "-z", base) + git(cwd, "ls-files", "--others", "--exclude-standard", "-z")
    return set(filter(None, raw.decode().split("\0")))


class Engine:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.directory = self.root / ".pipeline"
        self.path = self.directory / "state.json"
        self.state = None

    @contextlib.contextmanager
    def locked(self, init=False):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "state.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.path.exists():
                self.state = read_json(self.path)
                require(self.state.get("schema_version") == 2, "unsupported state schema")
            else:
                require(init, "state missing; run init (legacy requires explicit import)")
            yield

    def save(self):
        self.state["updated_at"] = now()
        dump(self.path, self.state)
        run = self.state["runs"].get(self.state["current_run"], {})
        lines = ["# Pipeline State（由 state.json 產生，勿手改）", "",
                 "- run: " + str(self.state["current_run"]),
                 "- phase: " + run.get("phase", "plan"),
                 "- status: " + run.get("status", "PLANNING"),
                 "- round_dir: " + run.get("round_dir", ""), "", "## 工作項", ""]
        for ident, task in self.state["tickets"].items():
            lines.append("- " + ident + ": " + task["status"] + " " + task.get("commit", ""))
        lines += ["", "## 決策", ""]
        for decision in self.state["decisions"]:
            lines.append("- " + decision["reason"])
        lines += ["", "## 待裁決", ""]
        for ident, question in self.state.get("questions", {}).items():
            if question["status"] == "OPEN":
                lines.append("- " + ident + ": " + question["prompt"])
        lines += ["", "- push: " + self.state.get("push", {}).get("status", "READY")]
        atomic(self.directory / "state.md", "\n".join(lines) + "\n")

    def current(self):
        require(self.state["current_run"] in self.state["runs"], "no current run")
        return self.state["runs"][self.state["current_run"]]

    def task(self, ident):
        require(ident in self.state["tickets"], "unknown task: " + ident)
        task = self.state["tickets"][ident]
        require(task.get("run_id") == self.state["current_run"], "task belongs to a different run")
        return task

    def assert_plan(self, ident=None):
        data, tickets, resolved = plan(self.root)
        require(data["status"] == "FINAL", "plan is not FINAL")
        require_final_spec(self.root)
        require(revision(self.root) == self.current()["spec_revision"], "spec changed; start a new run")
        if ident:
            require(task_hash(tickets[ident]) == self.task(ident)["ticket_hash"], "ticket changed since task start")
        return tickets, resolved

    def initialize(self, legacy=None):
        if self.state:
            return {"status": "already initialized"}
        require(not (self.directory / "state.md").exists() or legacy, "legacy state.md exists; review and import first")
        self.state = {"schema_version": 2, "current_run": None, "runs": {}, "tickets": {},
                      "next_ids": {k: 1 for k in "VEUQ"}, "decisions": [],
                      "questions": {}, "push": {"status": "READY", "reason": ""},
                      "external_reviews": {}, "incremental_since_full": 0}
        if legacy:
            data = read_json(legacy)
            for ident, task in data.get("tickets", {}).items():
                require(task["status"] == "COMMITTED", "only verified committed legacy tasks can be imported")
                task["commit"] = git(self.root, "rev-parse", "--verify", task["commit"] + "^{commit}").decode().strip()
                self.state["tickets"][ident] = task
            for kind, number in data.get("next_ids", {}).items():
                require(kind in "VEUQ" and isinstance(number, int) and number >= 1, "invalid ID high-water mark")
                self.state["next_ids"][kind] = number
        self.save()
        return {"status": "initialized"}

    def new_run(self, mode, tasks, label=None):
        data, tickets, _ = plan(self.root)
        require(data["status"] == "FINAL", "plan is not FINAL")
        require_final_spec(self.root)
        require(not dirty(self.root), "main worktree must be clean")
        require((tasks or mode != "build") and len(tasks) == len(set(tasks)) and all(t in tickets for t in tasks), "invalid run task list")
        require(all(t.get("status") not in {"BUILDING", "CHECKING", "VERIFIED"} for t in self.state["tickets"].values()), "finish or explicitly block active tasks first")
        if self.state["current_run"]:
            old = self.current()
            require(old["status"] in {"COMPLETED", "INCOMPLETE", "NEEDS_USER"}, "current run still active")
        if label:
            require(re.fullmatch(r"T-Rev[0-9]+[a-z]?", label), "invalid run label")
        numbers = [int(k.split("-", 1)[0]) for k in self.state["runs"]]
        for p in (self.directory / "rounds").glob("*"):
            if re.match(r"^\d+", p.name):
                numbers.append(int(re.match(r"^\d+", p.name)[0]))
        ident = f"{max(numbers, default=0) + 1:02}" + ("-" + label if label else "")
        round_dir = self.directory / "rounds" / ident
        for name in ("build-log", "ticket-checks", "evidence", "scratch"):
            (round_dir / name).mkdir(parents=True)
        run = {"mode": mode, "phase": "build", "status": "RUNNING", "round_dir": str(round_dir),
               "spec_revision": revision(self.root), "base_head": git(self.root, "rev-parse", "HEAD").decode().strip(),
               "tasks": tasks, "attempts": {}, "checks": {}, "reason": ""}
        self.state["runs"][ident] = run
        self.state["current_run"] = ident
        for task_id in tasks:
            old = self.state["tickets"].get(task_id)
            if old:
                dump(round_dir / ("previous-" + task_id + ".json"), old)
            self.state["tickets"][task_id] = {"status": "PENDING", "run_id": ident, "attempt": 0}
        self.save()
        return {"run_id": ident, **run}

    def ready(self):
        tickets, resolved = self.assert_plan()
        ready, blocked = [], {}
        for ident in self.current()["tasks"]:
            task = self.state["tickets"][ident]
            if resolved[ident] != ident or task["status"] != "PENDING":
                continue
            missing = [resolved[d] for d in tickets[ident]["depends_on"]
                       if self.state["tickets"].get(resolved[d], {}).get("status") != "COMMITTED"]
            if missing:
                blocked[ident] = missing
            else:
                ready.append(ident)
        return {"ready": ready, "blocked": blocked}

    def start(self, ident):
        tickets, _ = self.assert_plan()
        task = self.task(ident)
        require(not any(t["status"] in {"BUILDING", "CHECKING", "VERIFIED"} for t in self.state["tickets"].values()), "another task is active")
        require(task["status"] in {"PENDING", "FAILED", "ENV_BLOCKED"}, "task cannot start; requirements need a new run")
        require(not dirty(self.root), "main worktree must be clean")
        if task["status"] == "PENDING":
            require(ident in self.ready()["ready"], "dependencies not committed")
        else:
            key = ("ticket:" if task["status"] == "FAILED" else "env:") + ident
            count = self.current()["attempts"].get(key, {}).get("count", 0)
            used = task.setdefault("retry_used", {}).get(key, 0)
            require(count > used, "consume the retry budget before restarting: " + key)
            task["retry_used"][key] = count
        if "cwd" not in task:
            task["base_head"] = git(self.root, "rev-parse", "HEAD").decode().strip()
            task["cwd"] = str(self.directory / "worktrees" / (self.state["current_run"] + "-" + ident))
            task["branch"] = "blacktea/" + self.state["current_run"] + "/" + ident
        task["status"] = "BUILDING"
        task["attempt"] += 1
        task["ticket_hash"] = task_hash(tickets[ident])
        task.pop("receipt", None)
        self.save()
        return task

    def receipt(self, ident, cwd, evidence):
        tickets, _ = self.assert_plan(ident)
        task = self.task(ident)
        cwd, evidence = Path(cwd).resolve(), Path(evidence).resolve()
        require(task["status"] == "CHECKING", "task is not CHECKING")
        require(str(cwd) == task["cwd"], "wrong worktree")
        require(evidence.is_file() and evidence.is_relative_to(Path(self.current()["round_dir"])), "evidence must exist in this round")
        require(git(cwd, "rev-parse", "HEAD").decode().strip() == task["base_head"], "unexpected worktree HEAD")
        changed = changed_files(cwd, task["base_head"])
        require(changed <= set(tickets[ident]["files"]), "out-of-scope changes: " + str(sorted(changed - set(tickets[ident]["files"]))))
        receipt = {"task_id": ident, "run_id": self.state["current_run"], "attempt": task["attempt"],
                   "spec_revision": self.current()["spec_revision"], "base_head": task["base_head"],
                   "ticket_hash": task["ticket_hash"], "fingerprint": digest(work_files(cwd)),
                   "changed_files": sorted(changed), "evidence": str(evidence), "created_at": now()}
        path = Path(self.current()["round_dir"]) / "ticket-checks" / f"{ident}-{task['attempt']}.receipt.json"
        require(not path.exists(), "receipt already exists; do not overwrite")
        dump(path, receipt)
        task["receipt"], task["status"] = str(path), "VERIFIED"
        self.save()
        return {"receipt": str(path), **receipt}

    def verify(self, ident, commit=None):
        tickets, _ = self.assert_plan(ident)
        task = self.task(ident)
        require(task["status"] in {"VERIFIED", "COMMITTED"}, "task has no valid verification")
        receipt = read_json(task["receipt"])
        require(receipt["task_id"] == ident and receipt["run_id"] == self.state["current_run"] and
                receipt["attempt"] == task["attempt"] and receipt["ticket_hash"] == task["ticket_hash"] and
                receipt["spec_revision"] == self.current()["spec_revision"], "stale receipt")
        cwd = Path(task["cwd"])
        if commit:
            commit = git(self.root, "rev-parse", "--verify", commit + "^{commit}").decode().strip()
            parents = git(self.root, "rev-list", "--parents", "-n", "1", commit).decode().split()
            require(parents == [commit, task["base_head"]], "candidate must be one commit on the checked baseline")
            changed = changed_files(self.root, task["base_head"], commit)
            require(changed <= set(tickets[ident]["files"]), "commit includes out-of-scope paths")
            actual = digest(committed_files(self.root, commit))
        else:
            require(git(cwd, "rev-parse", "HEAD").decode().strip() == task["base_head"], "use verify-commit after commit")
            actual = digest(work_files(cwd))
        require(actual == receipt["fingerprint"], "content changed since independent verification")
        return {"verified": True, "fingerprint": actual, "commit": commit}

    def complete(self, ident, commit):
        verified = self.verify(ident, commit)
        task = self.task(ident)
        if task["status"] == "COMMITTED":
            require(task["commit"] == verified["commit"], "different already-recorded commit")
            return {"status": "already completed"}
        require(not dirty(self.root), "main worktree must be clean after integration")
        require(git(self.root, "rev-parse", "HEAD").decode().strip() == verified["commit"], "commit must be integrated before completion")
        require(not dirty(Path(task["cwd"])), "ticket worktree changed after commit")
        task["status"], task["commit"] = "COMMITTED", verified["commit"]
        self.save()
        return task


def one_line(text):
    return " ".join(str(text).split())


def cell(text, limit=None):
    text = one_line(text)
    if limit and len(text) > limit:
        text = text[:limit] + "…"
    return text.replace("|", "\\|")


def ticket_lines(t):
    numbered = lambda items: " ".join(f"({i}) {one_line(x)}" for i, x in enumerate(items, 1))
    lines = ["- [ ] **" + t["id"] + " " + one_line(t["title"]) + "**",
             "  - 所屬功能: " + one_line(t["feature"]),
             "  - 內容: " + one_line(t["description"]),
             "  - 做法: " + one_line(t["approach"]),
             "  - 異動檔案: " + "、".join("`" + f + "`" for f in t["files"]),
             "  - 依賴: " + ("、".join(t["depends_on"]) or "無")]
    if t["supersedes"]:
        lines.append("  - 取代: " + "、".join(t["supersedes"]))
    lines += ["  - 完成條件(DoD): " + numbered(t["dod"]),
              "  - 驗證方式: " + "；".join(one_line(x) for x in t["verify"]), ""]
    return lines


def workplan_markdown(data, tickets, revision_id):
    project = one_line(data.get("project", ""))
    lines = ["# " + (project + " " if project else "") + "工作單", "",
             "> 狀態：" + data["status"], "> 規格版本: " + revision_id[:12],
             "> 由 tickets.json 產生，勿手改；進度見 .pipeline/state.md。", ""]
    for section in data.get("preamble", []):
        lines += ["## " + one_line(section["heading"]), "", section["body"].strip(), ""]
    groups = data.get("groups", [])
    placed = set()
    for group in groups:
        members = [t for t in tickets.values() if t.get("group") == group["name"]]
        lines += ["## " + one_line(group["name"]), ""]
        if group.get("how", "").strip():
            lines += ["### 這一群怎麼做", "", group["how"].strip(), ""]
        for t in members:
            lines += ticket_lines(t)
            placed.add(t["id"])
    rest = [t for t in tickets.values() if t["id"] not in placed]
    if rest:
        lines += ["## " + ("其他工作項" if groups else "工作項"), ""]
        for t in rest:
            lines += ticket_lines(t)
    lines += ["## 總表", "", "| 票 | 所屬功能 | 內容 | 做法摘要 | 依賴 | 完成條件摘要 | 驗證方式 |",
              "|---|---|---|---|---|---|---|"]
    for t in tickets.values():
        lines.append("| " + " | ".join([t["id"], cell(t["feature"]), cell(t["title"]), cell(t["approach"], 60),
                                         "、".join(t["depends_on"]) or "無", cell("；".join(t["dod"]), 60),
                                         cell("；".join(t["verify"]), 60)]) + " |")
    lines.append("")
    if data.get("self_audit", "").strip():
        lines += ["## 自我稽核結果", "", data["self_audit"].strip(), ""]
    lines += ["全域驗收清單以 `01-requirements.md` 的「全域驗收清單」章為唯一來源。", ""]
    return "\n".join(lines)


def md2html(kind, source, output, project):
    command = ["uv", "run", "--quiet", str(Path(__file__).with_name("md2html.py")), "--kind", kind,
               str(source), str(output), "--project", project]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    require(result.returncode == 0, "md2html failed for " + kind + ": " + result.stderr.strip()[-500:])
    return result.stdout.strip()


def render(root, project=None, kind="all"):
    plan_dir, out_dir = root / ".pipeline/plan", root / ".pipeline/output"
    rendered = []
    data = tickets = None
    if kind in {"all", "workplan"}:
        data, tickets, _ = plan(root)
    project = project or (data or {}).get("project") or root.name
    project = re.sub(r"\s+", "_", one_line(project))
    require(re.fullmatch(r"[^/\\\0]{1,100}", project), "invalid project name")
    out_dir.mkdir(parents=True, exist_ok=True)
    if kind in {"all", "requirements"}:
        rendered.append(md2html("requirements", plan_dir / "01-requirements.md",
                                out_dir / (project + "_requirements.html"), project))
    if kind in {"all", "workplan"}:
        atomic(plan_dir / "02-workplan.md", workplan_markdown(data, tickets, revision(root)))
        rendered.append(md2html("workplan", plan_dir / "02-workplan.md",
                                out_dir / (project + "_workplan.html"), project))
    return {"rendered": rendered}


def snapshot(cwd, output):
    cwd, output = Path(cwd).resolve(), Path(output).resolve()
    require(not output.exists(), "snapshot destination must not exist")
    entries = work_files(cwd)
    for name, mode, _ in entries:
        require(mode != "120000", "snapshot refuses symlinks: " + name)
        require(not any(part == ".env" or part.startswith(".env.") and part != ".env.example" or
                        part.lower() in {"credentials.json", ".credentials.json", "id_rsa", "id_ed25519"} or
                        part.lower().endswith((".pem", ".key")) for part in PurePosixPath(name).parts), "snapshot contains a sensitive path")
    output.mkdir(parents=True)
    for name, mode, content in entries:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o755 if mode == "100755" else 0o644)
    return {"cwd": str(output), "fingerprint": digest(entries)}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-plan")
    sp = sub.add_parser("render-plan"); sp.add_argument("--project"); sp.add_argument("--only", choices=["all", "requirements", "workplan"], default="all")
    sub.add_parser("status")
    sub.add_parser("ready")
    init = sub.add_parser("init"); init.add_argument("--legacy-import")
    new = sub.add_parser("new-run"); new.add_argument("--mode", choices=["build", "change", "amend"], required=True); new.add_argument("--tasks", nargs="*", default=[]); new.add_argument("--label")
    for cmd in ("start", "add-task", "verify-receipt"):
        sub.add_parser(cmd).add_argument("--task", required=True)
    for cmd in ("verify-commit", "complete"):
        sp = sub.add_parser(cmd); sp.add_argument("--task", required=True); sp.add_argument("--commit", required=True)
    sp = sub.add_parser("task-status"); sp.add_argument("--task", required=True); sp.add_argument("--status", choices=["CHECKING", "FAILED", "ENV_BLOCKED", "NEEDS_REQUIREMENT"], required=True); sp.add_argument("--reason", default="")
    sp = sub.add_parser("receipt"); sp.add_argument("--task", required=True); sp.add_argument("--cwd", type=Path, required=True); sp.add_argument("--evidence", type=Path, required=True)
    sp = sub.add_parser("snapshot"); sp.add_argument("--cwd", type=Path, required=True); sp.add_argument("--output", type=Path, required=True)
    sp = sub.add_parser("allocate"); sp.add_argument("--kind", choices=list("VEUQ"), required=True); sp.add_argument("--count", type=int, default=1)
    sp = sub.add_parser("attempt"); sp.add_argument("--key", required=True); sp.add_argument("--limit", type=int, required=True)
    sp = sub.add_parser("decision"); sp.add_argument("--reason", required=True)
    sp = sub.add_parser("question"); sp.add_argument("--source", required=True); sp.add_argument("--prompt", required=True); sp.add_argument("--options", nargs="+", required=True)
    sp = sub.add_parser("resolve"); sp.add_argument("--id", required=True); sp.add_argument("--answer", required=True)
    sp = sub.add_parser("push-state"); sp.add_argument("--status", choices=["READY", "PAUSED"], required=True); sp.add_argument("--reason", required=True)
    sp = sub.add_parser("external-review"); sp.add_argument("--kind", choices=["plan", "code"], required=True)
    sp = sub.add_parser("phase"); sp.add_argument("--name", choices=["build", "audit", "e2e", "report"], required=True); sp.add_argument("--status", choices=["RUNNING", "NEEDS_USER", "COMPLETED", "INCOMPLETE"], required=True); sp.add_argument("--reason", default="")
    sp = sub.add_parser("record-check"); sp.add_argument("--stage", choices=["audit", "e2e"], required=True); sp.add_argument("--result", choices=["PASS", "FAIL", "ENV_BLOCKED", "NEEDS_REQUIREMENT", "SKIPPED", "N/A"], required=True); sp.add_argument("--evidence", required=True); sp.add_argument("--reason", default="")
    sp = sub.add_parser("record-e2e"); sp.add_argument("--scope", choices=["full", "incremental"], required=True); sp.add_argument("--result", choices=["PASS", "FAIL", "ENV_BLOCKED"], required=True)
    return p


def execute(a):
    root = a.root.resolve()
    if a.command == "validate-plan":
        data, tickets, _ = plan(root)
        return {"valid": True, "tickets": len(tickets), "status": data["status"]}
    if a.command == "render-plan":
        return render(root, a.project, a.only)
    if a.command == "snapshot":
        return snapshot(a.cwd, a.output)
    engine = Engine(root)
    with engine.locked(init=a.command == "init"):
        if a.command == "init": return engine.initialize(a.legacy_import)
        if a.command == "new-run": return engine.new_run(a.mode, a.tasks, a.label)
        if a.command == "status":
            engine.save()  # repair state.md if interrupted after atomic JSON write
            return engine.state
        if a.command == "ready": return engine.ready()
        if a.command == "start": return engine.start(a.task)
        if a.command == "receipt": return engine.receipt(a.task, a.cwd, a.evidence)
        if a.command == "verify-receipt": return engine.verify(a.task)
        if a.command == "verify-commit": return engine.verify(a.task, a.commit)
        if a.command == "complete": return engine.complete(a.task, a.commit)
        if a.command == "allocate":
            require(1 <= a.count <= 1000, "invalid allocation count")
            first = engine.state["next_ids"][a.kind]
            engine.state["next_ids"][a.kind] += a.count
            result = {"ids": [f"{a.kind}-{n:03}" for n in range(first, first + a.count)]}
        elif a.command == "attempt":
            attempts = engine.current()["attempts"]
            ceiling = 2 if a.key.startswith(("ticket:", "env:")) or a.key == "e2e" else 3 if a.key == "audit" else 0
            require(ceiling and 0 < a.limit <= ceiling, "unknown retry key or excessive limit")
            previous = attempts.get(a.key, {"count": 0, "limit": a.limit})
            require(a.limit > 0 and previous["limit"] == a.limit, "retry limit cannot change within a run")
            require(previous["count"] < a.limit, "retry budget exhausted: " + a.key)
            attempts[a.key] = {"count": previous["count"] + 1, "limit": a.limit}
            result = attempts[a.key]
        elif a.command == "decision":
            result = {"time": now(), "run_id": engine.state["current_run"], "reason": a.reason}
            engine.state["decisions"].append(result)
        elif a.command == "question":
            require(2 <= len(a.options) <= 4, "questions need 2-4 options")
            number = engine.state["next_ids"]["Q"]
            engine.state["next_ids"]["Q"] += 1
            ident = f"Q-{number:03}"
            result = {"id": ident, "source": a.source, "prompt": a.prompt, "options": a.options,
                      "status": "OPEN", "run_id": engine.state["current_run"], "created_at": now()}
            engine.state["questions"][ident] = result
        elif a.command == "resolve":
            require(a.id in engine.state["questions"], "unknown question")
            result = engine.state["questions"][a.id]
            require(result["status"] == "OPEN", "question already resolved")
            result.update(status="RESOLVED", answer=a.answer, resolved_at=now())
            engine.state["decisions"].append({"time": now(), "run_id": engine.state["current_run"], "reason": a.id + ": " + a.answer})
        elif a.command == "push-state":
            result = engine.state["push"] = {"status": a.status, "reason": a.reason, "updated_at": now()}
        elif a.command == "external-review":
            require(a.kind not in engine.state["external_reviews"], "external review slot already consumed")
            result = engine.state["external_reviews"][a.kind] = {"attempted_at": now()}
        elif a.command == "add-task":
            tickets, _ = engine.assert_plan()
            require(a.task in tickets and a.task not in engine.current()["tasks"], "unknown or duplicate run task")
            require(a.task.startswith("fix-"), "only repair tasks can be added without a new run")
            engine.current()["tasks"].append(a.task)
            result = engine.state["tickets"][a.task] = {"status": "PENDING", "run_id": engine.state["current_run"], "attempt": 0}
        elif a.command == "task-status":
            task = engine.task(a.task)
            require(task["status"] in {"BUILDING", "CHECKING", "VERIFIED"}, "illegal task transition")
            require(a.status != "CHECKING" or task["status"] == "BUILDING", "only completed build may enter CHECKING")
            task["status"], task["reason"] = a.status, a.reason
            if a.status != "CHECKING": task.pop("receipt", None)
            result = task
        elif a.command == "record-check":
            evidence = Path(a.evidence).resolve()
            require(evidence.is_file() and evidence.is_relative_to(Path(engine.current()["round_dir"])), "missing current-run evidence")
            require(not dirty(root), "checks must refer to a clean integrated worktree")
            engine.assert_plan()
            if a.result == "N/A":
                require(a.stage == "e2e" and a.reason.strip() and not engine.current()["tasks"], "N/A only for documented spec-only changes with no implementation tasks")
            result = engine.current()["checks"][a.stage] = {"result": a.result, "reason": a.reason, "evidence": str(evidence), "head": git(root, "rev-parse", "HEAD").decode().strip(), "fingerprint": digest(work_files(root)), "spec_revision": revision(root)}
        elif a.command == "record-e2e":
            result = {"scope": a.scope, "result": a.result}
            engine.current()["e2e_scope"] = result
            if a.result == "PASS" and a.scope == "full": engine.state["incremental_since_full"] = 0
            elif a.result == "PASS" and not engine.current().get("incremental_counted"):
                engine.state["incremental_since_full"] += 1
                engine.current()["incremental_counted"] = True
        elif a.command == "phase":
            run = engine.current()
            if a.status == "COMPLETED":
                require(a.name == "report", "completion is only valid in report phase")
                _, resolved = engine.assert_plan()
                require(all(engine.state["tickets"].get(resolved[t], {}).get("status") == "COMMITTED" for t in run["tasks"]), "required tasks incomplete")
                require(run["checks"].get("audit", {}).get("result") == "PASS" and run["checks"].get("e2e", {}).get("result") in {"PASS", "N/A"}, "required checks have not passed")
                current_digest = digest(work_files(root))
                require(all(run["checks"][s]["fingerprint"] == current_digest and run["checks"][s]["spec_revision"] == revision(root) for s in ("audit", "e2e")), "check results are stale")
                require(not dirty(root), "main worktree is dirty")
            if a.status in {"INCOMPLETE", "NEEDS_USER"}: require(a.reason.strip(), "reason required")
            run.update(phase=a.name, status=a.status, reason=a.reason)
            result = run
        else:
            raise Invalid("unknown command")
        engine.save()
        return result


def main():
    try:
        print(json.dumps(execute(parser().parse_args()), ensure_ascii=False, indent=2))
    except (Invalid, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
