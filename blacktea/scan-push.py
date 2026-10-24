#!/usr/bin/env python3
"""Read-only scan of every pending commit tree. Never print matched values.

Candidate scan, not a guarantee. Two heuristics trade recall for usability and are
documented in skills/git/SKILL.md:
- Template files (.env.example / .sample / .template / .dist, *.example ...) whose
  assignments are all empty or placeholders are not reported as sensitive paths.
- Assignment values made only of fixture words and digits (SECRET123, your-key-here),
  non-ASCII notes, markup placeholders, or code references are skipped.
"""
import argparse
import json
import re
import subprocess
import sys


class ScanError(Exception):
    pass


def git(*args):
    result = subprocess.run(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        # Git errors can include credential-bearing remote URLs: do not echo stderr.
        raise ScanError("git command failed: " + args[0])
    return result.stdout


SENSITIVE_PATH = re.compile(
    r"credential|token|secret|\.env|\.pem|id_rsa|hosts\.yml|\.key$", re.I
)
TOKEN = re.compile(
    rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}"
    rb"|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.)"  # JWT
)
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
# Credential-like names, allowing prefixes/suffixes such as FRED_API_KEY,
# DB_PASSWORD or AWS_SECRET_ACCESS_KEY (the old \b-anchored rule missed them).
CREDENTIAL_NAME = (
    rb"[A-Za-z0-9_]*(?:api[_-]?key|secret|passw(?:or)?d|pwd|token|"
    rb"private[_-]?key|access[_-]?key|client[_-]?secret)[A-Za-z0-9_]*"
)
# Value may be quoted or bare (.env / .ini / YAML style).
ASSIGNMENT = re.compile(
    rb"(?i)(?<![A-Za-z0-9_])" + CREDENTIAL_NAME
    + rb"[\"']?[ \t]*[:=][ \t]*(?:([\"'])([^\"'\r\n]*)\1|([^\s\"'`*&<>#;,)\]}]+))"
)
PLACEHOLDER = re.compile(
    rb"^(?:example|dummy|test|mock|changeme|replace[_ -]?me|your[_ -]|<|&lt;|\$\{|\$[A-Za-z_]|\*{3}|\.{3}"
    rb"|none$|null$|true$|false$)",
    re.I,
)
# Whole value built only from fixture words, digits and separators
# (SECRET123, abc123secret, SUPERSECRET123, your-key-here). A real value that merely
# contains "test" somewhere (MyTestPass2024!, base64 noise) is still reported.
FIXTURE_VALUE = re.compile(
    rb"(?i)^(?=.*[a-z])(?:[0-9_\-.:/]|abc|xyz|x{3,}|my|your|the|here|super|secret|value|test(?:ing)?|"
    rb"example|sample|dummy|fake|mock|placeholder|redacted|changeme|replace|key|api|token|"
    rb"insert|fill|put|demo|foo|bar|baz|local|dev|default|not|set|none|null)+$"
)
# Unquoted identifier chain, call, interpolation or expression:
# os.environ[...], config.db_password, get_token(), {config.KEY}, [part.strip() ...].
CODE_REFERENCE = re.compile(
    rb"^[A-Za-z_][A-Za-z0-9_]{0,40}(?:(?:\.[A-Za-z_][A-Za-z0-9_]{0,40})+(?:[(\[{].*)?|[(\[{].*)$|^[$\[{(]"
)
# Bare keyword or constant name: token_type=bearer, api_key: required, key = FRED_API_KEY.
PLAIN_WORD = re.compile(rb"^(?:[a-z_-]{1,19}|[A-Z_-]{1,19}|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$")
TEMPLATE_PATH = re.compile(
    r"(?i)(?:^|/)\.env\.(?:example|sample|template|dist)$|\.(?:example|sample|template|dist)$"
)
ENV_LINE = re.compile(rb"^[ \t]*(?:export[ \t]+)?[A-Za-z_][A-Za-z0-9_]*[ \t]*=[ \t]*(.*?)[ \t\r]*$")


def looks_like_placeholder(value):
    if not value:
        return True
    if any(b > 0x7F for b in value):  # natural-language notes such as 你的金鑰
        return True
    return bool(PLACEHOLDER.search(value) or FIXTURE_VALUE.search(value))


def credential_values(data):
    """Yield assignment values that look like real credentials."""
    for m in ASSIGNMENT.finditer(data):
        quoted = m.group(1) is not None
        value = m.group(2) if quoted else m.group(3)
        if len(value) < 8 or looks_like_placeholder(value):
            continue
        if not quoted and (CODE_REFERENCE.search(value) or value.isdigit() or PLAIN_WORD.search(value)):
            continue  # code reference, count, or lowercase keyword
        yield value


def template_is_clean(data):
    """A template may only hold comments and KEY= lines with empty or placeholder values.

    Anything else (raw key material, YAML/JSON bodies, real values) keeps the
    sensitive-path finding."""
    for line in data.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(b"#"):
            continue
        m = ENV_LINE.match(line)
        if not m:
            return False
        value = re.sub(rb"(?:^|[ \t]+)#.*$", b"", m.group(1)).strip().strip(b"\"'")
        if not looks_like_placeholder(value):
            return False
    return True


def content_rules(data):
    rules = []
    if TOKEN.search(data):
        rules.append("token-pattern")
    if PRIVATE_KEY.search(data):
        rules.append("private-key")
    if any(True for _ in credential_values(data)):
        rules.append("credential-assignment")
    return rules


def scan(base=None):
    head = git("rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if base:
        base_sha = git("rev-parse", "--verify", base + "^{commit}").decode().strip()
        # Divergence is allowed: all commits reachable from HEAD but not the remote
        # are scanned, including merged side branches.
        rev_range = base_sha + ".." + head
    else:
        rev_range = head
    commits = git("rev-list", "--reverse", "--topo-order", rev_range).decode().splitlines()
    # Also inspect the final tree if no commits are pending.
    trees = commits or [head]
    blobs = {}
    findings = []
    seen = set()
    for commit in trees:
        for entry in git("ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
            if not entry:
                continue
            meta, raw_path = entry.split(b"\t", 1)
            _mode, kind, raw_oid = meta.split()
            path = raw_path.decode("utf-8", "surrogateescape")
            if kind != b"blob":
                raise ScanError("unscanned nested repository (gitlink)")
            oid = raw_oid.decode()
            if oid not in blobs:
                size = int(git("cat-file", "-s", oid))
                if size > 10 * 1024 * 1024:
                    raise ScanError("blob exceeds 10 MiB; separate scan required")
                data = git("cat-file", "blob", oid)
                blobs[oid] = (content_rules(data), template_is_clean(data))
            found, clean_template = blobs[oid]
            rules = []
            if SENSITIVE_PATH.search(path) and not (
                TEMPLATE_PATH.search(path) and not found and clean_template
            ):
                rules.append("sensitive-path")
            rules.extend(found)
            for rule in rules:
                key = (path, oid, rule)
                if key not in seen:
                    seen.add(key)
                    findings.append({"commit": commit, "path": path, "rule": rule})
    return {"pending_commits": len(commits), "scanned_trees": len(trees), "findings": findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Verified destination remote ref; omit only for an empty destination")
    args = parser.parse_args()
    try:
        result = scan(args.base)
    except (ScanError, OSError, ValueError) as exc:
        print(json.dumps({"status": "unknown", "error": str(exc)}, ensure_ascii=True))
        return 2
    result["status"] = "findings" if result["findings"] else "clean"
    print(json.dumps(result, ensure_ascii=True))
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
