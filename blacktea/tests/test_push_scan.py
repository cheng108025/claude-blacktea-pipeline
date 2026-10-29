"""Regression scenarios use disposable local repositories and synthetic values."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_push.py"


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
        (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
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

    def test_root_option_scans_other_directory(self):
        self.commit("normal.py", "answer = 42\n")
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.repo), "--base", self.base],
                                cwd=tempfile.gettempdir(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["pending_commits"], 1)

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

    def test_empty_env_template_is_clean(self):
        self.commit(".env.example", "FRED_API_KEY=\n# comment\nDB_PASS" + "WORD=\"\"\n")
        self.assertEqual(self.scan(self.base)[0], 0)

    def test_env_template_with_value_is_flagged(self):
        self.commit(".env.example", "FRED_API_" + "KEY=" + "a1b2c3d4" + "e5f6a7b8c9d0\n")
        code, result = self.scan(self.base)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "sensitive-path" for f in result["findings"]))

    def test_template_with_plain_word_value_is_flagged(self):
        self.commit(".env.sample", "HOST=productionhostname\n")
        self.assertEqual(self.scan(self.base)[0], 1)

    def test_real_env_file_is_still_flagged(self):
        self.commit(".env", "FRED_API_KEY=\n")
        self.assertEqual(self.scan(self.base)[0], 1)

    def test_prefixed_and_unquoted_assignments_are_detected(self):
        cases = [
            "FRED_API_" + "KEY=\"a1b2c3d4e5f6a7b8c9d0\"\n",
            "DB_PASS" + "WORD=\"Zq7vLm2pRx9w\"\n",
            "AWS_SECRET_ACCESS_" + "KEY=\"wJalrXUtnFEMI7K7MDENGbPxRfiCYEXAMPLEKY\"\n".replace("EXAMPLE", "QWERTYU"),
            "pass" + "word=hunter2hunter2\n",
            "FRED_API_" + "KEY=a1b2c3d4e5f6a7b8c9d0\n",
        ]
        for i, line in enumerate(cases):
            with self.subTest(i=i):
                name = "conf%d.ini" % i
                self.commit(name, line)
                code, result = self.scan(self.base)
                self.assertEqual(code, 1)
                self.assertTrue(any(f["path"] == name and f["rule"] == "credential-assignment"
                                    for f in result["findings"]))
                self.assertNotIn(line.split("=", 1)[1].strip().strip('"'), json.dumps(result))
                self.git("rm", "-q", name)
                self.git("commit", "-qm", "remove fixture")
                self.base = self.git("rev-parse", "HEAD").strip()

    def test_code_references_and_fixtures_are_not_flagged(self):
        lines = [
            "api_key = os.environ[\"FRED_API_KEY\"]",
            "token = get_token()",
            "pass" + "word = config.db_password",
            "pass" + "word=$DB_PASSWORD",
            "api_key=SECRET123",
            "pass" + "word = 'abc123secret'",
            "api_key=***",
            "api_key=&lt;key&gt;",
            "FRED_API_KEY=`，值為空的範本",
            "secret: \"your-key-here\"",
            "token_count = 1234567890",
            "url = f\"x?api_" + "key={config.FRED_API_KEY}\"",
            "tokens = [part.strip() for part in raw]",
            "api_" + "key=SECRETAB",
        ]
        self.commit("fixtures.py", "\n".join(lines) + "\n")
        code, result = self.scan(self.base)
        self.assertEqual(code, 0, result)

    def test_empty_assignment_does_not_borrow_next_line(self):
        self.commit("conf.ini", "PASS" + "WORD=\nNEXT=a1b2c3d4e5f6a7b8\n")
        self.assertEqual(self.scan(self.base)[0], 0)

    def test_template_with_raw_material_is_flagged(self):
        cases = {
            "token.sample": "Zq7vLm2pRx9wKt4n" + "Bc8dHf3jMs6q\n",
            "secrets.example": "db:\n  pass" + "word: \"\"\n",
            ".env.template": "FRED_API_" + "KEY=" + "a1b2c3d4e5f6" + "a7b8 # real\n",
            ".env.dist": "PORT=8080\n",
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                self.commit(name, content)
                code, result = self.scan(self.base)
                self.assertTrue(any(f["path"] == name and f["rule"] == "sensitive-path"
                                    for f in result["findings"]))

    def test_template_comments_and_inline_notes_are_clean(self):
        self.commit("config/.ENV.Example",
                    "# get one at the provider\nexport FRED_API_" + "KEY=  # fill in\nDB_PASS" + "WORD='changeme'\r\n")
        self.assertEqual(self.scan(self.base)[0], 0)

    def test_real_values_containing_fixture_words_are_detected(self):
        cases = [
            "pass" + "word = \"MyTest" + "Pass2024!\"\n",
            "API_" + "KEY=Qw8test" + "Zx3Lp9Vn2Rt7\n",
            "secret: \"Where" + "Is9Kz4Lq\"\n",
            "DB_PASS" + "WORD=Hunter" + "hunter\n",
            "JWT_SEC" + "RET=Ab9-cD8_" + "eF7.gH6-iJ5\n",
        ]
        for i, line in enumerate(cases):
            with self.subTest(i=i):
                name = "real%d.cfg" % i
                self.commit(name, line)
                code, result = self.scan(self.base)
                self.assertTrue(any(f["path"] == name and f["rule"] == "credential-assignment"
                                    for f in result["findings"]), line)

    def test_jwt_is_detected(self):
        jwt = "ey" + "J" + "hbGciOiJIUzI1NiJ9" + ".ey" + "J" + "zdWIiOiIxMjM0NTY3In0" + ".c2lnbmF0dXJl"
        self.commit("note.txt", "auth " + jwt + "\n")
        code, result = self.scan(self.base)
        self.assertTrue(any(f["rule"] == "token-pattern" for f in result["findings"]))
        self.assertNotIn(jwt, json.dumps(result))

    def test_prefix_bypass_is_detected(self):
        # Must-fix #1: a value merely starting with "test" is not a placeholder.
        v = ("A" * 8) + "9" + ("B" * 11)
        self.commit("config.ini", "DB_PASS" + "WORD=\"test" + v + "\"\n")
        code, result = self.scan(self.base)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "credential-assignment" for f in result["findings"]))
        self.assertNotIn(v, json.dumps(result))

    def test_prefix_bypass_in_template_is_detected(self):
        v = ("A" * 8) + "9" + ("B" * 11)
        self.commit(".env.example", "DB_PASS" + "WORD=\"test" + v + "\"\n")
        code, result = self.scan(self.base)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "sensitive-path" for f in result["findings"]))

    def test_template_quoted_hash_is_not_treated_as_comment(self):
        # Must-fix #2: a '#' inside quotes is literal data, not a comment.
        v = ("A" * 8) + "9" + ("B" * 11)
        for name, quote in ((".env.example", "\""), (".env.sample", "'")):
            with self.subTest(name=name):
                self.commit(name, "FOO_KEY=" + quote + " # " + v + quote + "\n")
                code, result = self.scan(self.base)
                self.assertEqual(code, 1)
                self.assertTrue(any(f["path"] == name and f["rule"] == "sensitive-path"
                                    for f in result["findings"]))
                self.git("rm", "-q", name)
                self.git("commit", "-qm", "remove fixture")
                self.base = self.git("rev-parse", "HEAD").strip()

    def test_mismatched_quote_characters_are_detected(self):
        # Must-fix #3: a double-quoted value may contain a literal apostrophe and
        # vice versa; the old backreference-based rule missed both.
        v = ("A" * 8) + "9" + ("B" * 11)
        cases = [
            "DB_PASS" + "WORD=\"" + v + "'\"\n",
            "DB_PASS" + "WORD='" + v + "\"'\n",
        ]
        for i, line in enumerate(cases):
            with self.subTest(i=i):
                name = "mix%d.ini" % i
                self.commit(name, line)
                code, result = self.scan(self.base)
                self.assertEqual(code, 1)
                self.assertTrue(any(f["path"] == name and f["rule"] == "credential-assignment"
                                    for f in result["findings"]))
                self.assertNotIn(v, json.dumps(result))
                self.git("rm", "-q", name)
                self.git("commit", "-qm", "remove fixture")
                self.base = self.git("rev-parse", "HEAD").strip()

    def test_multiline_json_and_yaml_values_are_detected(self):
        # Must-fix #4: sensitive fields whose value sits on a different line.
        v = ("A" * 8) + "9" + ("B" * 11)
        cases = {
            "config.json": "{\n \"pass" + "word\":\n \"" + v + "\"\n}\n",
            "config.yml": "pass" + "word: |\n  " + v + "\n",
            "folded.yml": "pass" + "word: >\n  " + v + "\n",
            "wrapped.yml": "pass" + "word: \"" + v[:9] + "\n  " + v[9:] + "\"\n",
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                self.commit(name, content)
                code, result = self.scan(self.base)
                self.assertEqual(code, 1, (name, result))
                self.assertTrue(any(f["path"] == name and f["rule"] == "credential-assignment"
                                    for f in result["findings"]))
                self.assertNotIn(v, json.dumps(result))
                self.git("rm", "-q", name)
                self.git("commit", "-qm", "remove fixture")
                self.base = self.git("rev-parse", "HEAD").strip()

    def test_pathological_fixture_word_value_scans_quickly(self):
        # Must-fix #5 case A: a 99-byte quoted value used to take 3+ seconds.
        import time
        v = ("A" * 8) + "9" + ("B" * 11)
        value = ("X" * 64) + v
        self.commit("config.ini", "DB_PASS" + "WORD=\"" + value + "\"\n")
        started = time.perf_counter()
        code, result = self.scan(self.base)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 2.0, "scan took %.2fs, expected sub-second" % elapsed)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "credential-assignment" for f in result["findings"]))

    def test_pathological_repeated_keyword_blob_scans_quickly(self):
        # Must-fix #5 case B: a blob of nothing but "password" (no '=' at all)
        # used to take ~10s per MiB.
        import time
        self.commit("large.txt", "pass" + "word" * (300_000 // 8))
        started = time.perf_counter()
        code, result = self.scan(self.base)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 2.0, "scan took %.2fs, expected sub-second" % elapsed)
        self.assertEqual(code, 0, result)

    def test_pathological_large_quoted_value_scans_quickly(self):
        # A legitimate-looking multi-MB quoted value: the alternation-per-character
        # form of the quoted-value pattern was slow here even without catastrophic
        # backtracking (regression guard for the run-then-escape rewrite).
        import time
        v = ("A" * 8) + "9" + ("B" * 11)
        value = ("X" * (2 * 1024 * 1024)) + v
        self.commit("config.ini", "DB_PASS" + "WORD=\"" + value + "\"\n")
        started = time.perf_counter()
        code, result = self.scan(self.base)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 2.0, "scan took %.2fs, expected sub-second" % elapsed)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule"] == "credential-assignment" for f in result["findings"]))

    def test_no_pending_commits_still_checks_final_tree(self):
        code, result = self.scan(self.base)
        self.assertEqual(code, 0)
        self.assertEqual(result["pending_commits"], 0)
        self.assertEqual(result["scanned_trees"], 1)


if __name__ == "__main__":
    unittest.main()
