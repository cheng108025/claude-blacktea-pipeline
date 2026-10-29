#!/usr/bin/env python3
"""Check staged Claude references, metadata, and helper syntax (requires PyYAML)."""
import ast
import json
from pathlib import Path
import re
import sys
import yaml


def check(root):
    errors = []
    agents = {}
    for path in sorted((root / "agents").glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text()
        front = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        if not front:
            errors.append(str(path.relative_to(root)) + ": missing frontmatter")
            continue
        try:
            fields = yaml.safe_load(front[1])
        except yaml.YAMLError:
            errors.append(path.name + ": invalid YAML")
            continue
        if "description" not in fields:
            errors.append(path.name + ": missing description")
        if path.name == "agent1_plan.md":
            if "name" in fields: errors.append("agent1 must remain a main-conversation document")
        else:
            name = fields.get("name", "")
            if not name or name in agents: errors.append("missing/duplicate agent name: " + name)
            agents[name] = path
            if fields.get("model") not in {"opus", "sonnet", "haiku", "inherit"}:
                errors.append(path.name + ": invalid model")
            if name != "agent0-conduct" and "Agent" not in fields.get("disallowedTools", ""):
                errors.append(path.name + ": worker can delegate")
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        text = path.read_text()
        front = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        try:
            fields = yaml.safe_load(front[1]) if front else {}
        except yaml.YAMLError:
            errors.append(str(path.relative_to(root)) + ": invalid YAML")
            continue
        allowed = {"name", "description", "user-invocable", "disable-model-invocation", "allowed-tools", "context", "agent", "model", "argument-hint", "hooks"}
        if set(fields) - allowed:
            errors.append(str(path.relative_to(root)) + ": unknown Claude skill fields")
        for key in ("user-invocable", "disable-model-invocation"):
            if key in fields and not isinstance(fields[key], bool):
                errors.append(str(path.relative_to(root)) + ": non-boolean " + key)
        if fields.get("name") != path.parent.name or not fields.get("description"):
            errors.append(str(path.relative_to(root)) + ": invalid skill metadata")
    for path in (root / "commands").glob("*.md"):
        text = path.read_text()
        if "$ARGUMENTS" not in text:
            errors.append(path.name + ": arguments are not forwarded")
    for directory in ("agents", "commands", "skills", "blacktea"):
        for path in (root / directory).rglob("*.md"):
            # Deployment paths resolve to this staging tree, never to the live engine.
            for ref in re.findall(r"~/.claude/([^`\s）()，；。]+)", path.read_text()):
                ref = ref.rstrip("/、：:;,.。")
                if any(c in ref for c in "*<>|") or ref in {"settings.json", "hooks"} or ref.startswith("hooks/"):
                    continue
                if not (root / ref).exists():
                    errors.append(str(path.relative_to(root)) + ": missing reference " + ref)
    for path in (root / "blacktea/templates").glob("*.json"):
        try: json.loads(path.read_text())
        except ValueError: errors.append(str(path.relative_to(root)) + ": invalid JSON")
    for path in (root / "blacktea/scripts").glob("*.py"):
        try: ast.parse(path.read_text())
        except SyntaxError: errors.append(path.name + ": invalid Python")
    return errors


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    errors = check(root)
    print(json.dumps({"root": str(root), "errors": errors, "valid": not errors}, ensure_ascii=False, indent=2))
    sys.exit(bool(errors))
