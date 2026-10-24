#!/usr/bin/env python3
"""Read-only scan of every pending commit tree. Never print matched values."""
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
TOKEN = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16})")
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
ASSIGNMENT = re.compile(
    rb'''\b(?:api[_-]?key|secret|password)\b["']?\s*[:=]\s*["']([^"'\r\n]{8,})["']''', re.I
)
PLACEHOLDER = re.compile(
    rb"^(?:example|dummy|test|mock|changeme|replace[_ -]?me|your[_ -]|<|\$\{|\*{3}|\.{3})", re.I
)


def content_rules(data):
    rules = []
    if TOKEN.search(data):
        rules.append("token-pattern")
    if PRIVATE_KEY.search(data):
        rules.append("private-key")
    if any(not PLACEHOLDER.search(m.group(1)) for m in ASSIGNMENT.finditer(data)):
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
            rules = ["sensitive-path"] if SENSITIVE_PATH.search(path) else []
            if oid not in blobs:
                size = int(git("cat-file", "-s", oid))
                if size > 10 * 1024 * 1024:
                    raise ScanError("blob exceeds 10 MiB; separate scan required")
                blobs[oid] = content_rules(git("cat-file", "blob", oid))
            rules.extend(blobs[oid])
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
