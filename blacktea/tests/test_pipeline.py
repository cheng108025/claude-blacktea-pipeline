import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load("pipeline")


def ticket(ident="T01", deps=None, supersedes=None):
    return {"id": ident, "title": ident, "feature": "demo", "description": "demo behavior",
            "approach": "implement behavior", "files": ["app.py", "new.py"],
            "depends_on": deps or [], "dod": ["expected behavior"], "verify": ["python3 app.py"],
            "supersedes": supersedes or []}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="blacktea-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.g("init", "-q")
        self.g("config", "user.name", "Blacktea Test")
        self.g("config", "user.email", "test@example.invalid")
        (self.root / ".pipeline/plan").mkdir(parents=True)
        (self.root / ".gitignore").write_text(".pipeline/state.*\n.pipeline/worktrees/\n.pipeline/rounds/\n")
        (self.root / "app.py").write_text("print(1)\n")
        (self.root / ".pipeline/plan/01-requirements.md").write_text("FINAL\nexpected: 2\n")
        self.write_plan([ticket()])
        self.commit("baseline")
        self.call("init")

    def g(self, *args, cwd=None):
        return p.git(cwd or self.root, *args).decode().strip()

    def commit(self, message, cwd=None):
        self.g("add", "-A", cwd=cwd)  # test fixture only; dispatcher uses explicit file lists
        self.g("commit", "-qm", message, cwd=cwd)
        return self.g("rev-parse", "HEAD", cwd=cwd)

    def call(self, *args):
        return p.execute(p.parser().parse_args(["--root", str(self.root), *map(str, args)]))

    def write_plan(self, tickets):
        (self.root / ".pipeline/plan/tickets.json").write_text(json.dumps({"status": "FINAL", "tickets": tickets}))

    def begin(self, ident="T01"):
        self.run_data = self.call("new-run", "--mode", "build", "--tasks", ident)
        task = self.call("start", "--task", ident)
        self.cwd = Path(task["cwd"])
        self.g("worktree", "add", "-b", task["branch"], task["cwd"], task["base_head"])
        return task

    def receipt(self, ident="T01"):
        self.call("task-status", "--task", ident, "--status", "CHECKING")
        report = Path(self.run_data["round_dir"]) / "ticket-checks/check.md"
        report.write_text("PASS: actual fixture verification\n")
        return self.call("receipt", "--task", ident, "--cwd", self.cwd, "--evidence", report)

    def integrate(self, ident="T01"):
        sha = self.commit("implementation", cwd=self.cwd)
        self.call("verify-commit", "--task", ident, "--commit", sha)
        self.g("merge", "--ff-only", sha)
        self.call("complete", "--task", ident, "--commit", sha)
        return sha


class PipelineTests(Fixture):
    def test_untracked_mutation_invalidates_receipt(self):
        self.begin()
        (self.cwd / "new.py").write_text("print(2)\n")
        self.receipt()
        self.call("verify-receipt", "--task", "T01")
        (self.cwd / "new.py").write_text("print(99)\n")
        with self.assertRaisesRegex(p.Invalid, "content changed"):
            self.call("verify-receipt", "--task", "T01")

    def test_commit_after_check_resume_is_idempotent(self):
        self.begin()
        (self.cwd / "new.py").write_text("print(2)\n")
        self.receipt()
        sha = self.commit("implementation", cwd=self.cwd)
        # Simulate interruption after commit: state is still VERIFIED.
        self.call("verify-commit", "--task", "T01", "--commit", sha)
        with self.assertRaisesRegex(p.Invalid, "integrated"):
            self.call("complete", "--task", "T01", "--commit", sha)
        self.g("merge", "--ff-only", sha)
        self.call("complete", "--task", "T01", "--commit", sha)
        self.assertEqual(self.call("complete", "--task", "T01", "--commit", sha)["status"], "already completed")

    def test_deletion_and_executable_mode_match_commit(self):
        self.begin()
        (self.cwd / "app.py").unlink()
        (self.cwd / "new.py").write_text("#!/usr/bin/env python3\nprint(2)\n")
        (self.cwd / "new.py").chmod(0o755)
        self.receipt()
        self.integrate()

    def test_failed_worktree_does_not_pollute_main(self):
        self.begin()
        (self.cwd / "app.py").write_text("broken\n")
        self.call("task-status", "--task", "T01", "--status", "FAILED", "--reason", "bad behavior")
        self.assertEqual((self.root / "app.py").read_text(), "print(1)\n")
        self.assertFalse(p.dirty(self.root))
        with self.assertRaisesRegex(p.Invalid, "retry budget"):
            self.call("start", "--task", "T01")

    def test_retry_limits_persist_and_cannot_be_raised(self):
        self.begin()
        for _ in range(2):
            self.call("task-status", "--task", "T01", "--status", "FAILED")
            self.call("attempt", "--key", "ticket:T01", "--limit", 2)
            self.call("start", "--task", "T01")
        self.call("task-status", "--task", "T01", "--status", "FAILED")
        with self.assertRaisesRegex(p.Invalid, "exhausted"):
            self.call("attempt", "--key", "ticket:T01", "--limit", 2)
        with self.assertRaises(p.Invalid):
            self.call("attempt", "--key", "ticket:T01", "--limit", 3)

    def test_no_parallel_builds(self):
        self.write_plan([ticket(), ticket("T02")]); self.commit("two tickets")
        self.call("new-run", "--mode", "build", "--tasks", "T01", "T02")
        self.call("start", "--task", "T01")
        with self.assertRaisesRegex(p.Invalid, "another task"):
            self.call("start", "--task", "T02")

    def test_replacement_releases_original_dependents(self):
        self.write_plan([ticket(), ticket("T02", ["T01"]), ticket("T-Rev01", supersedes=["T01"])])
        self.commit("replacement")
        self.run_data = self.call("new-run", "--mode", "amend", "--tasks", "T01", "T02", "T-Rev01")
        self.assertEqual(self.call("ready")["ready"], ["T-Rev01"])
        task = self.call("start", "--task", "T-Rev01")
        self.cwd = Path(task["cwd"])
        self.g("worktree", "add", "-b", task["branch"], task["cwd"], task["base_head"])
        (self.cwd / "app.py").write_text("print(2)\n")
        self.receipt("T-Rev01"); self.integrate("T-Rev01")
        self.assertEqual(self.call("ready")["ready"], ["T02"])

    def test_replacement_dependency_cycle_rejected(self):
        self.write_plan([ticket(), ticket("T-Rev01", ["T01"], ["T01"])])
        with self.assertRaisesRegex(p.Invalid, "cycle"):
            self.call("validate-plan")

    def test_scope_and_draft_checks(self):
        self.begin()
        (self.cwd / "unexpected.py").write_text("print(2)\n")
        with self.assertRaisesRegex(p.Invalid, "out-of-scope"):
            self.receipt()
        data = p.read_json(self.root / ".pipeline/plan/tickets.json")
        data["status"] = "DRAFT"
        p.dump(self.root / ".pipeline/plan/tickets.json", data)
        with self.assertRaisesRegex(p.Invalid, "not FINAL"):
            self.call("ready")

    def test_same_day_revision_change_invalidates_execution(self):
        self.begin()
        (self.root / ".pipeline/plan/01-requirements.md").write_text("FINAL\nexpected: 3\n")
        with self.assertRaisesRegex(p.Invalid, "spec changed"):
            self.call("ready")

    def test_final_tickets_do_not_override_draft_requirements(self):
        (self.root / ".pipeline/plan/01-requirements.md").write_text("> 狀態：DRAFT\nexpected: 2\n")
        self.commit("draft requirements")
        with self.assertRaisesRegex(p.Invalid, "requirements must"):
            self.call("new-run", "--mode", "build", "--tasks", "T01")

    def test_snapshot_includes_new_files_without_touching_source(self):
        self.begin()
        (self.cwd / "new.py").write_text("print(2)\n")
        out = Path(self.run_data["round_dir"]) / "scratch/mutation"
        self.call("snapshot", "--cwd", self.cwd, "--output", out)
        (out / "new.py").write_text("print(99)\n")
        self.assertEqual((self.cwd / "new.py").read_text(), "print(2)\n")
        self.assertFalse((out / ".pipeline").exists())

    def test_snapshot_rejects_symlink(self):
        self.begin()
        (self.cwd / "new.py").symlink_to(self.root / "app.py")
        with self.assertRaisesRegex(p.Invalid, "symlinks"):
            self.call("snapshot", "--cwd", self.cwd, "--output", Path(self.run_data["round_dir"]) / "scratch/unsafe")

    def test_environment_block_is_not_pass(self):
        self.begin()
        self.call("task-status", "--task", "T01", "--status", "ENV_BLOCKED", "--reason", "browser missing")
        with self.assertRaises(p.Invalid):
            self.call("phase", "--name", "report", "--status", "COMPLETED")
        self.call("phase", "--name", "report", "--status", "INCOMPLETE", "--reason", "browser missing")

    def test_ids_survive_new_runs_and_state_view_recovers(self):
        self.assertEqual(self.call("allocate", "--kind", "V", "--count", 2)["ids"], ["V-001", "V-002"])
        self.begin()
        self.call("task-status", "--task", "T01", "--status", "ENV_BLOCKED")
        self.call("phase", "--name", "report", "--status", "INCOMPLETE", "--reason", "test")
        self.call("new-run", "--mode", "change", "--tasks", "T01", "--label", "T-Rev01")
        self.assertEqual(self.call("allocate", "--kind", "V")["ids"], ["V-003"])
        (self.root / ".pipeline/state.md").write_text("stale view")
        self.call("status")
        self.assertIn("02-T-Rev01", (self.root / ".pipeline/state.md").read_text())

    def test_render_builds_fixed_workplan_structure_and_html(self):
        source = self.root / ".pipeline/plan/01-requirements.md"
        source.write_text("> 狀態：FINAL\n\n# 規格書\n\n## 缺口總覽\n\n無缺口\n")
        plan = {"status": "FINAL", "project": "Demo App", "self_audit": "| # | 項目 | 結果 |\n|---|---|---|\n| 1 | 覆蓋 | 0 缺口 |",
                "preamble": [{"heading": "缺口總覽", "body": "無缺口"}],
                "groups": [{"name": "一、基礎建設", "how": "先建環境"}],
                "tickets": [dict(ticket(), group="一、基礎建設", approach="a|b"), ticket("T02", deps=["T01"])]}
        (self.root / ".pipeline/plan/tickets.json").write_text(json.dumps(plan))
        result = self.call("render-plan")
        workplan = (self.root / ".pipeline/plan/02-workplan.md").read_text()
        for expected in ("## 缺口總覽", "### 這一群怎麼做", "- [ ] **T01 T01**", "## 其他工作項", "## 總表",
                         "| T02 | demo | T02 | implement behavior | T01 |", "a\\|b", "## 自我稽核結果"):
            self.assertIn(expected, workplan)
        self.assertIn("tickets=2", " ".join(result["rendered"]))
        page = (self.root / ".pipeline/output/Demo_App_requirements.html").read_text()
        self.assertIn('data-theme="light"', page)
        self.assertTrue((self.root / ".pipeline/output/Demo_App_workplan.html").exists())
        self.assertEqual(source.read_text(), "> 狀態：FINAL\n\n# 規格書\n\n## 缺口總覽\n\n無缺口\n")

    def test_finding_outcomes_feed_metrics(self):
        self.begin()
        self.call("finding", "--id", "V-001", "--outcome", "open", "--severity", "High", "--stage", "audit", "--origin", "introduced")
        self.call("finding", "--id", "V-001", "--outcome", "open")
        self.call("finding", "--id", "V-001", "--outcome", "fixed")
        self.call("finding", "--id", "V-002", "--outcome", "open", "--severity", "Medium", "--stage", "audit", "--origin", "pre-existing")
        self.call("finding", "--id", "V-003", "--outcome", "open", "--severity", "Low", "--stage", "ticket")
        self.call("finding", "--id", "V-003", "--outcome", "withdrawn", "--reason", "behavior is specified")
        with self.assertRaises(ValueError):
            self.call("finding", "--id", "V-004", "--outcome", "open")  # new finding needs severity and stage
        with self.assertRaises(ValueError):
            self.call("finding", "--id", "V-002", "--outcome", "waived")  # needs a reason
        m = self.call("metrics")
        self.assertEqual(m["findings"], 3)
        self.assertEqual(m["by_outcome"], {"fixed": 1, "open": 1, "withdrawn": 1})
        self.assertEqual(m["noise_rate"], 0.5)
        self.assertEqual(m["escaped_past_ticket_check"], 1)  # V-001 only: V-002 pre-existing, V-003 ticket stage
        self.assertEqual(m["multi_round_findings"], 1)

    def test_metrics_first_pass_rate(self):
        self.begin()
        (self.cwd / "app.py").write_text("print(2)\n")
        self.receipt()
        self.integrate()
        m = self.call("metrics")
        self.assertEqual(m["tickets_committed"], 1)
        self.assertEqual(m["ticket_first_pass_rate"], 1.0)

    def test_render_rejects_unknown_group(self):
        self.write_plan([dict(ticket(), group="missing")])
        with self.assertRaises(ValueError):
            self.call("render-plan", "--only", "workplan")

    def test_completion_requires_fresh_checks_but_allows_report_commit(self):
        self.begin()
        (self.cwd / "app.py").write_text("print(2)\n")
        self.receipt(); self.integrate()
        for stage in ("audit", "e2e"):
            report = Path(self.run_data["round_dir"]) / (stage + ".md")
            report.write_text("verified behavior")
            self.call("record-check", "--stage", stage, "--result", "PASS", "--evidence", report)
        (self.root / ".pipeline/output").mkdir()
        (self.root / ".pipeline/output/FINAL-REPORT.md").write_text("summary")
        self.commit("report only")
        self.call("phase", "--name", "report", "--status", "COMPLETED")
        (self.root / "app.py").write_text("print(99)\n")
        self.commit("unverified implementation")
        with self.assertRaisesRegex(p.Invalid, "stale"):
            self.call("phase", "--name", "report", "--status", "COMPLETED")

    def test_spec_only_change_allows_documented_e2e_na(self):
        run = self.call("new-run", "--mode", "change")
        report = Path(run["round_dir"]) / "audit.md"
        report.write_text("spec matches implementation; behavior unchanged")
        self.call("record-check", "--stage", "audit", "--result", "PASS", "--evidence", report)
        with self.assertRaises(p.Invalid):
            self.call("record-check", "--stage", "e2e", "--result", "N/A", "--evidence", report)
        self.call("record-check", "--stage", "e2e", "--result", "N/A", "--evidence", report, "--reason", "only clarified documentation")
        self.call("phase", "--name", "report", "--status", "COMPLETED")

    def test_incremental_e2e_count_once_per_run(self):
        self.begin()
        self.call("record-e2e", "--scope", "incremental", "--result", "PASS")
        self.call("record-e2e", "--scope", "incremental", "--result", "FAIL")
        self.call("record-e2e", "--scope", "incremental", "--result", "PASS")
        self.assertEqual(self.call("status")["incremental_since_full"], 1)
        self.call("record-e2e", "--scope", "full", "--result", "PASS")
        self.assertEqual(self.call("status")["incremental_since_full"], 0)

    def test_question_resolution_and_push_pause_persist(self):
        question = self.call("question", "--source", "T01", "--prompt", "Which behavior?", "--options", "A", "B")
        ident = question["id"]
        self.assertIn(ident, (self.root / ".pipeline/state.md").read_text())
        self.call("push-state", "--status", "PAUSED", "--reason", "scan finding")
        self.call("resolve", "--id", ident, "--answer", "B")
        state = self.call("status")
        self.assertEqual(state["questions"][ident]["status"], "RESOLVED")
        self.assertEqual(state["push"]["status"], "PAUSED")
        with self.assertRaisesRegex(p.Invalid, "already resolved"):
            self.call("resolve", "--id", ident, "--answer", "A")


if __name__ == "__main__":
    unittest.main()
