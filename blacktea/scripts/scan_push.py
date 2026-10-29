#!/usr/bin/env python3
"""Read-only scan of every pending commit tree. Never print matched values.

Candidate scan, not a guarantee. Heuristics trade recall for usability and are
documented in skills/git/SKILL.md:
- Template files (.env.example / .sample / .template / .dist, *.example ...) whose
  assignments are all empty or placeholders are not reported as sensitive paths.
  A value is only a placeholder if the WHOLE value is one, never just a prefix.
- Assignment values made only of fixture words and digits (SECRET123, your-key-here),
  non-ASCII notes, markup placeholders, or code references are skipped.
- Quoted values may embed the other quote character, span multiple physical lines
  (JSON pretty-printing, YAML folded scalars), and YAML `key: |`/`key: >` block
  scalars are read from their indented body.
- Name-matching and the fixture-word check are written to stay linear in input size
  (bounded quantifiers, no nested backtracking) so adversarial input cannot stall the
  scan; see test_pathological_* in tests/test_push_scan.py.
"""
import argparse
import json
import os
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
# Prefix/suffix are bounded (not `*`) so a name match can never backtrack across an
# unbounded run of word characters — see test_pathological_repeated_keyword_blob.
CREDENTIAL_NAME = (
    rb"[A-Za-z0-9_]{0,48}(?:api[_-]?key|secret|passw(?:or)?d|pwd|token|"
    rb"private[_-]?key|access[_-]?key|client[_-]?secret)[A-Za-z0-9_]{0,48}"
)
# Value may be double- or single-quoted (each may embed the OTHER quote character,
# and may continue onto a following line — JSON pretty-printing, YAML folding) or
# bare (.env / .ini style, same line only: an empty bare value must never swallow
# the next line's assignment — see test_empty_assignment_does_not_borrow_next_line).
ASSIGNMENT = re.compile(
    rb"(?i)(?<![A-Za-z0-9_])" + CREDENTIAL_NAME + rb"[\"']?[ \t]*[:=]"
    # Run-then-escape form, not `(?:[^"\\]|\\.)*`: equivalent but each char is
    # tested once via a quantified class instead of retrying the alternation per
    # character, which matters on a multi-MB value (test_pathological_large_quoted_value).
    rb"(?:[ \t]*(?:\r?\n[ \t]*)*\"([^\"\\]*(?:\\.[^\"\\]*)*)\""
    rb"|[ \t]*(?:\r?\n[ \t]*)*'([^'\\]*(?:\\.[^'\\]*)*)'"
    rb"|[ \t]*([^\s\"'`*&<>#;,)\]}]+))"
)
# YAML block scalar: `key: |` / `key: >` with the value on indented following lines
# (no quotes to delimit it, so it needs its own pattern). \1 pins the continuation
# lines to more indentation than the key itself.
YAML_BLOCK = re.compile(
    rb"(?im)^([ \t]*)(?:" + CREDENTIAL_NAME + rb")[ \t]*:[ \t]*[|>][+-]?[ \t]*\r?\n"
    rb"((?:\1[ \t]+\S.*\r?\n?)+)"
)
# Whole-value markers that mean "fill this in" regardless of what is written inside
# them. Matched with fullmatch (never a prefix check) so "test"+<realsecret> cannot
# ride in on a marker that only covers its own leading characters.
EXACT_PLACEHOLDER = re.compile(
    rb"(?i)<[^<>]*>?|&lt;[^&]*(?:&gt;)?|\$\{[^}]*\}?|\$[A-Za-z_][A-Za-z0-9_]*|\*{3,}|\.{3,}"
    rb"|none|null|true|false"
)
# One fixture token: a run of digits/separators, or one of these whole words. Matched
# token-by-token (is_all_fixture_tokens below), never as a backtracking `(?:...)+$`
# over the whole value — see test_pathological_fixture_word_value for why that matters.
FIXTURE_TOKEN = re.compile(
    rb"(?i)[0-9_\-.:/ ]+|abc|xyz|x{3,}|my|your|the|here|super|secret|value|testing|test|"
    rb"example|sample|dummy|fake|mock|placeholder|redacted|changeme|replace|key|api|token|"
    rb"insert|fill|put|demo|foo|bar|baz|local|dev|default|not|set|none|null"
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
# An end-of-line comment: '#' at the very start of what remains, or after whitespace.
# Only used on values that are NOT quoted (parse_template_value below never runs this
# over the inside of a quoted value, where a literal '#' is part of the data).
LINE_COMMENT = re.compile(rb"(?:^|[ \t])#.*$")


def is_all_fixture_tokens(value):
    """True if value is entirely fixture words/digits/separators, e.g. SECRET123,
    abc123secret, your-key-here. Walks token-by-token (advancing by each match's
    end) instead of backtracking over a `(?:...)+` loop, so it stays linear even on
    adversarial input such as "X"*64 — see test_pathological_fixture_word_value."""
    pos, length, has_letter = 0, len(value), False
    while pos < length:
        m = FIXTURE_TOKEN.match(value, pos)
        if not m:
            return False
        if re.search(rb"[A-Za-z]", m.group()):
            has_letter = True
        pos = m.end()
    return has_letter  # a value of pure digits/separators is still reported


def looks_like_placeholder(value):
    if not value:
        return True
    if not value.isascii():  # natural-language notes such as 你的金鑰 (C-level
        return True          # check: a Python-level per-byte loop is slow on a huge value)
    if EXACT_PLACEHOLDER.fullmatch(value):
        return True
    return is_all_fixture_tokens(value)


def credential_values(data):
    """Yield assignment values that look like real credentials."""
    for m in ASSIGNMENT.finditer(data):
        if m.group(1) is not None:
            value, quoted = m.group(1), True
        elif m.group(2) is not None:
            value, quoted = m.group(2), True
        else:
            value, quoted = m.group(3), False
        if len(value) < 8 or looks_like_placeholder(value):
            continue
        if not quoted and (CODE_REFERENCE.search(value) or value.isdigit() or PLAIN_WORD.search(value)):
            continue  # code reference, count, or lowercase keyword
        yield value
    for m in YAML_BLOCK.finditer(data):
        value = b" ".join(line.strip() for line in m.group(2).splitlines() if line.strip())
        if len(value) >= 8 and not looks_like_placeholder(value):
            yield value


def parse_template_value(raw):
    """Quote-aware value extraction for one KEY=... template line.

    A '#' inside a quoted value is literal data, not a comment: find the matching
    closing quote first (the SAME quote character; the other kind may appear inside
    it) and return only what is between them, ignoring anything after the close.
    An unclosed quote returns None so the caller treats the line conservatively.
    For an unquoted value, only a '#' at the start or after whitespace is a comment.
    """
    raw = raw.strip()
    if raw[:1] in (b'"', b"'"):
        quote = raw[:1]
        end = raw.find(quote, 1)
        return None if end == -1 else raw[1:end]
    m = LINE_COMMENT.search(raw)
    return (raw[: m.start()] if m else raw).strip()


def template_is_clean(data):
    """A template may only hold comments and KEY= lines with empty or placeholder values.

    Anything else (raw key material, YAML/JSON bodies, real values, an unclosed
    quote) keeps the sensitive-path finding — the conservative default."""
    for line in data.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(b"#"):
            continue
        m = ENV_LINE.match(line)
        if not m:
            return False
        value = parse_template_value(m.group(1))
        if value is None or not looks_like_placeholder(value):
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
    parser.add_argument("--root", help="Repository to scan (default: current directory)")
    parser.add_argument("--base", help="Verified destination remote ref; omit only for an empty destination")
    args = parser.parse_args()
    try:
        if args.root:
            os.chdir(args.root)
        result = scan(args.base)
    except (ScanError, OSError, ValueError) as exc:
        print(json.dumps({"status": "unknown", "error": str(exc)}, ensure_ascii=True))
        return 2
    result["status"] = "findings" if result["findings"] else "clean"
    print(json.dumps(result, ensure_ascii=True))
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
