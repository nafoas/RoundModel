#!/usr/bin/env python3
"""Owner's rule: read every bit of the method documentation at the beginning
and end of every single command. Runs on PreToolUse and PostToolUse for all
tools and puts CLAUDE.md, docs/INTENTS.md and the tasks files into context."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

try:
    event = json.load(sys.stdin).get("hook_event_name", "PreToolUse")
except Exception:
    event = "PreToolUse"

docs = [ROOT / "CLAUDE.md", ROOT / "docs" / "INTENTS.md"]
docs += sorted((ROOT / "tasks").glob("*.md"))

when = "BEFORE this command" if event == "PreToolUse" else "AFTER this command"
parts = [f"Method documentation, re-read {when} (owner's rule: every command, "
         "beginning and end). Does this action serve what the owner asked, "
         "done the way they asked, judged against HIM by eye?"]
for p in docs:
    try:
        parts.append(f"===== {p.relative_to(ROOT)} =====\n{p.read_text()}")
    except OSError:
        pass

print(json.dumps({"hookSpecificOutput": {"hookEventName": event,
                                         "additionalContext": "\n\n".join(parts)}}))
