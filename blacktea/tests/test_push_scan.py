"""Regression scenarios use disposable local repositories and synthetic values."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scan-push.py"


class PushScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Scan Test")
        self.git("config", "user.email", "scan@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.commit("readme.md", "safe baseline\n")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.PIPE).decode()

    def commit(self, name, content):
        (self.repo / name).write_text(content)
        self.git("add", "--", name)
        self.git("commit", "-qm", "fixture")

    def scan(self, base=None):
        args = [sys.executable, str(SCRIPT)]
        if base is not None:
            args.extend(["--base", base])
        result = subprocess.run(args, cwd=self.repo, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_clean_pending_commits(self):
        self.commit("normal.py", "answer = 42\n")
        code, result = self.scan(self.base)
        self.assertEqual(code, 0)
        self.assertEqual(result["pending_commits"], 1)

    def test_added_then_removed_value_is_still_detected_without_disclosure(self):
        self.commit("config.py", "value = None\n")
        baseline = self.git("rev-parse", "HEAD").strip()
        value = "gh" + "p_" + "A" * 36
        self.commit("config.py", "value = '" + value + "'\n")
        self.commit("config.py", "value = None\n")
        self.assertEqual(self.git("diff", baseline, "HEAD", "--", "config.py"), "")
        code, result = self.scan(baseline)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "token-pattern" for f in result["findings"]))
        self.assertNotIn(value, json.dumps(result))

    def test_deleted_sensitive_file_is_detected(self):
        self.commit("credentials.json", "{}\n")
        self.git("rm", "-q", "credentials.json")
        self.git("commit", "-qm", "remove fixture")
        code, result = self.scan(self.base)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["path"] == "credentials.json" for f in result["findings"]))

    def test_merged_side_branch_history_is_scanned(self):
        self.git("checkout", "-qb", "fixture-side")
        self.commit("side.py", "value = '" + "gh" + "p_" + "B" * 36 + "'\n")
        self.commit("side.py", "value = None\n")
        self.git("checkout", "-q", "-")
        self.commit("main.py", "answer = 1\n")
        self.git("merge", "--no-ff", "-qm", "merge fixture", "fixture-side")
        self.assertEqual(self.scan(self.base)[0], 1)

    def test_initial_push_scans_all_history(self):
        self.commit("config.py", "pass" + "word = 'real-looking-fixture-value'\n")
        self.commit("config.py", "password = None\n")
        self.assertEqual(self.scan()[0], 1)

    def test_bad_base_is_unknown(self):
        code, result = self.scan("missing-destination")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "unknown")

    def test_json_assignment_is_detected(self):
        self.commit("config.json", json.dumps({"pass" + "word": "real-looking-fixture-value"}))
        self.assertEqual(self.scan(self.base)[0], 1)

    def test_large_blob_is_unknown(self):
        self.commit("large.txt", "a" * (10 * 1024 * 1024 + 1))
        code, result = self.scan(self.base)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "unknown")

    def test_private_key_marker_is_detected_without_disclosure(self):
        marker = "-----BEGIN " + "PRIVATE KEY-----"
        self.commit("config.txt", marker + "\nfixture-data\n")
        code, result = self.scan(self.base)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "private-key" for f in result["findings"]))
        self.assertNotIn(marker, json.dumps(result))

    def test_nested_repository_is_unknown(self):
        self.git("update-index", "--add", "--cacheinfo", "160000," + self.base + ",nested")
        self.git("commit", "-qm", "gitlink fixture")
        code, result = self.scan(self.base)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "unknown")

    def test_no_pending_commits_still_checks_final_tree(self):
        code, result = self.scan(self.base)
        self.assertEqual(code, 0)
        self.assertEqual(result["pending_commits"], 0)
        self.assertEqual(result["scanned_trees"], 1)


if __name__ == "__main__":
    unittest.main()
